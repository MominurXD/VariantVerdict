from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator


Variant = Literal['control', 'treatment']


class AggregateRow(BaseModel):
    date: str
    segment: str = 'All users'
    variant: Variant
    assigned: int = Field(gt=0)
    conversions: int = Field(ge=0)
    latency_ms: float = Field(gt=0)
    error_rate: float = Field(ge=0, le=1)

    @field_validator('conversions')
    @classmethod
    def conversions_not_above_assigned(cls, value: int, info):
        assigned = info.data.get('assigned')
        if assigned is not None and value > assigned:
            raise ValueError('conversions cannot exceed assigned')
        return value


class AnalysisRequest(BaseModel):
    experiment_name: str = Field(min_length=2, max_length=120)
    rows: list[AggregateRow] = Field(min_length=4)
    baseline_conversion_pct: float | None = Field(default=None, ge=0, le=100)
    max_latency_regression_pct: float = Field(default=10.0, ge=0, le=500)
    min_detectable_relative_lift_pct: float = Field(default=15.0, gt=0, le=500)
    expected_treatment_share: float = Field(default=0.5, gt=0.05, lt=0.95)
    alpha: float = Field(default=0.05, gt=0.0001, lt=0.5)
    target_power: float = Field(default=0.8, gt=0.5, lt=0.999)


class ArmSummary(BaseModel):
    assigned: int
    conversions: int
    conversion_rate: float
    latency_ms: float
    error_rate: float


class IntegrityCheck(BaseModel):
    id: str
    name: str
    passed: bool
    severity: Literal['info', 'warning', 'blocker']
    detail: str


class SegmentResult(BaseModel):
    segment: str
    control_rate: float
    treatment_rate: float
    relative_lift_pct: float | None
    p_value: float
    adjusted_p_value: float


class DailyPoint(BaseModel):
    date: str
    control_rate: float | None = None
    treatment_rate: float | None = None


class AnalysisResult(BaseModel):
    run_id: str
    experiment_name: str
    created_at: str
    verdict: Literal['ship', 'hold', 'collect']
    verdict_title: str
    verdict_reason: str
    confidence_score: int
    control: ArmSummary
    treatment: ArmSummary
    absolute_lift_pp: float
    relative_lift_pct: float | None
    p_value: float
    confidence_interval_pp: tuple[float, float]
    srm_p_value: float
    observed_treatment_share: float
    latency_change_pct: float
    error_rate_change_pp: float
    estimated_power: float
    estimated_mde_relative_pct: float | None
    checks: list[IntegrityCheck]
    segments: list[SegmentResult]
    daily: list[DailyPoint]
    row_count: int
    methodology: dict[str, str]
