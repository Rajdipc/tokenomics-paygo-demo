"""Token Bill of Materials (TBOM) pricing, token allocation, and ADK telemetry plugin.

Every Gemini call reports exact billed totals in ``usage_metadata``:
  - ``prompt_token_count`` (total input tokens, including cached)
  - ``cached_content_token_count`` (portion of input billed at cached rate)
  - ``candidates_token_count`` (visible output tokens)
  - ``thoughts_token_count`` (internal reasoning tokens, billed at output rate)

This module provides:
  1. ``PRICES`` and ``token_cost()``: list-price calculation on Standard PayGo.
  2. ``allocate()``: proportional character-weighted split of ``prompt_token_count``
     across the six TBOM line items so the parts sum *exactly* to the billed prompt tokens.
  3. ``TBOMLedgerPlugin``: a Google ADK ``BasePlugin`` that automatically attaches
     low-cardinality Cloud Billing labels before each model call and records an
     itemized TBOM row in ``session.state["tbom_calls"]`` after each model call.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from typing import Any

from google.genai import types

# =============================================================================
# 1. Generally Available (GA) models and Standard PayGo list prices
# =============================================================================

FRONTIER = "gemini-4-argon"
FLASH = "gemini-3.8-flash"
FLASH_LITE = "gemini-3.5-flash-lite"

TIER = {
    FRONTIER: "frontier",
    FLASH: "flash",
    FLASH_LITE: "flash-lite",
}

# Gemini 4 Argon supports implicit context caching only (no explicit caches).
EXPLICIT_CACHE_MODELS = {FLASH, FLASH_LITE}

# Standard PayGo list prices, global endpoint, prompts <= 200K tokens, USD per 1M tokens.
# Source: https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
# As of 2026-10-15. Keep in sync with sql/00_reference_tables.sql.
PRICES: dict[str, dict[str, float | None]] = {
    FRONTIER: {"input": 4.00, "cached": 0.20, "output": 20.00, "cache_storage_hour": None},
    FLASH: {"input": 1.50, "cached": 0.15, "output": 7.50, "cache_storage_hour": 1.00},
    FLASH_LITE: {"input": 0.30, "cached": 0.03, "output": 2.50, "cache_storage_hour": 1.00},
}

LINE_ITEMS = (
    "system_prompt",
    "handbook",
    "tool_schemas",
    "history",
    "tool_results",
    "claim_input",
)


def token_cost(model: str, prompt: int, cached: int, output: int, thoughts: int) -> float:
    """Cost of one Gemini call in USD.

    ``prompt`` includes ``cached`` tokens; ``thoughts`` (thinking tokens) bill at
    the model's output rate.
    """
    p = PRICES.get(model) or PRICES[FLASH]
    in_rate = float(p["input"] or 0.0)
    cached_rate = float(p["cached"] or 0.0)
    out_rate = float(p["output"] or 0.0)
    return (
        max(0, prompt - cached) * in_rate
        + cached * cached_rate
        + (output + thoughts) * out_rate
    ) / 1_000_000


def allocate(chars: dict[str, int], prompt_tokens: int) -> dict[str, int]:
    """Split ``prompt_tokens`` across ``LINE_ITEMS`` in proportion to character counts.

    Uses largest-remainder rounding so the six integer line items always sum
    *exactly* to ``prompt_tokens``.
    """
    sizes = {k: max(0, int(chars.get(k, 0))) for k in LINE_ITEMS}
    total = sum(sizes.values())
    if not total or prompt_tokens <= 0:
        return dict.fromkeys(LINE_ITEMS, 0)
    raw = {k: prompt_tokens * v / total for k, v in sizes.items()}
    out = {k: int(v) for k, v in raw.items()}
    remainder = prompt_tokens - sum(out.values())
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:remainder]:
        out[k] += 1
    return out


def build_labels(step: str, model: str, run_id: str = "r5", run_tag: str | None = None) -> dict[str, str]:
    """Low-cardinality Cloud Billing labels for a Gemini request (AGENTS.md Rule #1)."""
    tag = (run_tag or os.environ.get("TBOM_RUN_TAG") or "prod").lower()[:62]
    tier = TIER.get(model, "flash")
    return {
        "app": "cymbal-claims",
        "experiment": "tbom",
        "run": run_id.lower(),
        "run_tag": tag,
        "step": step.lower().replace("_agent", ""),
        "tier": tier,
    }


def _estimate_request_chars(llm_request: Any) -> dict[str, int]:
    """Inspect an ADK ``LlmRequest`` and estimate character sizes for each TBOM line item."""
    chars = dict.fromkeys(LINE_ITEMS, 0)
    config = getattr(llm_request, "config", None)
    if config:
        sys_inst = getattr(config, "system_instruction", None)
        if not isinstance(sys_inst, str) and sys_inst is not None:
            parts = getattr(sys_inst, "parts", None) or []
            sys_inst = "\n".join(getattr(p, "text", "") or "" for p in parts)
        if isinstance(sys_inst, str) and sys_inst:
            if "<handbook>" in sys_inst and "</handbook>" in sys_inst:
                start = sys_inst.index("<handbook>")
                end = sys_inst.index("</handbook>") + len("</handbook>")
                chars["handbook"] += end - start
                chars["system_prompt"] += max(0, len(sys_inst) - (end - start))
            else:
                chars["system_prompt"] += len(sys_inst)
        tools = getattr(config, "tools", None)
        if tools:
            chars["tool_schemas"] += len(
                json.dumps([t.model_dump(exclude_none=True) for t in tools if hasattr(t, "model_dump")], default=str)
            )
    tools_dict = getattr(llm_request, "tools_dict", None)
    if tools_dict and chars["tool_schemas"] == 0:
        chars["tool_schemas"] += sum(len(str(k)) + len(str(getattr(v, "description", ""))) + 120 for k, v in tools_dict.items())
    contents = getattr(llm_request, "contents", None) or []
    for idx, content in enumerate(contents):
        is_last = idx == len(contents) - 1
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "text", None):
                txt = part.text
                if "<handbook>" in txt and "</handbook>" in txt:
                    start = txt.index("<handbook>")
                    end = txt.index("</handbook>") + len("</handbook>")
                    chars["handbook"] += end - start
                    rem = len(txt) - (end - start)
                    chars["claim_input" if is_last else "history"] += max(0, rem)
                elif is_last and getattr(content, "role", "") == "user":
                    chars["claim_input"] += len(txt)
                else:
                    chars["history"] += len(txt)
            elif getattr(part, "function_call", None):
                chars["history"] += len(json.dumps(part.function_call.args or {}, default=str))
            elif getattr(part, "function_response", None):
                chars["tool_results"] += len(json.dumps(part.function_response.response or {}, default=str))
    return chars


try:
    from google.adk.plugins.base_plugin import BasePlugin
except ImportError:  # pragma: no cover - fallback when google-adk is not installed
    class BasePlugin:  # type: ignore[no-redef]
        def __init__(self, name: str = "tbom"):
            self.name = name


class TBOMLedgerPlugin(BasePlugin):
    """Google ADK plugin that meters every model call into an itemized TBOM ledger."""

    def __init__(self, run_id: str = "R5", run_tag: str | None = None):
        super().__init__(name="tbom_ledger")
        self.run_id = run_id
        self.run_tag = run_tag or os.environ.get("TBOM_RUN_TAG") or "adk-live"
        self._pending: dict[str, tuple[float, dict[str, int], str, dict[str, str]]] = {}

    @staticmethod
    def _ctx_key(callback_context: Any) -> str:
        inv = getattr(callback_context, "_invocation_context", None)
        inv_id = getattr(inv, "invocation_id", None) or "default"
        agent_name = getattr(callback_context, "agent_name", None) or "agent"
        return f"{inv_id}:{agent_name}"

    async def before_model_callback(self, *, callback_context: Any, llm_request: Any) -> None:
        step = getattr(callback_context, "agent_name", "adjudicate") or "adjudicate"
        model = str(getattr(llm_request, "model", None) or FLASH)
        labels = build_labels(step=step, model=model, run_id=self.run_id, run_tag=self.run_tag)
        if getattr(llm_request, "config", None) is not None:
            existing = dict(getattr(llm_request.config, "labels", None) or {})
            existing.update(labels)
            llm_request.config.labels = existing
        chars = _estimate_request_chars(llm_request)
        self._pending[self._ctx_key(callback_context)] = (time.perf_counter(), chars, model, labels)
        return None

    async def after_model_callback(self, *, callback_context: Any, llm_response: Any) -> None:
        t0, chars, model, labels = self._pending.pop(
            self._ctx_key(callback_context),
            (time.perf_counter(), dict.fromkeys(LINE_ITEMS, 0), FLASH, {}),
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        u = getattr(llm_response, "usage_metadata", None) or types.GenerateContentResponseUsageMetadata()
        prompt_tokens = int(getattr(u, "prompt_token_count", 0) or 0)
        cached_tokens = int(getattr(u, "cached_content_token_count", 0) or 0)
        output_tokens = int(getattr(u, "candidates_token_count", 0) or 0)
        thoughts_tokens = int(getattr(u, "thoughts_token_count", 0) or 0)

        fcs: list[str] = []
        content = getattr(llm_response, "content", None)
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "function_call", None) and getattr(part.function_call, "name", None):
                fcs.append(part.function_call.name)

        calls = list(callback_context.state.get("tbom_calls") or [])
        claim_ref = str(callback_context.state.get("claim_ref") or "CLM-ADK")
        step = (getattr(callback_context, "agent_name", "adjudicate") or "adjudicate").replace("_agent", "")
        row: dict[str, Any] = {
            "run_tag": self.run_tag,
            "run_id": self.run_id,
            "claim_ref": claim_ref,
            "step": step,
            "call_index": len(calls),
            "model": model,
            "tier": TIER.get(model, "flash"),
            "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "latency_ms": latency_ms,
            "traffic_type": str(getattr(u, "traffic_type", "ON_DEMAND") or "ON_DEMAND"),
            "prompt_tokens": prompt_tokens,
            "cached_tokens": cached_tokens,
            "output_tokens": output_tokens,
            "thoughts_tokens": thoughts_tokens,
            "function_calls": ",".join(fcs),
            "labels": json.dumps(labels),
            "simulated": False,
            "cost_usd": token_cost(model, prompt_tokens, cached_tokens, output_tokens, thoughts_tokens),
        }
        row.update({f"tbom_{k}": v for k, v in allocate(chars, prompt_tokens).items()})
        calls.append(row)
        callback_context.state["tbom_calls"] = calls
        return None
