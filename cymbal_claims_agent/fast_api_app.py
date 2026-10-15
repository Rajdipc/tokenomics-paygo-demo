"""FastAPI serving entrypoint for Cloud Run and Gemini Platform Agent Runtime (Agent Engine).

Serves:
  - ``GET /api/health``: readiness check showing loaded ``SKILL.md``, active GA models,
    and the 4 scoped tools.
  - ``POST /api/adjudicate``: adjudicates a claim by ``claim_ref`` (e.g. ``"CLM-000001"``)
    or raw ``claim_text`` using the Google ADK R5 ``SequentialAgent`` and returns both
    the structured decision and the live itemized **Token Bill of Materials (TBOM)** receipt.
  - Standard Google ADK routes (``/run``, ``/run_sse``, ``/apps/cymbal_claims_agent/...``)
    and ADK Developer Web UI (``/``).
  - Gemini Platform Agent Runtime (``reasoning_engine``) contract routes
    (``POST /api/reasoning_engine`` and ``POST /api/stream_reasoning_engine``).
"""

from __future__ import annotations

import inspect
import json
import os
import pathlib
from typing import Any

from fastapi import FastAPI, HTTPException, Request, encoders, responses
from pydantic import BaseModel, Field

from .agent import adjudicate_claim_with_adk
from .tbom import FLASH, FLASH_LITE, FRONTIER
from .tools import SKILL_PATH, get_default_store

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent

try:
    from google.adk.cli.fast_api import get_fast_api_app

    app: FastAPI = get_fast_api_app(
        agents_dir=str(ROOT_DIR),
        web=os.environ.get("ADK_WEB", "true").lower() in ("true", "1", "yes"),
    )
except Exception:  # pragma: no cover - fallback minimal FastAPI app
    app = FastAPI()

app.title = "Cymbal Claims TBOM Agent (R5)"
app.description = (
    "Production R5 Cymbal Insurance Claims Agent built with Google ADK on Gemini Platform "
    "(Gemini 3.5 Flash-Lite triage -> Gemini 3.8 Flash adjudication -> Gemini 4 Argon review) "
    "with real-time Token Bill of Materials (TBOM) metering."
)


class AdjudicateRequest(BaseModel):
    claim_ref: str | None = Field(
        default="CLM-000001",
        description="Synthetic claim reference from data/incoming_claims.jsonl (e.g. CLM-000001).",
    )
    claim_text: str | None = Field(
        default=None,
        description="Optional custom claim email text (overrides claim_ref lookup if provided).",
    )
    inject_faults: bool = Field(
        default=False,
        description="If true, simulates upstream fraud-screening timeouts on every 5th claim to test R4G loop guards.",
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Readiness and configuration check for Cloud Run and Agent Runtime."""
    store = get_default_store()
    return {
        "ok": True,
        "app": "cymbal_claims_agent",
        "design": "R5 (Tiered Models + Static-First Context Caching + Loop Guards + TBOM Ledger)",
        "skill_loaded": SKILL_PATH.exists() and bool(store.skill_markdown),
        "skill_path": "skills/cymbal-claims-adjudication/SKILL.md",
        "models": {
            "triage": FLASH_LITE,
            "adjudicator": FLASH,
            "reviewer": FRONTIER,
        },
        "tools": ["get_policy", "get_claims_history", "screen_fraud", "submit_decision"],
        "synthetic_records": {
            "customers": len(store.customers),
            "policies": len(store.policies),
            "incoming_claims": len(store.claims),
        },
    }


@app.post("/api/adjudicate")
async def adjudicate_endpoint(req: AdjudicateRequest) -> dict[str, Any]:
    """Run a claim through the Google ADK R5 agent and return the decision + live TBOM receipt."""
    return await adjudicate_claim_with_adk(
        claim_ref=req.claim_ref,
        claim_text_override=req.claim_text,
        inject_faults=req.inject_faults,
    )


# -----------------------------------------------------------------------------
# Gemini Platform Agent Runtime (Vertex AI Agent Engine) HTTP adapter routes
# -----------------------------------------------------------------------------


def _attach_reasoning_engine_routes(fastapi_app: FastAPI) -> None:
    runtime: Any = None
    streaming_methods: set[str] = set()
    sync_methods: set[str] = set()

    def get_runtime():
        nonlocal runtime, streaming_methods, sync_methods
        if runtime is None:
            from vertexai.agent_engines.templates.adk import AdkApp
            from .agent import app as adk_app

            runtime = AdkApp(app=adk_app)
            runtime.set_up()
            ops = runtime.register_operations()
            streaming_methods = set(ops.get("stream", [])) | set(ops.get("async_stream", []))
            sync_methods = set(ops.get("", [])) | set(ops.get("async", []))
        return runtime

    @fastapi_app.post("/api/stream_reasoning_engine")
    async def stream_query(request: Request) -> responses.StreamingResponse:
        body = await request.json()
        rt = get_runtime()
        method_name = body.get("class_method", "async_stream_query")
        if method_name not in streaming_methods:
            raise HTTPException(status_code=404, detail=f"Unsupported streaming method: {method_name!r}")
        method = getattr(rt, method_name)

        async def generator():
            async for event in method(**(body.get("input") or {})):
                yield json.dumps(event, default=str) + "\n"

        return responses.StreamingResponse(content=generator(), media_type="application/json")

    @fastapi_app.post("/api/reasoning_engine")
    async def query(request: Request) -> responses.JSONResponse:
        body = await request.json()
        rt = get_runtime()
        method_name = body.get("class_method", "query")
        if method_name not in sync_methods:
            raise HTTPException(status_code=404, detail=f"Unsupported method: {method_name!r}")
        method = getattr(rt, method_name)
        kwargs = body.get("input") or {}
        output = await method(**kwargs) if inspect.iscoroutinefunction(method) else method(**kwargs)
        return responses.JSONResponse(content=encoders.jsonable_encoder({"output": output}))


_attach_reasoning_engine_routes(app)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
