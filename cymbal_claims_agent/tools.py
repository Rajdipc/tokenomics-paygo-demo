"""Synthetic data store, domain tools, and Google ADK FunctionTools for Cymbal Insurance.

Implements:
  - ``Store``: loads the synthetic Cymbal Insurance records (customers, policies,
    60K historical claims, 5K incoming claim emails, answer key, and the 20K-token
    Claims Adjudication Handbook) plus the ``skills/cymbal-claims-adjudication/SKILL.md``
    skill definition.
  - ``Tools``: executes tool calls for a single claim with deterministic policy-ID
    normalization (``AGENTS.md`` Rule #3: ``"policy no. 003009" -> "POL-003009"``)
    and a per-tool retry circuit breaker (``AGENTS.md`` Rule #4: ``retry_budget=1``).
  - Standalone Google ADK tool callables (``get_policy``, ``get_claims_history``,
    ``screen_fraud``, ``submit_decision``) with full type annotations and docstrings
    for ``google.adk.agents.Agent``.
"""

from __future__ import annotations

import csv
import datetime as dt
import functools
import json
import pathlib
import random
import re
from typing import Any

from google.genai import types

try:
    from google.adk.tools import ToolContext
except (ImportError, AttributeError):  # pragma: no cover
    ToolContext = Any  # type: ignore[misc,assignment]

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SKILL_PATH = ROOT_DIR / "skills" / "cymbal-claims-adjudication" / "SKILL.md"


def read_csv(name: str, data_dir: pathlib.Path = DATA_DIR) -> list[dict]:
    with (data_dir / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Store:
    """The synthetic Cymbal Insurance dataset and skill metadata, held in memory."""

    def __init__(self, data_dir: pathlib.Path = DATA_DIR):
        self.data_dir = data_dir
        self.customers = {r["customer_id"]: r for r in read_csv("customers.csv", data_dir)}
        self.policies = {r["policy_id"]: r for r in read_csv("policies.csv", data_dir)}
        self.history: dict[str, list[dict]] = {}
        for r in read_csv("claims_history.csv", data_dir):
            self.history.setdefault(r["customer_id"], []).append(r)
        self.claims = [
            json.loads(x)
            for x in (data_dir / "incoming_claims.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.claims_by_ref = {c["claim_ref"]: c for c in self.claims}
        self.answers = {r["claim_ref"]: r for r in read_csv("answer_key.csv", data_dir)}
        self.handbook = (data_dir / "policy_handbook.md").read_text(encoding="utf-8")
        self.skill_markdown = SKILL_PATH.read_text(encoding="utf-8") if SKILL_PATH.exists() else ""


@functools.lru_cache(maxsize=1)
def get_default_store() -> Store:
    """Process-wide singleton Store for ADK serving on Cloud Run and Agent Runtime."""
    return Store()


# =============================================================================
# Tool Declarations for run_experiment.py (R0 25-tool vs R1+ 3-tool comparison)
# =============================================================================


def decl(name: str, description: str, props: dict, required: list[str]) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters={"type": "OBJECT", "properties": props, "required": required},
    )


S, N, I = {"type": "STRING"}, {"type": "NUMBER"}, {"type": "INTEGER"}

GET_POLICY = decl(
    "get_policy",
    "Fetch the policy record (product, plan, status, term dates, limits, deductible, riders).",
    {"policy_id": S},
    ["policy_id"],
)
GET_HISTORY = decl(
    "get_claims_history",
    "List the customer's prior claims before a date of loss.",
    {"customer_id": S, "as_of_date": S, "lookback_days": I},
    ["customer_id", "as_of_date"],
)
SCREEN = decl(
    "screen_fraud",
    "Run fraud screening. Returns an advisory score from 0 to 100.",
    {"policy_id": S, "peril": S, "amount_claimed": N},
    ["policy_id", "peril", "amount_claimed"],
)
SUBMIT = decl(
    "submit_decision",
    "Record the final decision. Call exactly once.",
    {
        "claim_ref": S,
        "decision": {"type": "STRING", "enum": ["APPROVE", "DENY", "ESCALATE"]},
        "reason_code": S,
        "payout_usd": N,
        "peril": S,
        "confidence": N,
        "justification": S,
    },
    ["claim_ref", "decision", "reason_code", "payout_usd", "peril", "confidence", "justification"],
)

# 22 plausible but irrelevant tools used in R0 to measure tool-schema bloat.
DECOYS = [
    decl(n, d, {p: {"type": "STRING", "description": p.replace("_", " ")} for p in ps}, ps[:1])
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
    ]
]


def toolset(name: str) -> list[types.Tool]:
    """Return the Gen AI SDK Tool list for ``"relevant"`` (R1+) or ``"all"`` (R0)."""
    decls = [GET_POLICY, GET_HISTORY, SCREEN] + (DECOYS if name == "all" else []) + [SUBMIT]
    return [types.Tool(function_declarations=decls)]


def schema_chars(tools: list[types.Tool] | None) -> int:
    return len(json.dumps([t.model_dump(exclude_none=True) for t in tools or []], default=str))


# =============================================================================
# Core Tool Executor (shared by ADK FunctionTools and run_experiment.py)
# =============================================================================


class Tools:
    """Executes the tools for ONE claim; injects faults and applies the retry budget."""

    def __init__(self, store: Store, cfg: Any, claim_ref: str):
        self.store, self.cfg = store, cfg
        self.faulty = bool(getattr(cfg, "faults", False)) and (
            claim_ref[-6:].isdigit() and int(claim_ref[-6:]) % 5 == 0
        )
        self.calls = self.failures = self.decoy_calls = 0
        self.screening_down = self.guard_tripped = False

    @staticmethod
    def norm_policy_id(raw: Any) -> str:
        """AGENTS.md Rule #3: normalize 6-digit references ('policy no. 003009' -> 'POL-003009')."""
        s = str(raw or "").strip().upper()
        m = re.search(r"(\d{6})", s)
        return f"POL-{m.group(1)}" if m else s

    def run(self, name: str, args: dict) -> str:
        self.calls += 1
        try:
            if name == "get_policy":
                return self.policy(self.norm_policy_id(args.get("policy_id", "")))
            if name == "get_claims_history":
                return self.claims_history(
                    str(args.get("customer_id", "")).strip().upper(),
                    str(args.get("as_of_date", ""))[:10],
                    int(args.get("lookback_days") or 365),
                )
            if name == "screen_fraud":
                return self.screen(
                    self.norm_policy_id(args.get("policy_id", "")),
                    float(args.get("amount_claimed") or 0),
                )
        except (TypeError, ValueError) as exc:
            return self.dump({"status": "ERROR", "error": f"bad arguments: {exc}"})
        self.decoy_calls += 1
        return self.dump({
            "status": "OK",
            "tool": name,
            "note": "Informational only.",
            "results": [{"id": f"R{k}", "value": round(random.random(), 4)} for k in range(5)],
        })

    def policy(self, policy_id: str) -> str:
        row = self.store.policies.get(policy_id)
        if row is None:
            return self.dump({"status": "NOT_FOUND", "policy_id": policy_id})
        riders = row["riders"].replace("|", ", ") or "none"
        if getattr(self.cfg, "tool_output", "compact") == "compact":
            return (
                "| policy_id | customer_id | product | plan | status | start | end | coverage_limit | deductible | riders |\n"
                "|---|---|---|---|---|---|---|---|---|---|\n"
                f"| {row['policy_id']} | {row['customer_id']} | {row['product']} | {row['plan']} | {row['status']} "
                f"| {row['start_date']} | {row['end_date']} | {row['coverage_limit']} | {row['deductible']} | {riders} |"
            )
        rng = random.Random(policy_id)
        return self.dump({
            "status": "OK",
            "policy": {**row, "riders": riders.split(", ")},
            "customer": self.store.customers.get(row["customer_id"], {}),
            "billing_history": [
                {"period": k, "amount_due": round(rng.uniform(25, 180), 2), "status": rng.choice(["PAID", "PAID", "LATE"])}
                for k in range(12)
            ],
            "agent_notes": ["Customer prefers e-mail contact.", "Verified identity at onboarding."],
            "audit": {"source_system": "PAS-7", "record_version": rng.randint(1, 30), "etag": f"{rng.getrandbits(64):016x}"},
        })

    def claims_history(self, customer_id: str, as_of: str, lookback: int) -> str:
        try:
            day = dt.date.fromisoformat(as_of)
        except ValueError:
            return self.dump({"status": "ERROR", "error": "as_of_date must be YYYY-MM-DD"})
        before = [r for r in self.store.history.get(customer_id, []) if r["incident_date"] < as_of]
        start = (day - dt.timedelta(days=lookback)).isoformat()
        window = [r for r in before if r["incident_date"] >= start]
        if getattr(self.cfg, "tool_output", "compact") == "compact":
            return (
                f"Prior claims with date of loss in the {lookback} days before {as_of}: **{len(window)}**\n"
                + "\n".join(
                    f"- {r['incident_date']} {r['product']} {r['peril']} {r['outcome']}"
                    for r in sorted(window, key=lambda r: r["incident_date"])[-3:]
                )
            )
        return self.dump({"status": "OK", "customer_id": customer_id, "claims": before})

    def screen(self, policy_id: str, amount: float) -> str:
        if self.faulty:
            self.failures += 1
            self.screening_down = True
            retry_budget = getattr(self.cfg, "retry_budget", None)
            if retry_budget is not None and self.failures > retry_budget:
                self.guard_tripped = True
                return self.dump({
                    "status": "UNAVAILABLE",
                    "retryable": False,
                    "message": (
                        "Fraud screening is unavailable after 1 retry. Do not call screen_fraud "
                        "again. Apply handbook Section 2 in order: if steps 1-5 do not deny the "
                        "claim, use step 6 (SCREENING_UNAVAILABLE)."
                    ),
                })
            return self.dump({
                "status": "ERROR",
                "error": "UPSTREAM_TIMEOUT",
                "retryable": True,
                "message": "Transient timeout; retry screen_fraud.",
            })
        rng = random.Random(f"{policy_id}:{amount:.2f}")
        score = rng.randint(1, 95)
        if getattr(self.cfg, "tool_output", "compact") == "compact":
            return f"fraud_score={score} (advisory)"
        return self.dump({
            "status": "OK",
            "screening": {
                "score": score,
                "model_version": "fraudnet-2026.09",
                "features": {f"f{k:02d}": round(rng.random(), 4) for k in range(24)},
            },
        })

    def dump(self, obj: Any) -> str:
        if getattr(self.cfg, "tool_output", "compact") == "compact":
            return json.dumps(obj, separators=(",", ":"), default=str)
        return json.dumps(obj, indent=2, default=str)


# =============================================================================
# Google ADK FunctionTool Callables (used by cymbal_claims_agent.agent.root_agent)
# =============================================================================


class _CompactConfig:
    tool_output = "compact"
    faults = False
    retry_budget = 1


def _tools_for_context(tool_context: ToolContext | None = None) -> Tools:
    store = get_default_store()
    claim_ref = "CLM-000001"
    faults = False
    if tool_context is not None and hasattr(tool_context, "state"):
        claim_ref = str(tool_context.state.get("claim_ref") or "CLM-000001")
        faults = bool(tool_context.state.get("inject_faults", False))
    cfg = _CompactConfig()
    cfg.faults = faults
    t = Tools(store, cfg, claim_ref)
    if tool_context is not None and hasattr(tool_context, "state"):
        t.failures = int(tool_context.state.get("screen_failures", 0))
    return t


def get_policy(policy_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Fetch the compact policy record (product, plan, status, term dates, limits, deductible, riders).

    Args:
        policy_id: Policy identifier such as POL-003009 (6-digit strings are normalized automatically).

    Returns:
        dict with 'status' and compact Markdown 'result' table.
    """
    t = _tools_for_context(tool_context)
    normalized = t.norm_policy_id(policy_id)
    res = t.policy(normalized)
    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["tool_calls"] = int(tool_context.state.get("tool_calls", 0)) + 1
    return {"status": "OK", "policy_id": normalized, "result": res}


def get_claims_history(customer_id: str, as_of_date: str, lookback_days: int, tool_context: ToolContext) -> dict[str, Any]:
    """List the customer's prior claims in the lookback window before the date of loss.

    Args:
        customer_id: Customer identifier (e.g., CUS-001234) from get_policy.
        as_of_date: Incident date in YYYY-MM-DD format.
        lookback_days: Number of days to look back (use 365 per handbook Section 2 Step 5).

    Returns:
        dict with 'status' and compact summary of prior claims in the window.
    """
    t = _tools_for_context(tool_context)
    res = t.claims_history(str(customer_id).strip().upper(), str(as_of_date)[:10], int(lookback_days or 365))
    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["tool_calls"] = int(tool_context.state.get("tool_calls", 0)) + 1
    return {"status": "OK", "result": res}


def screen_fraud(policy_id: str, peril: str, amount_claimed: float, tool_context: ToolContext) -> dict[str, Any]:
    """Run advisory fraud screening for a claim. Enforces a retry_budget=1 circuit breaker on upstream timeouts.

    Args:
        policy_id: Policy identifier (e.g., POL-003009).
        peril: Peril code from the claim (e.g., COLLISION, WATER_DAMAGE).
        amount_claimed: Claimed loss amount in USD.

    Returns:
        dict with 'result' containing the advisory fraud_score or circuit-breaker fallback instructions.
    """
    t = _tools_for_context(tool_context)
    res = t.screen(t.norm_policy_id(policy_id), float(amount_claimed or 0.0))
    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["tool_calls"] = int(tool_context.state.get("tool_calls", 0)) + 1
        tool_context.state["screen_failures"] = t.failures
        tool_context.state["screening_down"] = t.screening_down
        tool_context.state["guard_tripped"] = t.guard_tripped
    return {"status": "OK", "peril": peril, "result": res}


def submit_decision(
    claim_ref: str,
    decision: str,
    reason_code: str,
    payout_usd: float,
    peril: str,
    confidence: float,
    justification: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Record the final claim adjudication decision. Call exactly once per claim.

    Args:
        claim_ref: Claim reference ID (e.g., CLM-000001).
        decision: Final decision, one of APPROVE, DENY, or ESCALATE.
        reason_code: Handbook reason code (e.g., APPROVED, POLICY_INACTIVE, PERIL_EXCLUDED, SCREENING_UNAVAILABLE).
        payout_usd: Net payout in USD after deductible and sublimits (use 0 for DENY).
        peril: Normalized peril code.
        confidence: Confidence score between 0.0 and 1.0.
        justification: Concise justification (at most 40 words) citing the handbook step and payout arithmetic.

    Returns:
        dict confirming the decision was recorded.
    """
    payload = {
        "claim_ref": claim_ref,
        "decision": str(decision).strip().upper(),
        "reason_code": str(reason_code).strip().upper(),
        "payout_usd": float(payout_usd),
        "peril": str(peril).strip().upper(),
        "confidence": float(confidence),
        "justification": str(justification).strip(),
    }
    if tool_context is not None and hasattr(tool_context, "state"):
        tool_context.state["submitted_decision"] = payload
    return {"status": "recorded", "decision": payload}
