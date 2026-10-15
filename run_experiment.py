"""Token Bill of Materials (TBOM) experiment - Cymbal Insurance claims agent on Gemini Platform.

ONE script, run from Cloud Shell. It sends the same insurance claims through a
Gemini agent several times, applying one more cost lever each time, and writes
what every model call cost - token by token - to three JSONL files that you
then upload to BigQuery from the console (see RUNBOOK.md).

    pip install -r requirements.txt
    source .env
    python run_experiment.py --runs R0 R1 R2 R3 R5 --n 50
    python run_experiment.py --runs R4U R4G --n 40

Runs (one family of levers changes each time; all on Standard PayGo):
    R0   Baseline          one Gemini 4 Argon (frontier) agent does everything
    R1   Trim the TBOM     3 tools, compact tool output, one session per claim, short answers
    R2   Tier the models   3.5 Flash-Lite triage -> 3.8 Flash adjudication -> 4 Argon review if unsure
    R3   Cache the prefix  static-first prompts; explicit cache on Flash, implicit cache on Argon
    R4U  Flaky dependency  fraud service times out for 20% of claims, no guards
    R4G  Guard the loop    same fault, retry budget 1 + max 8 model calls per claim
    R5   Production        R3 + guards, healthy dependencies

Outputs in results/<run_tag>/:
    calls.jsonl   one row per model call: billed tokens, list-price cost, TBOM line items
    claims.jsonl  one row per claim: decision, expected decision, correct?, cost
    runs.jsonl    one row per run: explicit-cache cost, timings

Sections of this file:
    1. Prices and run configurations
    2. Data and tools
    3. Prompts
    4. The Token Bill of Materials ledger
    5. Gemini calls (Standard PayGo) and explicit caches
    6. The agent
    7. Command line
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import contextlib
import csv
import dataclasses
import datetime as dt
import json
import os
import pathlib
import random
import re
import sys
import threading
import time
from typing import Any

from google import genai
from google.genai import errors, types

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"

# =============================================================================
# 1. Prices and run configurations
# =============================================================================

# Generally available (GA) models only - no Preview models.
FRONTIER, FLASH, FLASH_LITE = "gemini-4-argon", "gemini-3.8-flash", "gemini-3.5-flash-lite"
TIER = {FRONTIER: "frontier", FLASH: "flash", FLASH_LITE: "flash-lite"}
# Gemini 4 Argon supports implicit context caching only (no explicit caches).
EXPLICIT_CACHE_MODELS = {FLASH, FLASH_LITE}

# Standard PayGo list prices, global endpoint, prompts <= 200K tokens, USD per 1M tokens.
# Source: https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
# As of 2026-10-15. These are the regular list prices. Until 30 Nov 2026 (4 Argon) and
# 31 Dec 2026 (3.8 Flash) the pricing page shows promotional prices delivered as 50%
# credits back, so the NET bill can be about half of this estimate (the billing export
# shows gross cost and the credit separately). Used only to estimate cost and enforce
# --max-usd; Cloud Billing is the source of truth. Keep in sync with sql/00_reference_tables.sql.
PRICES = {
    FRONTIER:   {"input": 4.00, "cached": 0.20, "output": 20.00, "cache_storage_hour": None},
    FLASH:      {"input": 1.50, "cached": 0.15, "output": 7.50, "cache_storage_hour": 1.00},
    FLASH_LITE: {"input": 0.30, "cached": 0.03, "output": 2.50, "cache_storage_hour": 1.00},
}


def token_cost(model: str, prompt: int, cached: int, output: int, thoughts: int) -> float:
    """Cost of one call. prompt includes cached tokens; thinking bills at the output rate."""
    p = PRICES[model]
    return (max(0, prompt - cached) * p["input"] + cached * p["cached"]
            + (output + thoughts) * p["output"]) / 1_000_000


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
    max_calls: int = 14                 # hard safety cap so nothing can run away
    retry_budget: int | None = None     # None = unlimited retries of a failing tool
    loop_guard: bool = False            # escalate instead of stopping when max_calls is hit
    faults: bool = False                # fraud screening times out for ~20% of claims
    strict_screening_prompt: bool = False


R0 = RunConfig("R0", "Baseline: one frontier agent does it all")
R1 = dataclasses.replace(R0, run_id="R1", title="Trim the TBOM", toolset="relevant",
                         tool_output="compact", session="claim", output_style="concise")
R2 = dataclasses.replace(R1, run_id="R2", title="Tier the models", flow="tiered", triage=FLASH_LITE,
                         adjudicator=FLASH, adjudicator_thinking="MEDIUM", reviewer=FRONTIER,
                         review_below_confidence=0.8)
R3 = dataclasses.replace(R2, run_id="R3", title="Cache the prefix", handbook="cached")
R4U = dataclasses.replace(R3, run_id="R4U", title="Flaky dependency, no guards", faults=True,
                          strict_screening_prompt=True)
R4G = dataclasses.replace(R4U, run_id="R4G", title="Flaky dependency, loop guards", retry_budget=1,
                          max_calls=8, loop_guard=True, strict_screening_prompt=False)
R5 = dataclasses.replace(R3, run_id="R5", title="Production: R3 + guards", retry_budget=1,
                         max_calls=8, loop_guard=True)
RUNS = {r.run_id: r for r in (R0, R1, R2, R3, R4U, R4G, R5)}

# =============================================================================
# 2. Data and tools
# =============================================================================


def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Store:
    """The synthetic Cymbal data, held in memory."""

    def __init__(self):
        self.customers = {r["customer_id"]: r for r in read_csv("customers.csv")}
        self.policies = {r["policy_id"]: r for r in read_csv("policies.csv")}
        self.history: dict[str, list[dict]] = {}
        for r in read_csv("claims_history.csv"):
            self.history.setdefault(r["customer_id"], []).append(r)
        self.claims = [json.loads(x) for x in (DATA / "incoming_claims.jsonl").read_text().splitlines()]
        self.answers = {r["claim_ref"]: r for r in read_csv("answer_key.csv")}
        self.handbook = (DATA / "policy_handbook.md").read_text(encoding="utf-8")


def decl(name: str, description: str, props: dict, required: list[str]) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(name=name, description=description, parameters={
        "type": "OBJECT", "properties": props, "required": required})


S, N, I = {"type": "STRING"}, {"type": "NUMBER"}, {"type": "INTEGER"}
GET_POLICY = decl("get_policy", "Fetch the policy record (product, plan, status, term dates, limits, "
                  "deductible, riders).", {"policy_id": S}, ["policy_id"])
GET_HISTORY = decl("get_claims_history", "List the customer's prior claims before a date of loss.",
                   {"customer_id": S, "as_of_date": S, "lookback_days": I}, ["customer_id", "as_of_date"])
SCREEN = decl("screen_fraud", "Run fraud screening. Returns an advisory score from 0 to 100.",
              {"policy_id": S, "peril": S, "amount_claimed": N}, ["policy_id", "peril", "amount_claimed"])
SUBMIT = decl("submit_decision", "Record the final decision. Call exactly once.", {
    "claim_ref": S, "decision": {"type": "STRING", "enum": ["APPROVE", "DENY", "ESCALATE"]},
    "reason_code": S, "payout_usd": N, "peril": S, "confidence": N, "justification": S},
    ["claim_ref", "decision", "reason_code", "payout_usd", "peril", "confidence", "justification"])

# 22 plausible but irrelevant tools. Every declaration is re-sent on every call, so an
# over-equipped agent pays for its whole toolbox on every turn.
DECOYS = [decl(n, d, {p: {"type": "STRING", "description": p.replace("_", " ")} for p in ps}, ps[:1])
          for n, d, ps in [
    ("lookup_weather_history", "Historical weather observations (precipitation, wind gusts, hail size) for a postal code and date range from the national weather archive.", ["postal_code", "start_date", "end_date"]),
    ("find_repair_shops", "Search the preferred repair network for body shops, glaziers, roofers and restoration contractors near an address, with ratings and cycle times.", ["address", "trade", "radius_km"]),
    ("estimate_vehicle_value", "Actual cash value of a vehicle from VIN, mileage and region using third-party valuation guides.", ["vin", "mileage", "zip"]),
    ("check_flight_status", "Operational history of a flight: scheduled and actual times, delay codes, cancellations, diversions.", ["flight_number", "date"]),
    ("search_vet_directory", "Licensed veterinary clinics and emergency hospitals near a location.", ["location", "specialty"]),
    ("convert_currency", "Convert an amount between currencies at the reference rate for a date.", ["amount", "from_currency", "to_currency", "date"]),
    ("send_customer_email", "Send an e-mail to the policyholder using an approved template; logged in the claim file.", ["customer_id", "template", "variables"]),
    ("schedule_inspection", "Book an on-site inspection with a field adjuster.", ["policy_id", "preferred_date", "notes"]),
    ("lookup_agent_directory", "Servicing agent or broker for a policy, with licence numbers.", ["policy_id"]),
    ("translate_text", "Translate free text between languages for customer communications.", ["text", "target_language"]),
    ("validate_address", "Standardize a postal address and return geocode and flood zone.", ["address"]),
    ("get_payment_status", "Premium payment and refund status on a policy, including grace periods.", ["policy_id"]),
    ("extract_document_fields", "OCR an uploaded invoice, police report or medical bill.", ["document_id", "document_type"]),
    ("check_sanctions_list", "Screen a person or company against sanctions lists before payment.", ["full_name", "country"]),
    ("lookup_credit_score", "Insurance credit score for underwriting (not for claims decisions).", ["customer_id"]),
    ("estimate_property_value", "Rebuild cost and market value for a residential property.", ["address", "square_feet"]),
    ("search_medical_providers", "In-network hospitals abroad with direct-billing agreements.", ["country", "city"]),
    ("get_police_report", "Retrieve a police or incident report from participating departments.", ["report_number", "jurisdiction"]),
    ("book_rental_car", "Reserve a replacement rental vehicle for a policyholder.", ["policy_id", "pickup_date", "days"]),
    ("list_catastrophe_events", "Declared catastrophe events for a state and date range.", ["state", "start_date", "end_date"]),
    ("get_customer_preferences", "Communication preferences, language and accessibility needs.", ["customer_id"]),
    ("search_knowledge_base", "Full-text search over internal claims articles and past rulings.", ["query", "max_results"]),
]]


def toolset(name: str) -> list[types.Tool]:
    decls = [GET_POLICY, GET_HISTORY, SCREEN] + (DECOYS if name == "all" else []) + [SUBMIT]
    return [types.Tool(function_declarations=decls)]


def schema_chars(tools: list[types.Tool] | None) -> int:
    return len(json.dumps([t.model_dump(exclude_none=True) for t in tools or []], default=str))


class Tools:
    """Executes the tools for ONE claim; injects faults and applies the retry budget."""

    def __init__(self, store: Store, cfg: RunConfig, claim_ref: str):
        self.store, self.cfg = store, cfg
        self.faulty = cfg.faults and int(claim_ref[-6:]) % 5 == 0  # ~20% of claims
        self.calls = self.failures = self.decoy_calls = 0
        self.screening_down = self.guard_tripped = False

    @staticmethod
    def norm_policy_id(raw: Any) -> str:
        s = str(raw or "").strip().upper()
        m = re.search(r"(\d{6})", s)
        return f"POL-{m.group(1)}" if m else s

    def run(self, name: str, args: dict) -> str:
        self.calls += 1
        try:
            if name == "get_policy":
                return self.policy(self.norm_policy_id(args.get("policy_id", "")))
            if name == "get_claims_history":
                return self.claims_history(str(args.get("customer_id", "")).strip().upper(),
                                           str(args.get("as_of_date", ""))[:10],
                                           int(args.get("lookback_days") or 365))
            if name == "screen_fraud":
                return self.screen(self.norm_policy_id(args.get("policy_id", "")),
                                   float(args.get("amount_claimed") or 0))
        except (TypeError, ValueError) as exc:
            return self.dump({"status": "ERROR", "error": f"bad arguments: {exc}"})
        self.decoy_calls += 1
        return self.dump({"status": "OK", "tool": name, "note": "Informational only.",
                          "results": [{"id": f"R{k}", "value": round(random.random(), 4)} for k in range(5)]})

    def policy(self, policy_id: str) -> str:
        row = self.store.policies.get(policy_id)
        if row is None:
            return self.dump({"status": "NOT_FOUND", "policy_id": policy_id})
        riders = row["riders"].replace("|", ", ") or "none"
        if self.cfg.tool_output == "compact":
            return ("| policy_id | customer_id | product | plan | status | start | end | coverage_limit | deductible | riders |\n"
                    "|---|---|---|---|---|---|---|---|---|---|\n"
                    f"| {row['policy_id']} | {row['customer_id']} | {row['product']} | {row['plan']} | {row['status']} "
                    f"| {row['start_date']} | {row['end_date']} | {row['coverage_limit']} | {row['deductible']} | {riders} |")
        rng = random.Random(policy_id)  # the full system-of-record payload a real API returns
        return self.dump({"status": "OK", "policy": {**row, "riders": riders.split(", ")},
                          "customer": self.store.customers.get(row["customer_id"], {}),
                          "billing_history": [{"period": k, "amount_due": round(rng.uniform(25, 180), 2),
                                               "status": rng.choice(["PAID", "PAID", "LATE"])} for k in range(12)],
                          "agent_notes": ["Customer prefers e-mail contact.", "Verified identity at onboarding."],
                          "audit": {"source_system": "PAS-7", "record_version": rng.randint(1, 30),
                                    "etag": f"{rng.getrandbits(64):016x}"}})

    def claims_history(self, customer_id: str, as_of: str, lookback: int) -> str:
        try:
            day = dt.date.fromisoformat(as_of)
        except ValueError:
            return self.dump({"status": "ERROR", "error": "as_of_date must be YYYY-MM-DD"})
        before = [r for r in self.store.history.get(customer_id, []) if r["incident_date"] < as_of]
        start = (day - dt.timedelta(days=lookback)).isoformat()
        window = [r for r in before if r["incident_date"] >= start]
        if self.cfg.tool_output == "compact":
            return (f"Prior claims with date of loss in the {lookback} days before {as_of}: **{len(window)}**\n"
                    + "\n".join(f"- {r['incident_date']} {r['product']} {r['peril']} {r['outcome']}"
                                for r in sorted(window, key=lambda r: r["incident_date"])[-3:]))
        return self.dump({"status": "OK", "customer_id": customer_id, "claims": before})

    def screen(self, policy_id: str, amount: float) -> str:
        if self.faulty:
            self.failures += 1
            self.screening_down = True
            if self.cfg.retry_budget is not None and self.failures > self.cfg.retry_budget:
                self.guard_tripped = True
                return self.dump({"status": "UNAVAILABLE", "retryable": False, "message":
                                  "Fraud screening is unavailable after 1 retry. Do not call screen_fraud "
                                  "again. Apply handbook Section 2 in order: if steps 1-5 do not deny the "
                                  "claim, use step 6 (SCREENING_UNAVAILABLE)."})
            return self.dump({"status": "ERROR", "error": "UPSTREAM_TIMEOUT", "retryable": True,
                              "message": "Transient timeout; retry screen_fraud."})
        rng = random.Random(f"{policy_id}:{amount:.2f}")
        score = rng.randint(1, 95)
        if self.cfg.tool_output == "compact":
            return f"fraud_score={score} (advisory)"
        return self.dump({"status": "OK", "screening": {
            "score": score, "model_version": "fraudnet-2026.09",
            "features": {f"f{k:02d}": round(rng.random(), 4) for k in range(24)}}})

    def dump(self, obj: Any) -> str:
        if self.cfg.tool_output == "compact":
            return json.dumps(obj, separators=(",", ":"), default=str)
        return json.dumps(obj, indent=2, default=str)


# =============================================================================
# 3. Prompts (the business rules live in the handbook, not here)
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

STRICT_LINE = ("\nMANDATORY OVERRIDE: You must obtain a successful screen_fraud result before calling "
               "submit_decision. Whenever screen_fraud returns UPSTREAM_TIMEOUT with retryable=true, "
               "call screen_fraud again instead of escalating.")

TRIAGE_SYSTEM = """Extract claim facts from a customer message for Cymbal Insurance. Return JSON only.
Format policy_id as POL-XXXXXX (6 digits).
Peril must be one of: COLLISION, THEFT, GLASS, VANDALISM, HAIL, FLOOD, ROADSIDE, FIRE, WATER_DAMAGE,
WIND_HAIL, EARTHQUAKE, ELECTRONICS, TRIP_CANCELLATION, MEDICAL_ABROAD, BAGGAGE_LOSS, FLIGHT_DELAY,
ACCIDENT, ILLNESS, DENTAL, MOLD, WEAR_AND_TEAR, PRE_EXISTING. Dates as YYYY-MM-DD; amount in USD.
complexity is "complex" if the description is ambiguous or the amount is large, else "simple"."""

TRIAGE_SCHEMA = {"type": "OBJECT", "properties": {
    "policy_id": S, "incident_date": S, "filed_date": S, "peril": S, "amount_claimed": N,
    "complexity": {"type": "STRING", "enum": ["simple", "complex"]}, "summary": S},
    "required": ["policy_id", "incident_date", "filed_date", "peril", "amount_claimed", "complexity", "summary"]}

REVIEWER_SYSTEM = """You are the senior reviewer for Cymbal Insurance claims. Check the junior adjuster's
draft against the Claims Adjudication Handbook, correct it if needed, and call submit_decision once.
Justification: at most 40 words."""


def claim_text(c: dict) -> str:
    return (f"New claim {c['claim_ref']} received {c['received_at'][:10]} via {c['channel']}.\n"
            f"Subject: {c['subject']}\n\n{c['body']}")


def handbook_block(store: Store) -> str:
    return f"<handbook>\n{store.handbook}\n</handbook>"


# =============================================================================
# 4. The Token Bill of Materials ledger
# =============================================================================
# The API reports exact totals per call (usage_metadata). The split into line items is
# an allocation: we know how many characters each part of the request contributed, and
# scale those sizes so the line items add up EXACTLY to the billed prompt tokens.

LINE_ITEMS = ("system_prompt", "handbook", "tool_schemas", "history", "tool_results", "claim_input")


def allocate(chars: dict[str, int], prompt_tokens: int) -> dict[str, int]:
    sizes = {k: max(0, chars.get(k, 0)) for k in LINE_ITEMS}
    total = sum(sizes.values())
    if not total or prompt_tokens <= 0:
        return dict.fromkeys(LINE_ITEMS, 0)
    raw = {k: prompt_tokens * v / total for k, v in sizes.items()}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: prompt_tokens - sum(out.values())]:
        out[k] += 1
    return out


class Jsonl:
    def __init__(self, path: pathlib.Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self.lock = path, threading.Lock()

    def write(self, row: dict) -> None:
        with self.lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")


# =============================================================================
# 5. Gemini calls (Standard PayGo on Gemini Platform) and explicit caches
# =============================================================================


class Gemini:
    """Standard PayGo: no consumption-option header. Retries 429/5xx with backoff."""

    simulated = False

    def __init__(self):
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            sys.exit("Set GOOGLE_CLOUD_PROJECT (see .env.example).")
        self.client = genai.Client(vertexai=True, project=project,
                                   location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
                                   http_options=types.HttpOptions(api_version="v1"))

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
        cache = self.client.caches.create(model=model, config=types.CreateCachedContentConfig(
            display_name=name, system_instruction=system, contents=contents, tools=tools,
            ttl=f"{ttl_seconds}s"))
        return cache.name, int(cache.usage_metadata.total_token_count or 0)

    def delete_cache(self, name):
        self.client.caches.delete(name=name)


# =============================================================================
# 6. The agent
# =============================================================================
# The loop calls the Gen AI SDK directly with automatic function calling OFF, so the
# harness controls - and records - every model call.


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
        # Merge into a trailing user turn only if it holds plain text. A turn that carries
        # function responses must stay on its own: Gemini rejects a function-response turn
        # that also contains new user text.
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
    def __init__(self, cfg, store, gemini, run_tag, out_calls, out_claims, tracer=None):
        self.cfg, self.store, self.gemini, self.run_tag = cfg, store, gemini, run_tag
        self.out_calls, self.out_claims, self.tracer = out_calls, out_claims, tracer
        self.caches: dict[str, dict] = {}

    # -- explicit caches (R3 onwards) -----------------------------------------

    def create_caches(self):
        if self.cfg.handbook != "cached":
            return
        hb = [types.Content(role="user", parts=[types.Part(text=handbook_block(self.store))])]
        plan = {"adjudicate": (self.cfg.adjudicator, self.system(), toolset(self.cfg.toolset))}
        if self.cfg.reviewer:
            plan["review"] = (self.cfg.reviewer, REVIEWER_SYSTEM, [types.Tool(function_declarations=[SUBMIT])])
        for role, (model, system, tools) in plan.items():
            if model not in EXPLICIT_CACHE_MODELS:
                continue  # e.g. Gemini 4 Argon: relies on implicit caching of a static-first prompt
            name, tokens = self.gemini.create_cache(model, system, hb, tools, 3600,
                                                    f"tbom-{self.cfg.run_id.lower()}-{role}")
            self.caches[role] = {"name": name, "model": model, "tokens": tokens, "created": time.time(),
                                 "chars": {"system_prompt": len(system), "handbook": chars_of(hb[0]),
                                           "tool_schemas": schema_chars(tools)}}

    def delete_caches(self) -> tuple[float, float]:
        """Deletes the caches; returns (storage USD, creation USD)."""
        storage = creation = 0.0
        for c in self.caches.values():
            with contextlib.suppress(Exception):
                self.gemini.delete_cache(c["name"])
            hours = max(time.time() - c["created"], 60) / 3600
            storage += c["tokens"] / 1e6 * PRICES[c["model"]]["cache_storage_hour"] * hours
            creation += c["tokens"] / 1e6 * PRICES[c["model"]]["input"]  # cache writes bill as input
        return storage, creation

    def system(self) -> str:
        s = BASELINE_SYSTEM if self.cfg.output_style == "verbose" else OPTIMIZED_SYSTEM
        return s + (STRICT_LINE if self.cfg.strict_screening_prompt else "")

    # -- entry point -------------------------------------------------------------

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
                convo.to_history()  # earlier claims in the same chat become history
            tools, calls, t0 = Tools(self.store, self.cfg, claim["claim_ref"]), [], time.perf_counter()
            msg, hb = claim_text(claim), handbook_block(self.store)
            convo.user(f"{msg}\n\n{hb}", claim_input=len(msg), handbook=len(hb))
            with self.span(claim):
                result = self.loop(claim, convo, tools, calls, "adjudicate", self.cfg.adjudicator,
                                   self.cfg.adjudicator_thinking, self.system(), toolset(self.cfg.toolset))
            rows.append(self.finish(claim, result, tools, calls, t0, reviewed=False))
        return rows

    def tiered(self, claim):
        tools, calls, t0 = Tools(self.store, self.cfg, claim["claim_ref"]), [], time.perf_counter()
        with self.span(claim):
            try:
                facts = self.triage(claim, calls)
            except Exception as exc:  # noqa: BLE001 - adjudicator falls back to the raw message
                facts = {"summary": f"triage failed: {exc}"}
            req = (f"Claim {claim['claim_ref']}, filed {claim['received_at'][:10]}. Triage extracted: "
                   + "; ".join(f"{k}={facts.get(k)}" for k in
                               ("policy_id", "incident_date", "peril", "amount_claimed", "summary")))
            if not facts.get("policy_id"):
                req += "\n\nOriginal message:\n" + claim_text(claim)
            convo = Conversation()
            if self.cfg.handbook == "cached":
                convo.user(req, claim_input=len(req))
            else:
                hb = handbook_block(self.store)
                convo.user(f"{req}\n\n{hb}", claim_input=len(req), handbook=len(hb))
            result = self.loop(claim, convo, tools, calls, "adjudicate", self.cfg.adjudicator,
                               self.cfg.adjudicator_thinking, self.system(), toolset(self.cfg.toolset))
            reviewed = False
            draft = result.get("decision")
            if (self.cfg.reviewer and draft and not result.get("forced")
                    and float(draft.get("confidence") or 0) < self.cfg.review_below_confidence):
                reviewed = True
                gathered = [json.dumps(facts)] + [
                    str(p.function_response.response.get("result")) for c in convo.contents
                    for p in c.parts or [] if p.function_response and p.function_response.name != "submit_decision"]
                with contextlib.suppress(Exception):
                    result["decision"] = self.review(claim, gathered, draft, calls) or draft
        return self.finish(claim, result, tools, calls, t0, reviewed)

    def triage(self, claim, calls) -> dict:
        msg = claim_text(claim)
        config = types.GenerateContentConfig(
            system_instruction=TRIAGE_SYSTEM, response_mime_type="application/json",
            response_schema=TRIAGE_SCHEMA, labels=self.labels("triage", self.cfg.triage),
            thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"))
        resp = self.call(claim, "triage", self.cfg.triage, [types.Content(role="user", parts=[types.Part(text=msg)])],
                         config, calls, {"system_prompt": len(TRIAGE_SYSTEM),
                                         "tool_schemas": len(json.dumps(TRIAGE_SCHEMA)), "claim_input": len(msg)})
        return json.loads(resp.text or "{}")

    def review(self, claim, gathered, draft, calls):
        req = (f"Claim {claim['claim_ref']}.\nFacts gathered:\n" + "\n".join(f"- {g}" for g in gathered)
               + f"\n\nDraft decision: {draft}\nReturn the corrected decision with submit_decision.")
        fact_chars = sum(len(g) for g in gathered)
        items = {"claim_input": len(req) - fact_chars, "tool_results": fact_chars}
        think = types.ThinkingConfig(thinking_level="HIGH")
        if "review" in self.caches:
            config = types.GenerateContentConfig(cached_content=self.caches["review"]["name"],
                                                 thinking_config=think, labels=self.labels("review", self.cfg.reviewer))
            items.update(self.caches["review"]["chars"])
        else:
            tools = [types.Tool(function_declarations=[SUBMIT])]
            hb = handbook_block(self.store)
            if self.cfg.handbook == "cached":
                # No explicit cache on this model: put the static part FIRST so implicit
                # caching can reuse it across claims.
                system = f"{REVIEWER_SYSTEM}\n\n{hb}"
            else:
                system, req = REVIEWER_SYSTEM, f"{req}\n\n{hb}"
            config = types.GenerateContentConfig(
                system_instruction=system, tools=tools, thinking_config=think,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                labels=self.labels("review", self.cfg.reviewer))
            items.update({"system_prompt": len(REVIEWER_SYSTEM), "handbook": len(hb),
                          "tool_schemas": schema_chars(tools)})
        resp = self.call(claim, "review", self.cfg.reviewer,
                         [types.Content(role="user", parts=[types.Part(text=req)])], config, calls, items)
        return next((dict(fc.args or {}) for fc in resp.function_calls or [] if fc.name == "submit_decision"), None)

    def loop(self, claim, convo, tools, calls, step, model, thinking, system, decls) -> dict:
        """Call the model, run the tools it asks for, repeat until submit_decision."""
        cache = self.caches.get(step)
        for _ in range(self.cfg.max_calls):
            common = dict(thinking_config=types.ThinkingConfig(thinking_level=thinking),
                          automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                          labels=self.labels(step, model))
            if cache:  # system instruction, handbook and tools come from the cache
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
            except Exception as exc:  # noqa: BLE001 - recorded on the claim row
                return {"error": f"{type(exc).__name__}: {exc}"[:500]}
            if not resp.candidates or not resp.candidates[0].content:
                return {"error": "EMPTY_RESPONSE"}
            turn = resp.candidates[0].content  # re-sent as-is (keeps thought signatures)
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
        if self.cfg.loop_guard:  # the guard: stop paying and hand the claim to a human
            return {"decision": {"decision": "ESCALATE", "reason_code": "LOOP_GUARD", "payout_usd": None,
                                 "confidence": 0.0}, "forced": True}
        return {"error": "SAFETY_CAP_REACHED"}

    def call(self, claim, step, model, contents, config, calls, items) -> types.GenerateContentResponse:
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        span_cm = (self.tracer.start_as_current_span(f"gen_ai.{step}") if self.tracer
                   else contextlib.nullcontext())
        with span_cm as span:
            resp, latency = self.gemini.generate(model, contents, config)
            u = resp.usage_metadata or types.GenerateContentResponseUsageMetadata()
            row = {
                "run_tag": self.run_tag, "run_id": self.cfg.run_id, "claim_ref": claim["claim_ref"], "step": step,
                "call_index": len(calls), "model": model, "tier": TIER[model], "started_at": started,
                "latency_ms": latency, "traffic_type": str(getattr(u.traffic_type, "value", u.traffic_type) or ""),
                "prompt_tokens": u.prompt_token_count or 0, "cached_tokens": u.cached_content_token_count or 0,
                "output_tokens": u.candidates_token_count or 0, "thoughts_tokens": u.thoughts_token_count or 0,
                "function_calls": ",".join(fc.name for fc in resp.function_calls or []),
                "labels": json.dumps(config.labels or {}), "simulated": self.gemini.simulated,
            }
            row["cost_usd"] = token_cost(model, row["prompt_tokens"], row["cached_tokens"],
                                         row["output_tokens"], row["thoughts_tokens"])
            row.update({f"tbom_{k}": v for k, v in allocate(items, row["prompt_tokens"]).items()})
            if span is not None:  # token counts and cost on the Cloud Trace span
                for key, value in {"gen_ai.request.model": model, "gen_ai.usage.input_tokens": row["prompt_tokens"],
                                   "gen_ai.usage.output_tokens": row["output_tokens"] + row["thoughts_tokens"],
                                   "tbom.cached_tokens": row["cached_tokens"], "tbom.cost_usd": row["cost_usd"],
                                   "claim_ref": claim["claim_ref"]}.items():
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
            exp_decision == "DENY" or (payout is not None
                                       and abs(float(payout) - exp_payout) <= max(1.0, 0.01 * exp_payout)))
        row = {
            "run_tag": self.run_tag, "run_id": self.cfg.run_id, "claim_ref": claim["claim_ref"],
            "product": a["product"], "complexity": a["complexity"],
            "decision": d.get("decision"), "reason_code": d.get("reason_code"),
            "payout_usd": float(payout) if payout is not None else None,
            "confidence": float(d["confidence"]) if d.get("confidence") is not None else None,
            "expected_decision": exp_decision, "expected_reason": a["expected_reason" + sfx],
            "expected_payout": exp_payout, "correct": correct, "reviewed_by_frontier": reviewed,
            "llm_calls": len(calls), "tool_calls": tools.calls, "decoy_calls": tools.decoy_calls,
            "tool_failures": tools.failures, "fault_injected": tools.faulty,
            "guard_tripped": tools.guard_tripped or bool(result.get("forced")),
            "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
            "cached_tokens": sum(c["cached_tokens"] for c in calls),
            "output_tokens": sum(c["output_tokens"] for c in calls),
            "thoughts_tokens": sum(c["thoughts_tokens"] for c in calls),
            "cost_usd": sum(c["cost_usd"] for c in calls),
            "latency_ms": int((time.perf_counter() - t0) * 1000), "simulated": self.gemini.simulated,
            "error": result.get("error"),
        }
        self.out_claims.write(row)
        return row

    def labels(self, step, model) -> dict[str, str]:
        # Request labels flow into Cloud Billing (PayGo only). Keep values low-cardinality:
        # Cloud Billing keeps at most 1,000 unique values per label key.
        return {"app": "cymbal-claims", "experiment": "tbom", "run": self.cfg.run_id.lower(),
                "run_tag": self.run_tag, "step": step, "tier": TIER[model]}

    def span(self, claim):
        if not self.tracer:
            return contextlib.nullcontext()
        return self.tracer.start_as_current_span("claim", attributes={
            "claim_ref": claim["claim_ref"], "run": self.cfg.run_id})


# =============================================================================
# 7. Command line
# =============================================================================


def setup_tracer():
    """Optional: send spans to Cloud Trace (--trace), billed to GOOGLE_CLOUD_PROJECT."""
    import google.auth
    from google.cloud.trace_v2 import TraceServiceClient
    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    # Use the same project for quota, so a different quota project in local ADC can't break export.
    creds, _ = google.auth.default(quota_project_id=project)
    exporter = CloudTraceSpanExporter(project_id=project, client=TraceServiceClient(credentials=creds))
    provider = TracerProvider(resource=Resource.create({"service.name": "tbom-claims-demo"}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("tbom"), provider


def main(argv=None, gemini=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", default=["R0", "R1", "R2", "R3", "R5"], choices=list(RUNS))
    ap.add_argument("--n", type=int, default=50, help="claims per run (the same claims for every run)")
    ap.add_argument("--workers", type=int, default=4, help="claims processed in parallel")
    ap.add_argument("--max-usd", type=float, default=75.0, help="stop when the list-price estimate reaches this")
    ap.add_argument("--run-tag", default=os.environ.get("TBOM_RUN_TAG") or f"exp-{dt.date.today()}")
    ap.add_argument("--trace", action="store_true", help="also send spans to Cloud Trace")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,62}", args.run_tag):
        sys.exit("--run-tag: lowercase letters, digits, '-' or '_' only (it becomes a billing label)")

    store = Store()
    gemini = gemini or Gemini()
    tracer, provider = setup_tracer() if args.trace else (None, None)
    out = HERE / "results" / args.run_tag
    calls, claims_out, runs_out = Jsonl(out / "calls.jsonl"), Jsonl(out / "claims.jsonl"), Jsonl(out / "runs.jsonl")
    claims = store.claims[: args.n]
    spent, lock = 0.0, threading.Lock()
    print(f"run_tag={args.run_tag}  claims={len(claims)}  runs={args.runs}  ->  {out}")

    for run_id in args.runs:
        if spent >= args.max_usd:
            print(f"skipping {run_id}: --max-usd reached")
            continue
        cfg = RUNS[run_id]
        agent = Agent(cfg, store, gemini, args.run_tag, calls, claims_out, tracer)
        started = dt.datetime.now(dt.timezone.utc)
        agent.create_caches()
        batches = ([claims[i:i + 3] for i in range(0, len(claims), 3)] if cfg.session == "queue"
                   else [[c] for c in claims])
        rows: list[dict] = []
        try:
            with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = [pool.submit(agent.process, b) for b in batches]
                for fut in cf.as_completed(futures):
                    batch_rows = fut.result()
                    rows += batch_rows
                    with lock:
                        spent += sum(r["cost_usd"] for r in batch_rows)
                    if spent >= args.max_usd:
                        for f in futures:
                            f.cancel()
                        break
        finally:
            storage, creation = agent.delete_caches()
        spent += storage + creation
        runs_out.write({"run_tag": args.run_tag, "run_id": run_id, "title": cfg.title, "n_claims": len(rows),
                        "started_at": started.isoformat(),
                        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "cache_storage_usd": round(storage, 6), "cache_creation_usd": round(creation, 6),
                        "simulated": gemini.simulated})
        n = len(rows) or 1
        ok = sum(r["correct"] for r in rows)
        llm = sum(r["cost_usd"] for r in rows) + storage + creation
        prompt = sum(r["prompt_tokens"] for r in rows)
        print(f"{run_id:4s} {cfg.title[:40]:40s} claims={len(rows):3d} accuracy={ok / n:6.1%} "
              f"tokens/claim={(prompt + sum(r['output_tokens'] + r['thoughts_tokens'] for r in rows)) / n:9,.0f} "
              f"cached={sum(r['cached_tokens'] for r in rows) / max(prompt, 1):4.0%} "
              f"$/claim={llm / n:.4f} errors={sum(1 for r in rows if r['error'])}")
    if provider:
        provider.shutdown()
    print(f"List-price estimate for this invocation: ${spent:,.2f}.  Next: upload {out} to BigQuery (RUNBOOK step 6).")


if __name__ == "__main__":
    main()
