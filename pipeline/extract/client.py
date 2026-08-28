"""The OpenRouter client.

OpenRouter exposes an OpenAI-compatible chat-completions endpoint; this module talks to it through
the `openai` package's async client pointed at OpenRouter's base URL, never at a provider SDK.
There is no Anthropic API key anywhere in this project and this module does not read one - the
model name is a setting (`settings.llm_model`), not a constant, so switching models needs no code
change.

Signatures and the usage-block shape were read from the openai package actually pinned by this
project's lockfile (openai==3.5.0, installed under .venv/Lib/site-packages/openai), not from
memory: AsyncOpenAI(api_key=..., base_url=...), chat.completions.create(tools=[...],
tool_choice={"type": "function", "function": {"name": ...}}) to force the tool call, and the
response's usage.prompt_tokens / usage.completion_tokens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from core.logging import get_logger
from core.settings import Settings, get_settings
from openai import AsyncOpenAI

from pipeline.extract.prompt import PROMPT_VERSION, STATEMENT_TOOL, STATEMENT_TOOL_NAME, ReportInput, build_messages

log = get_logger("extract.client")

# Prices read from openrouter.ai/models for anthropic/claude-sonnet-5 on 2026-08-28. USD per
# 1,000,000 tokens. Update this dict (and the date in this comment) when the model or its price
# changes - nothing here re-derives it from a live API call, so a stale entry fails silently
# unless someone checks the date.
PRICING_USD_PER_MILLION_TOKENS: dict[str, dict[str, Decimal]] = {
    "anthropic/claude-sonnet-5": {"input": Decimal("2"), "output": Decimal("10")},
}
_MILLION = Decimal(1_000_000)


@dataclass(frozen=True)
class ExtractionResult:
    """What one extract() call produced: the raw claims plus what they cost."""

    claims: list[dict[str, Any]]
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = field(default_factory=lambda: Decimal("0"))


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> Decimal:
    """USD cost of one call, from the pinned price table. Unknown models cost 0 rather than crash
    a run over a pricing gap - the run's own tokens_in/tokens_out are still recorded either way."""
    prices = PRICING_USD_PER_MILLION_TOKENS.get(model)
    if prices is None:
        return Decimal("0")
    return (Decimal(tokens_in) * prices["input"] + Decimal(tokens_out) * prices["output"]) / _MILLION


def _build_client(settings: Settings) -> AsyncOpenAI:
    if settings.openrouter_api_key is None:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
    return AsyncOpenAI(
        api_key=settings.openrouter_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
    )


def _statements(raw: Any) -> list[dict[str, Any]]:
    """Normalise whatever the model put in `statements` into a list of claim dicts.

    The tool schema asks for an array of objects. A live run returned it as a JSON *string*
    containing that array - some models and gateways serialise nested structures inside tool
    arguments rather than nesting them. The recorded fixture had a real list, so no test saw it,
    and the job crashed with "dictionary update sequence element #0 has length 1" because
    list.extend over a string iterates its characters.

    Anything that is not a dict after normalising is dropped with a log line rather than guessed
    at. A malformed claim has no quote we can verify, and inventing structure for it would put an
    unverifiable statement in front of a reader - which is the one thing this pipeline exists to
    prevent.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("statements_not_json", extra={"preview": raw[:120]})
            return []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        log.warning("statements_unexpected_type", extra={"type": type(raw).__name__})
        return []

    claims = [item for item in raw if isinstance(item, dict)]
    dropped = len(raw) - len(claims)
    if dropped:
        log.warning("statements_non_object_entries_dropped", extra={"dropped": dropped})
    return claims


async def extract(report: ReportInput, *, openai_client: AsyncOpenAI | None = None) -> ExtractionResult:
    """Call the model once for one report and return its claims plus cost.

    The only network call in this module. jobs/extract.py calls this once per report, gated by
    MAX_REPORTS_PER_RUN and MAX_RUN_COST_USD - never in a loop over claims, because claims do not
    exist yet at the point this function is called.
    """
    settings = get_settings()
    active_client = openai_client or _build_client(settings)

    response = await active_client.chat.completions.create(
        model=settings.llm_model,
        messages=build_messages(report),
        tools=[STATEMENT_TOOL],
        tool_choice={"type": "function", "function": {"name": STATEMENT_TOOL_NAME}},
    )

    claims: list[dict[str, Any]] = []
    message = response.choices[0].message
    if message.tool_calls:
        for tool_call in message.tool_calls:
            payload = json.loads(tool_call.function.arguments)
            claims.extend(_statements(payload.get("statements")))

    tokens_in = response.usage.prompt_tokens if response.usage else 0
    tokens_out = response.usage.completion_tokens if response.usage else 0

    return ExtractionResult(
        claims=claims,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd(settings.llm_model, tokens_in, tokens_out),
    )


__all__ = ["PROMPT_VERSION", "ExtractionResult", "cost_usd", "extract"]
