from __future__ import annotations

from dataclasses import asdict, dataclass


DATA_KEYWORDS = {
    "activation",
    "api",
    "audit",
    "audience",
    "batch",
    "blueprint",
    "campaign",
    "collection",
    "connected",
    "count",
    "current",
    "dataflow",
    "dataset",
    "destination",
    "failed",
    "field",
    "find",
    "how many",
    "id",
    "journey",
    "list",
    "live",
    "merge policy",
    "metric",
    "observability",
    "platform",
    "property",
    "published",
    "sandbox",
    "schema",
    "segment",
    "show",
    "status",
    "tag",
    "timestamp",
}

CONCEPTUAL_PREFIXES = (
    "explain ",
    "what is ",
    "what are ",
    "define ",
    "describe ",
    "why ",
    "how does ",
)


@dataclass(frozen=True)
class SimplePromptDecision:
    is_simple: bool
    reason: str
    suggested_action: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 4)
        return payload


def decide_simple_prompt(query: str) -> SimplePromptDecision:
    lowered = " ".join(query.lower().split())
    matched = sorted(keyword for keyword in DATA_KEYWORDS if keyword in lowered)
    if matched:
        return SimplePromptDecision(
            is_simple=False,
            reason=f"Data/evidence keyword(s) require SQL/API pipeline: {', '.join(matched[:5])}.",
            suggested_action="USE_DATA_PIPELINE",
            confidence=0.95,
        )
    if lowered.startswith(CONCEPTUAL_PREFIXES):
        return SimplePromptDecision(
            is_simple=True,
            reason="Conceptual question with no local DB/API evidence request.",
            suggested_action="LLM_DIRECT",
            confidence=0.85,
        )
    return SimplePromptDecision(
        is_simple=False,
        reason="Ambiguous question; use data pipeline to avoid unsupported facts.",
        suggested_action="USE_DATA_PIPELINE",
        confidence=0.65,
    )

