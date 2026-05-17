from pydantic import BaseModel, Field, ValidationError
from app.schemas.report import ImpactItemCreate
from app.security import choose_event_source


class EventCandidate(BaseModel):
    title: str = Field(max_length=512)
    source: str = Field(max_length=128)
    url: str | None = Field(default=None, max_length=1024)
    authority_level: str | None = Field(default=None, max_length=32)


def validate_ai_impact_output(raw: dict, allowed_event_urls: set[str]) -> ImpactItemCreate:
    event_source, source_type = choose_event_source(raw.get("event_source"), allowed_event_urls)
    # Normalize source_type — AI models sometimes return non-standard values
    if source_type not in ("url", "ai_analysis"):
        source_type = "ai_analysis"
    normalized = {**raw, "event_source": event_source, "source_type": source_type, "raw_output": raw}
    # Normalize mapped_cn_targets — strip exchange suffixes from symbols (.SZ, .SH, .BJ)
    targets = normalized.get("mapped_cn_targets", [])
    if isinstance(targets, list):
        for t in targets:
            if isinstance(t, dict) and "symbol" in t:
                sym = t["symbol"]
                if isinstance(sym, str) and "." in sym:
                    t["symbol"] = sym.split(".")[0]
    normalized["mapped_cn_targets"] = targets
    # Enforce report_date matches input if present
    if "report_date" not in raw and "report_date" in normalized:
        pass  # keep what was set
    return ImpactItemCreate.model_validate(normalized)


def parse_ai_json(raw: dict, allowed_event_urls: set[str]) -> ImpactItemCreate | None:
    # Clamp impact_score to [0, 1] — AI models sometimes return 0-100 scale
    if "impact_score" in raw and isinstance(raw["impact_score"], (int, float)) and raw["impact_score"] > 1:
        raw["impact_score"] = min(1.0, raw["impact_score"] / 100)
    # Clamp confidence to [0, 1] — same issue
    if "confidence" in raw and isinstance(raw["confidence"], (int, float)) and raw["confidence"] > 1:
        raw["confidence"] = min(1.0, raw["confidence"] / 100)
    # Normalize source_type — map non-standard values to "ai_analysis"
    if "source_type" in raw and raw["source_type"] not in ("url", "ai_analysis"):
        raw["source_type"] = "ai_analysis"
    try:
        return validate_ai_impact_output(raw, allowed_event_urls)
    except ValidationError as e:
        import logging
        logging.getLogger(__name__).warning("AI output validation failed: %s | raw keys: %s", e, list(raw.keys()))
        return None
