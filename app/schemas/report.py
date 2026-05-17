from datetime import date
from pydantic import BaseModel, Field, field_validator
from app.security import is_safe_external_url

ImpactDirection = str
VALID_DIRECTIONS = {"利多", "利空", "偏多", "偏空", "中性"}


class CnTarget(BaseModel):
    symbol: str = Field(max_length=32)
    name: str = Field(max_length=64)
    relation_type: str = Field(max_length=64)
    theme: str = Field(max_length=128)


class ImpactItemCreate(BaseModel):
    report_date: date
    us_trade_date: date
    us_symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9.\-]+$")
    us_name: str | None = Field(default=None, max_length=128)
    turnover_rank: int = Field(ge=1, le=500)
    pct_change: float | None = None
    amount: float | None = Field(default=None, ge=0)
    reason_category: str = Field(max_length=64)
    event_summary: str = Field(max_length=512)
    mapped_cn_targets: list[CnTarget] = Field(default_factory=list, max_length=8)
    impact_direction: ImpactDirection
    impact_strength: int = Field(ge=1, le=5)
    impact_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    event_source: str = Field(max_length=1024)
    source_type: str = Field(pattern=r"^(url|ai_analysis)$")
    ai_model: str | None = Field(default=None, max_length=64)
    raw_output: dict | None = None

    @field_validator("impact_direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in VALID_DIRECTIONS:
            raise ValueError("invalid impact direction")
        return value

    @field_validator("event_source")
    @classmethod
    def validate_event_source(cls, value: str) -> str:
        if value == "AI分析":
            return value
        if not is_safe_external_url(value):
            raise ValueError("unsafe event source url")
        return value


class ImpactItemView(BaseModel):
    id: int
    report_date: date
    us_symbol: str
    turnover_rank: int
    pct_change: float | None
    reason_category: str | None
    event_summary: str | None
    mapped_cn_targets: str | None
    impact_direction: str | None
    impact_strength: int | None
    event_source: str | None
    source_type: str | None

    model_config = {"from_attributes": True}
