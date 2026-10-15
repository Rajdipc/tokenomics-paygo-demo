"""Cymbal Insurance Claims Agent (Google ADK + Multi-Run TBOM Experiment Engine).

This module defines:
  1. **The Production Google ADK Agent (``root_agent`` and ``app``)**:
     - ``triage_agent`` (``gemini-3.5-flash-lite``, ``MINIMAL`` thinking): extracts structured
       claim facts (policy ID, incident/filed dates, peril, amount, complexity) into
       ``session.state["triage_facts"]``.
     - ``adjudicator_agent`` (``gemini-3.8-flash``, ``MEDIUM`` thinking): applies the
       9-step procedure from ``skills/cymbal-claims-adjudication/SKILL.md`` and the
       static-first ``policy_handbook.md`` using only the 3 scoped tools
       (``get_policy``, ``get_claims_history``, ``screen_fraud``) plus ``submit_decision``.
     - ``reviewer_agent`` (``gemini-4-argon``, ``HIGH`` thinking): senior frontier review
       for low-confidence drafts (``< 0.80``).
     - ``TBOMLedgerPlugin``: attaches low-cardinality Cloud Billing labels and records
       the itemized Token Bill of Materials (TBOM) on every ADK model call.
     - ``adjudicate_claim_with_adk()``: programmatic helper used by the Cloud Run /
       Agent Runtime ``/api/adjudicate`` endpoint and ``deploy/05_test_deployed_agent.py``.

  2. **The Multi-Design TBOM Experiment Harness (``RunConfig``, ``R0``..``R5``, ``Agent``)**:
     - Used by ``run_experiment.py`` to compare all five waterfall designs (``R0`` to ``R5``)
       and the loop-guard fault-injection pair (``R4U`` vs ``R4G``) on identical claims.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime as dt
import json
import os
import pathlib
import random
import threading
import time
import uuid
from typing import Any, Literal

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from .tbom import (
    EXPLICIT_CACHE_MODELS,
    FLASH,
    FLASH_LITE,
    FRONTIER,
    LINE_ITEMS,
    PRICES,
     TBOMLedgerPlugin,
    TIER,
    allocate,
    token_cost,
)
from .tools import (
     I,
    N,
    S,
    SUBMIT,
    Store,
    Tools,
    get_claims_history,
    get_default_store,
    get_policy,
    schema_chars,
    screen_fraud,
    submit_decision,
    toolset,
)

# Ensure ADK uses Gemini Platform (Vertex AI) with ADC when GOOGLE_CLOUD_PROJECT is set.
if os.environ.get("GOOGLE_CLOUD_PROJECT"):
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

# =============================================================================
# 1. Prompts & Run Configurations (R0 through R5, R4U, R4G)
# =============================================================================

BASELINE_SYSTEM = """You are ClaimPilot, Cymbal Insurance's senior AI claims adjuster. You are meticulous,
empathetic and thorough. Customers depend on you to get every decision exactly right, so take your
time, think carefully step by step, and use every tool that could possibly help you build a complete
picture of the claim before deciding. It is always better to gather more information than less.
For every claim: read the customer's message and the Cymbal Claims Adjudication Handbook carefully;
look up the policy, the claims history and the fraud screening result; consider any other tools that
might add context; walk through every step of the handbook decision procedure; then call
submit_decision. In the justification, explain your full reasoning step by step, quote the handbook,
show every calculation and explain why you ruled out each alternative. Aim for at least 150 words.
You may receive several claims in one conversation; treat each new claim independently."""

OPTIMIZED_SYSTEM = """You adjudicate Cymbal Insurance claims strictly by the Claims Adjudication Handbook.
Use get_policy, get_claims_history and screen_fraud, then call submit_decision once.
Apply handbook Section 2 in order and stop at the first step that decides.
Justification: at most 40 words, cite the step and show the payout arithmetic."""

STRICT_LINE = (
    "\nMANDATORY OVERRIDE: You must obtain a successful screen_fraud result before calling "
    "submit_decision. Whenever screen_fraud returns UPSTREAM_TIMEOUT with retryable=true, "
    "call screen_fraud again instead of escalating."
)

TRIAGE_SYSTEM = """Extract claim facts from a customer message for Cymbal Insurance. Return JSON only.
Format policy_id as POL-XXXXXX (6 digits).
Peril must be one of: COLLISION, THEFT, GLASS, VANDALISM, HAIL, FLOOD, ROADSIDE, FIRE, WATER_DAMAGE,
WIND_HAIL, EARTHQUAKE, ELECTRONICS, TRIP_CANCELLATION, MEDICAL_ABROAD, BAGGAGE_LOSS, FLIGHT_DELAY,
ACCIDENT, ILLNESS, DENTAL, MOLD, WEAR_AND_TEAR, PRE_EXISTING. Dates as YYYY-MM-DD; amount in USD.
complexity is "complex" if the description is ambiguous or the amount is large, else "simple"."""

TRIAGE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "policy_id": S,
        "incident_date": S,
        "filed_date": S,
        "peril": S,
        "amount_claimed": N,
        "complexity": {"type": "STRING", "enum": ["simple", "complex"]},
        "summary": S,
    },
    "required": [
        "policy_id",
        "incident_date",
        "filed_date",
        "peril",
        "amount_claimed",
        "complexity",
        "summary",
    ],
}

REVIEWER_SYSTEM = """You are the senior reviewer for Cymbal Insurance claims. Check the junior adjuster's
draft against the Claims Adjudication Handbook, correct it if needed, and call submit_decision once.
Justification: at most 40 words."""


@dataclasses.dataclass(frozen=True)
class RunConfig:
    run_id: str
    title: str
    flow: str = "single"                # "single" agent, or "tiered": triage -> adjudicate -> review
    adjudicator: str = FRONTIER
    adjudicator_thinking: str = "HIGH"
    triage: str | None = None
    reviewer: str | None = None
    review_below_confidence: float = 0.0
    toolset: str = "all"                # "all" = 25 tools; "relevant" = the 3 the rules need
    tool_output: str = "verbose"        # "verbose" JSON records or "compact" Markdown
    session: str = "queue"              # "queue" = 3 claims share a chat; "claim" = fresh per claim
    handbook: str = "after_claim"       # "after_claim" (dynamic first) or "cached" (static first)
    output_style: str = "verbose"       # "verbose" justifications or "concise"
    max_calls: int = 14                 # max adjudicate turns per claim (+1 triage call in tiered runs -> 15 total in R4U)
    retry_budget: int | None = None     # None = unlimited retries of a failing tool
    loop_guard: bool = False            # escalate instead of stopping when max_calls is hit
    faults: bool = False                # fraud screening times out for ~20% of claims
    strict_screening_prompt: bool = False


R0 = RunConfig("R0", "Baseline: one frontier agent does it all")
R1 = dataclasses.replace(
    R0, run_id="R1", title="Trim the TBOM", toolset="relevant",
    tool_output="compact", session="claim", output_style="concise",
)
R2 = dataclasses.replace(
    R1, run_id="R2", title="Tier the models", flow="tiered", triage=FLASH_LITE,
    adjudicator=FLASH, adjudicator_thinking="MEDIUM", reviewer=FRONTIER,
    review_below_confidence=0.8,
)
R3 = dataclasses.replace(R2, run_id="R3", title="Cache the prefix", handbook="cached")
R4U = dataclasses.replace(
    R3, run_id="R4U", title="Flaky dependency, no guards", faults=True,
    strict_screening_prompt=True,
)
R4G = dataclasses.replace(
    R4U, run_id="R4G", title="Flaky dependency, loop guards", retry_budget=1,
    max_calls=8, loop_guard=True, strict_screening_prompt=False,
)
R5 = dataclasses.replace(
    R3, run_id="R5", title="Production: R3 + guards", retry_budget=1,
    max_calls=8, loop_guard=True,
)
RUNS = {r.run_id: r for r in (R0, R1, R2, R3, R4U, R4G, R5)}


def claim_text(c: dict) -> str:
    return (
        f"New claim {c['claim_ref']} received {c['received_at'][:10]} via {c['channel']}.\n"
        f"Subject: {c['subject']}\n\n{c['body']}"
    )


def handbook_block(store: Store) -> str:
    return f"<handbook>\n{store.handbook}\n</handbook>"


# =============================================================================
# 2. Production Google ADK Agent (R5 Tiered Architecture + TBOM Ledger Plugin)
# =============================================================================


def _adk_adjudicator_instruction(ctx: Any = None) -> str:
    """Static-first instruction provider for the R5 ADK adjudicator (system + skill + handbook)."""
    store = get_default_store()
    triage_facts = {}
    claim_ref = "CLM-000001"
    if ctx is not None and hasattr(ctx, "state"):
        triage_facts = ctx.state.get("triage_facts") or {}
        claim_ref = str(ctx.state.get("claim_ref") or "CLM-000001")
    return (
        f"{OPTIMIZED_SYSTEM}\n\n"
        f"<skill>\n{store.skill_markdown}\n</skill>\n\n"
        f"{handbook_block(store)}\n\n"
        f"Current claim_ref: {claim_ref}\n"
        f"Triage extracted facts from step 1: {json.dumps(triage_facts, default=str)}\n"
        "After calling submit_decision, reply with a concise 1-sentence summary of the recorded decision."
    )


class TriageFacts(BaseModel):
    """Structured triage facts extracted by Gemini 3.5 Flash-Lite."""

    policy_id: str = Field(description="Normalized policy ID formatted as POL-XXXXXX.")
    incident_date: str = Field(description="Date of loss in YYYY-MM-DD format.")
    filed_date: str = Field(description="Claim filed date in YYYY-MM-DD format.")
    peril: str = Field(description="Peril code from the handbook.")
    amount_claimed: float = Field(description="Claimed loss amount in USD.")
    complexity: Literal["simple", "complex"] = Field(description="simple or complex.")
    summary: str = Field(description="One-sentence summary of the claim.")


def create_triage_agent():
    """Step 1 of R5: Gemini 3.5 Flash-Lite extracts structured claim facts."""
    from google.adk.agents import Agent
    from google.adk.models import Gemini

    return Agent(
        name="triage_agent",
        model=Gemini(
            model=FLASH_LITE,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        description="Extracts structured claim facts (policy_id, dates, peril, amount, complexity) from an incoming claim message.",
        instruction=TRIAGE_SYSTEM,
        output_schema=TriageFacts,
        output_key="triage_facts",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0,
            thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
        ),
    )


def create_adjudicator_agent():
    """Step 2 of R5: Gemini 3.8 Flash adjudicates the claim using the 3 scoped tools."""
    from google.adk.agents import Agent
    from google.adk.models import Gemini

    return Agent(
        name="adjudicator_agent",
        model=Gemini(
            model=FLASH,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        description="Adjudicates Cymbal Insurance claims using the 3 scoped tools and the Claims Adjudication Handbook.",
        instruction=_adk_adjudicator_instruction,
        tools=[get_policy, get_claims_history, screen_fraud, submit_decision],
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0,
            thinking_config=types.ThinkingConfig(thinking_level="MEDIUM"),
        ),
    )


def _adk_reviewer_instruction(ctx: Any = None) -> str:
    store = get_default_store()
    return f"{REVIEWER_SYSTEM}\n\n{handbook_block(store)}"


def create_reviewer_agent():
    """Optional Step 3 of R5: Gemini 4 Argon reviews low-confidence drafts (< 0.8)."""
    from google.adk.agents import Agent
    from google.adk.models import Gemini

    return Agent(
        name="reviewer_agent",
        model=Gemini(
            model=FRONTIER,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
        description="Senior frontier reviewer (Gemini 4 Argon) for low-confidence claim decisions.",
        instruction=_adk_reviewer_instruction,
        tools=[submit_decision],
        generate_content_config=types.GenerateContentConfig(
            temperature=0.0,
            thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        ),
    )


def build_production_adk_agent():
    """Build the production R5 ADK 2.x Workflow (triage -> adjudicate) for ADK deployment."""
    from google.adk.workflow import Workflow

    triage = create_triage_agent()
    adjudicate = create_adjudicator_agent()
    return Workflow(
        name="cymbal_claims_agent",
        description="Cymbal Insurance R5 production claims agent (Gemini 3.5 Flash-Lite triage -> Gemini 3.8 Flash adjudication with TBOM telemetry).",
        edges=[
            ("START", triage),
            (triage, adjudicate),
        ],
    )


try:
    from google.adk.apps import App

    root_agent = build_production_adk_agent()
    app = App(
        name="cymbal_claims_agent",
        root_agent=root_agent,
        plugins=[TBOMLedgerPlugin(run_id="R5")],
    )
except ImportError:  # pragma: no cover - allows running offline unit tests without google-adk
    root_agent = None  # type: ignore[assignment]
    app = None  # type: ignore[assignment]


async def adjudicate_claim_with_adk(
    claim_ref: str | None = None,
    claim_text_override: str | None = None,
    inject_faults: bool = False,
) -> dict[str, Any]:
    """Run a single claim through the Google ADK R5 ``Runner`` and return the decision + TBOM receipt."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    store = get_default_store()
    if claim_ref and claim_ref in store.claims_by_ref:
        claim_obj = store.claims_by_ref[claim_ref]
        prompt_text = claim_text(claim_obj)
    elif claim_text_override:
        claim_ref = claim_ref or "CLM-CUSTOM"
        prompt_text = claim_text_override
    else:
        claim_obj = store.claims[0]
        claim_ref = claim_obj["claim_ref"]
        prompt_text = claim_text(claim_obj)

    session_service = InMemorySessionService()
    session_id = f"tbom-{uuid.uuid4().hex[:10]}"
    await session_service.create_session(
        app_name="cymbal_claims_agent",
        user_id="adjuster",
        session_id=session_id,
        state={
            "claim_ref": claim_ref,
            "inject_faults": inject_faults,
            "tbom_calls": [],
        },
    )
    runner = Runner(
        app=app,
        session_service=session_service,
    )
    t0 = time.perf_counter()
    final_text = ""
    async for event in runner.run_async(
        user_id="adjuster",
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)]),
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for p in event.content.parts:
                if p.text:
                    final_text = p.text

    session = await session_service.get_session(
        app_name="cymbal_claims_agent", user_id="adjuster", session_id=session_id
    )
    state = session.state if session else {}
    decision = state.get("submitted_decision") or {}
    tbom_calls = state.get("tbom_calls") or []

    # Score against answer_key.csv if claim_ref is known
    expected: dict[str, Any] | None = None
    correct: bool | None = None
    if claim_ref in store.answers:
        a = store.answers[claim_ref]
        sfx = "_if_screening_down" if state.get("screening_down") else ""
        exp_dec = a["expected_decision" + sfx]
        exp_pay = float(a["expected_payout" + sfx])
        expected = {
            "expected_decision": exp_dec,
            "expected_reason": a["expected_reason" + sfx],
            "expected_payout": exp_pay,
        }
        payout = decision.get("payout_usd")
        correct = decision.get("decision") == exp_dec and (
            exp_dec == "DENY"
            or (payout is not None and abs(float(payout) - exp_pay) <= max(1.0, 0.01 * exp_pay))
        )

    tbom_totals = {k: sum(int(c.get(f"tbom_{k}", 0)) for c in tbom_calls) for k in LINE_ITEMS}
    return {
        "claim_ref": claim_ref,
        "decision": decision,
        "agent_summary": final_text,
        "expected": expected,
        "correct": correct,
        "latency_ms": int((time.perf_counter() - t0) * 1000),
        "tbom_summary": {
            "llm_calls": len(tbom_calls),
            "tool_calls": int(state.get("tool_calls", 0)),
            "prompt_tokens": sum(int(c.get("prompt_tokens", 0)) for c in tbom_calls),
            "cached_tokens": sum(int(c.get("cached_tokens", 0)) for c in tbom_calls),
            "output_tokens": sum(int(c.get("output_tokens", 0)) for c in tbom_calls),
            "thoughts_tokens": sum(int(c.get("thoughts_tokens", 0)) for c in tbom_calls),
            "cost_usd": round(sum(float(c.get("cost_usd", 0.0)) for c in tbom_calls), 6),
            "line_items_tokens": tbom_totals,
        },
        "calls": tbom_calls,
    }


# =============================================================================
# 3. Multi-Design Experiment Harness (used by run_experiment.py for R0..R5)
# =============================================================================


class Jsonl:
    def __init__(self, path: pathlib.Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.lock = path, threading.Lock()

    def write(self, row: dict) -> None:
        with self.lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")


class Gemini:
    """Standard PayGo client on Gemini Platform; retries 429/5xx with backoff."""

    simulated = False

    def __init__(self):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise SystemExit("Set GOOGLE_CLOUD_PROJECT (see .env.example).")
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
            http_options=types.HttpOptions(api_version="v1"),
        )

    def generate(self, model, contents, config):
        delay = 2.0
        for attempt in range(6):
            start = time.perf_counter()
            try:
                resp = self.client.models.generate_content(model=model, contents=contents, config=config)
                return resp, int((time.perf_counter() - start) * 1000)
            except errors.APIError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 5:
                    raise
                time.sleep(delay + random.random())
                delay = min(delay * 2, 60)

    def create_cache(self, model, system, contents, tools, ttl_seconds, name):
        cache = self.client.caches.create(
            model=model,
            config=types.CreateCachedContentConfig(
                display_name=name,
                system_instruction=system,
                contents=contents,
                tools=tools,
                ttl=f"{ttl_seconds}s",
            ),
        )
        return cache.name, int(cache.usage_metadata.total_token_count or 0)

    def delete_cache(self, name):
        self.client.caches.delete(name=name)


def chars_of(content: types.Content) -> int:
    n = 0
    for p in content.parts or []:
        if p.text:
            n += len(p.text)
        elif p.function_call:
            n += len(json.dumps(p.function_call.args or {}, default=str))
        elif p.function_response:
            n += len(json.dumps(p.function_response.response or {}, default=str))
    return n


class Conversation:
    """Contents, plus which TBOM line item each content contributes."""

    def __init__(self):
        self.contents: list[types.Content] = []
        self.meta: list[dict[str, int]] = []

    def add(self, content, **items):
        self.contents.append(content)
        self.meta.append(items)

    def user(self, text, **items):
        last = self.contents[-1] if self.contents else None
        if last is not None and last.role == "user" and not any(p.function_response for p in last.parts or []):
            last.parts.append(types.Part(text=text))
            for k, v in items.items():
                self.meta[-1][k] = self.meta[-1].get(k, 0) + v
        else:
            self.add(types.Content(role="user", parts=[types.Part(text=text)]), **items)

    def to_history(self):
        self.meta = [{"history": sum(m.values())} for m in self.meta]

    def items(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for m in self.meta:
            for k, v in m.items():
                out[k] = out.get(k, 0) + v
        return out


class Agent:
    """Configurable claims agent supporting all 7 experiment designs (R0..R5, R4U, R4G)."""

    def __init__(self, cfg, store, gemini, run_tag, out_calls, out_claims, tracer=None):
        self.cfg, self.store, self.gemini, self.run_tag = cfg, store, gemini, run_tag
        self.out_calls, self.out_claims, self.tracer = out_calls, out_claims, tracer
        self.caches: dict[str, dict] = {}

    def create_caches(self):
        if self.cfg.handbook != "cached":
            return
        hb = [types.Content(role="user", parts=[types.Part(text=handbook_block(self.store))])]
        plan = {"adjudicate": (self.cfg.adjudicator, self.system(), toolset(self.cfg.toolset))}
        if self.cfg.reviewer:
            plan["review"] = (self.cfg.reviewer, REVIEWER_SYSTEM, [types.Tool(function_declarations=[SUBMIT])])
        for role, (model, system, tools) in plan.items():
            if model not in EXPLICIT_CACHE_MODELS:
                continue
            name, tokens = self.gemini.create_cache(
                model, system, hb, tools, 3600, f"tbom-{self.cfg.run_id.lower()}-{role}"
            )
            self.caches[role] = {
                "name": name,
                "model": model,
                "tokens": tokens,
                "created": time.time(),
                "chars": {
                    "system_prompt": len(system),
                    "handbook": chars_of(hb[0]),
                    "tool_schemas": schema_chars(tools),
                },
            }

    def delete_caches(self) -> tuple[float, float]:
        """Deletes the caches; returns (storage USD, creation USD)."""
        storage = creation = 0.0
        for c in self.caches.values():
            with contextlib.suppress(Exception):
                self.gemini.delete_cache(c["name"])
            hours = max(time.time() - c["created"], 60) / 3600
            storage += c["tokens"] / 1e6 * float(PRICES[c["model"]]["cache_storage_hour"] or 0.0) * hours
            creation += c["tokens"] / 1e6 * float(PRICES[c["model"]]["input"] or 0.0)
        return storage, creation

    def system(self) -> str:
        s = BASELINE_SYSTEM if self.cfg.output_style == "verbose" else OPTIMIZED_SYSTEM
        return s + (STRICT_LINE if self.cfg.strict_screening_prompt else "")

    def process(self, batch: list[dict]) -> list[dict]:
        if self.cfg.flow == "single":
            return self.single(batch)
        return [self.tiered(c) for c in batch]

    def single(self, batch):
        convo, rows = Conversation(), []
        for claim in batch:
            if self.cfg.session == "claim":
                convo = Conversation()
            else:
                convo.to_history()
            tools, calls, t0 = Tools(self.store, self.cfg, claim["claim_ref"]), [], time.perf_counter()
            msg, hb = claim_text(claim), handbook_block(self.store)
            convo.user(f"{msg}\n\n{hb}", claim_input=len(msg), handbook=len(hb))
            with self.span(claim):
                result = self.loop(
                    claim, convo, tools, calls, "adjudicate", self.cfg.adjudicator,
                    self.cfg.adjudicator_thinking, self.system(), toolset(self.cfg.toolset),
                )
            rows.append(self.finish(claim, result, tools, calls, t0, reviewed=False))
        return rows

    def tiered(self, claim):
        tools, calls, t0 = Tools(self.store, self.cfg, claim["claim_ref"]), [], time.perf_counter()
        with self.span(claim):
            try:
                facts = self.triage(claim, calls)
            except Exception as exc:  # noqa: BLE001
                facts = {"summary": f"triage failed: {exc}"}
            req = (
                f"Claim {claim['claim_ref']}, filed {claim['received_at'][:10]}. Triage extracted: "
                + "; ".join(
                    f"{k}={facts.get(k)}"
                    for k in ("policy_id", "incident_date", "peril", "amount_claimed", "summary")
                )
            )
            if not facts.get("policy_id"):
                req += "\n\nOriginal message:\n" + claim_text(claim)
            convo = Conversation()
            if self.cfg.handbook == "cached":
                convo.user(req, claim_input=len(req))
            else:
                hb = handbook_block(self.store)
                convo.user(f"{req}\n\n{hb}", claim_input=len(req), handbook=len(hb))
            result = self.loop(
                claim, convo, tools, calls, "adjudicate", self.cfg.adjudicator,
                self.cfg.adjudicator_thinking, self.system(), toolset(self.cfg.toolset),
            )
            reviewed = False
            draft = result.get("decision")
            if (
                self.cfg.reviewer
                and draft
                and not result.get("forced")
                and float(draft.get("confidence") or 0) < self.cfg.review_below_confidence
            ):
                reviewed = True
                gathered = [json.dumps(facts)] + [
                    str(p.function_response.response.get("result"))
                    for c in convo.contents
                    for p in c.parts or []
                    if p.function_response and p.function_response.name != "submit_decision"
                ]
                with contextlib.suppress(Exception):
                    result["decision"] = self.review(claim, gathered, draft, calls) or draft
        return self.finish(claim, result, tools, calls, t0, reviewed)

    def triage(self, claim, calls) -> dict:
        msg = claim_text(claim)
        config = types.GenerateContentConfig(
            system_instruction=TRIAGE_SYSTEM,
            response_mime_type="application/json",
            response_schema=TRIAGE_SCHEMA,
            labels=self.labels("triage", self.cfg.triage),
            thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
        )
        resp = self.call(
            claim, "triage", self.cfg.triage,
            [types.Content(role="user", parts=[types.Part(text=msg)])],
            config, calls,
            {"system_prompt": len(TRIAGE_SYSTEM), "tool_schemas": len(json.dumps(TRIAGE_SCHEMA)), "claim_input": len(msg)},
        )
        return json.loads(resp.text or "{}")

    def review(self, claim, gathered, draft, calls):
        req = (
            f"Claim {claim['claim_ref']}.\nFacts gathered:\n"
            + "\n".join(f"- {g}" for g in gathered)
            + f"\n\nDraft decision: {draft}\nReturn the corrected decision with submit_decision."
        )
        fact_chars = sum(len(g) for g in gathered)
        items = {"claim_input": len(req) - fact_chars, "tool_results": fact_chars}
        think = types.ThinkingConfig(thinking_level="HIGH")
        if "review" in self.caches:
            config = types.GenerateContentConfig(
                cached_content=self.caches["review"]["name"],
                thinking_config=think,
                labels=self.labels("review", self.cfg.reviewer),
            )
            items.update(self.caches["review"]["chars"])
        else:
            tools = [types.Tool(function_declarations=[SUBMIT])]
            hb = handbook_block(self.store)
            if self.cfg.handbook == "cached":
                system = f"{REVIEWER_SYSTEM}\n\n{hb}"
            else:
                system, req = REVIEWER_SYSTEM, f"{req}\n\n{hb}"
            config = types.GenerateContentConfig(
                system_instruction=system,
                tools=tools,
                thinking_config=think,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                labels=self.labels("review", self.cfg.reviewer),
            )
            items.update({"system_prompt": len(REVIEWER_SYSTEM), "handbook": len(hb), "tool_schemas": schema_chars(tools)})
        resp = self.call(
            claim, "review", self.cfg.reviewer,
            [types.Content(role="user", parts=[types.Part(text=req)])],
            config, calls, items,
        )
        return next((dict(fc.args or {}) for fc in resp.function_calls or [] if fc.name == "submit_decision"), None)

    def loop(self, claim, convo, tools, calls, step, model, thinking, system, decls) -> dict:
        cache = self.caches.get(step)
        for _ in range(self.cfg.max_calls):
            common = dict(
                thinking_config=types.ThinkingConfig(thinking_level=thinking),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                labels=self.labels(step, model),
            )
            if cache:
                config = types.GenerateContentConfig(cached_content=cache["name"], **common)
                static = cache["chars"]
            else:
                config = types.GenerateContentConfig(system_instruction=system, tools=decls, **common)
                static = {"system_prompt": len(system), "tool_schemas": schema_chars(decls)}
            items = convo.items()
            for k, v in static.items():
                items[k] = items.get(k, 0) + v
            try:
                resp = self.call(claim, step, model, convo.contents, config, calls, items)
            except Exception as exc:  # noqa: BLE001
                return {"error": f"{type(exc).__name__}: {exc}"[:500]}
            if not resp.candidates or not resp.candidates[0].content:
                return {"error": "EMPTY_RESPONSE"}
            turn = resp.candidates[0].content
            convo.add(turn, history=chars_of(turn))
            if not resp.function_calls:
                convo.user("Call submit_decision now.", claim_input=24)
                continue
            parts, final = [], None
            for fc in resp.function_calls:
                if fc.name == "submit_decision":
                    final, result = dict(fc.args or {}), "recorded"
                else:
                    result = tools.run(fc.name, dict(fc.args or {}))
                parts.append(types.Part.from_function_response(name=fc.name, response={"result": result}))
            reply = types.Content(role="user", parts=parts)
            convo.add(reply, tool_results=chars_of(reply))
            if final is not None:
                return {"decision": final}
        if self.cfg.loop_guard:
            return {
                "decision": {
                    "decision": "ESCALATE",
                    "reason_code": "LOOP_GUARD",
                    "payout_usd": None,
                    "confidence": 0.0,
                },
                "forced": True,
            }
        return {"error": "SAFETY_CAP_REACHED"}

    def call(self, claim, step, model, contents, config, calls, items) -> types.GenerateContentResponse:
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        span_cm = self.tracer.start_as_current_span(f"gen_ai.{step}") if self.tracer else contextlib.nullcontext()
        with span_cm as span:
            resp, latency = self.gemini.generate(model, contents, config)
            u = resp.usage_metadata or types.GenerateContentResponseUsageMetadata()
            row = {
                "run_tag": self.run_tag,
                "run_id": self.cfg.run_id,
                "claim_ref": claim["claim_ref"],
                "step": step,
                "call_index": len(calls),
                "model": model,
                "tier": TIER[model],
                "started_at": started,
                "latency_ms": latency,
                "traffic_type": str(getattr(u.traffic_type, "value", u.traffic_type) or ""),
                "prompt_tokens": u.prompt_token_count or 0,
                "cached_tokens": u.cached_content_token_count or 0,
                "output_tokens": u.candidates_token_count or 0,
                "thoughts_tokens": u.thoughts_token_count or 0,
                "function_calls": ",".join(fc.name for fc in resp.function_calls or []),
                "labels": json.dumps(config.labels or {}),
                "simulated": self.gemini.simulated,
            }
            row["cost_usd"] = token_cost(
                model, row["prompt_tokens"], row["cached_tokens"], row["output_tokens"], row["thoughts_tokens"]
            )
            row.update({f"tbom_{k}": v for k, v in allocate(items, row["prompt_tokens"]).items()})
            if span is not None:
                for key, value in {
                    "gen_ai.request.model": model,
                    "gen_ai.usage.input_tokens": row["prompt_tokens"],
                    "gen_ai.usage.output_tokens": row["output_tokens"] + row["thoughts_tokens"],
                    "tbom.cached_tokens": row["cached_tokens"],
                    "tbom.cost_usd": row["cost_usd"],
                    "claim_ref": claim["claim_ref"],
                }.items():
                    span.set_attribute(key, value)
        calls.append(row)
        self.out_calls.write(row)
        return resp

    def finish(self, claim, result, tools, calls, t0, reviewed) -> dict:
        a = self.store.answers[claim["claim_ref"]]
        sfx = "_if_screening_down" if tools.screening_down else ""
        exp_decision, exp_payout = a["expected_decision" + sfx], float(a["expected_payout" + sfx])
        d = result.get("decision") or {}
        payout = d.get("payout_usd")
        correct = d.get("decision") == exp_decision and (
            exp_decision == "DENY"
            or (payout is not None and abs(float(payout) - exp_payout) <= max(1.0, 0.01 * exp_payout))
        )
        row = {
            "run_tag": self.run_tag,
            "run_id": self.cfg.run_id,
            "claim_ref": claim["claim_ref"],
            "product": a["product"],
            "complexity": a["complexity"],
            "decision": d.get("decision"),
            "reason_code": d.get("reason_code"),
            "payout_usd": float(payout) if payout is not None else None,
            "confidence": float(d["confidence"]) if d.get("confidence") is not None else None,
            "expected_decision": exp_decision,
            "expected_reason": a["expected_reason" + sfx],
            "expected_payout": exp_payout,
            "correct": correct,
            "reviewed_by_frontier": reviewed,
            "llm_calls": len(calls),
            "tool_calls": tools.calls,
            "decoy_calls": tools.decoy_calls,
            "tool_failures": tools.failures,
            "fault_injected": tools.faulty,
            "guard_tripped": tools.guard_tripped or bool(result.get("forced")),
            "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
            "cached_tokens": sum(c["cached_tokens"] for c in calls),
            "output_tokens": sum(c["output_tokens"] for c in calls),
            "thoughts_tokens": sum(c["thoughts_tokens"] for c in calls),
            "cost_usd": sum(c["cost_usd"] for c in calls),
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "simulated": self.gemini.simulated,
            "error": result.get("error"),
        }
        self.out_claims.write(row)
        return row

    def labels(self, step, model) -> dict[str, str]:
        return {
            "app": "cymbal-claims",
            "experiment": "tbom",
            "run": self.cfg.run_id.lower(),
            "run_tag": self.run_tag,
            "step": step,
            "tier": TIER[model],
        }

    def span(self, claim):
        if not self.tracer:
            return contextlib.nullcontext()
        return self.tracer.start_as_current_span(
            "claim", attributes={"claim_ref": claim["claim_ref"], "run": self.cfg.run_id}
        )
