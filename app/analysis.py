from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from uuid import uuid4

import numpy as np
from scipy.stats import chi2, norm

from .models import (
    AggregateRow,
    AnalysisRequest,
    AnalysisResult,
    ArmSummary,
    DailyPoint,
    IntegrityCheck,
    SegmentResult,
)


def _weighted_mean(values: list[tuple[float, int]]) -> float:
    total_weight = sum(weight for _, weight in values)
    if not total_weight:
        return 0.0
    return sum(value * weight for value, weight in values) / total_weight


def _arm_summary(rows: list[AggregateRow]) -> ArmSummary:
    assigned = sum(r.assigned for r in rows)
    conversions = sum(r.conversions for r in rows)
    return ArmSummary(
        assigned=assigned,
        conversions=conversions,
        conversion_rate=conversions / assigned,
        latency_ms=_weighted_mean([(r.latency_ms, r.assigned) for r in rows]),
        error_rate=_weighted_mean([(r.error_rate, r.assigned) for r in rows]),
    )


def _two_proportion(control: ArmSummary, treatment: ArmSummary, alpha: float):
    p1 = control.conversion_rate
    p2 = treatment.conversion_rate
    n1, n2 = control.assigned, treatment.assigned
    pooled = (control.conversions + treatment.conversions) / (n1 + n2)
    pooled_se = sqrt(max(1e-15, pooled * (1 - pooled) * (1 / n1 + 1 / n2)))
    z = (p2 - p1) / pooled_se if pooled_se else 0.0
    p_value = 2 * norm.sf(abs(z))

    unpooled_se = sqrt(max(1e-15, p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2))
    zcrit = norm.ppf(1 - alpha / 2)
    diff = p2 - p1
    ci = (diff - zcrit * unpooled_se, diff + zcrit * unpooled_se)
    return float(p_value), ci


def _srm_p_value(control_n: int, treatment_n: int, expected_treatment_share: float) -> float:
    total = control_n + treatment_n
    expected_t = total * expected_treatment_share
    expected_c = total - expected_t
    stat = ((control_n - expected_c) ** 2 / expected_c) + ((treatment_n - expected_t) ** 2 / expected_t)
    return float(chi2.sf(stat, 1))


def _power(p1: float, p2: float, n1: int, n2: int, alpha: float) -> float:
    diff = abs(p2 - p1)
    if diff == 0:
        return alpha
    pooled = (p1 + p2) / 2
    se0 = sqrt(max(1e-15, pooled * (1 - pooled) * (1 / n1 + 1 / n2)))
    se1 = sqrt(max(1e-15, p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2))
    z_alpha = norm.ppf(1 - alpha / 2)
    z_effect = diff / se1
    # two-sided normal approximation
    return float(norm.cdf(z_effect - z_alpha * se0 / se1) + norm.cdf(-z_effect - z_alpha * se0 / se1))


def _mde_relative(p: float, n1: int, n2: int, alpha: float, target_power: float) -> float | None:
    if p <= 0 or p >= 1:
        return None
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(target_power)
    se = sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    abs_mde = (z_alpha + z_beta) * se
    return float(abs_mde / p * 100)


def _holm_adjust(pairs: list[tuple[str, float]]) -> dict[str, float]:
    ordered = sorted(pairs, key=lambda item: item[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (segment, p) in enumerate(ordered):
        candidate = min(1.0, (m - rank) * p)
        running = max(running, candidate)
        adjusted[segment] = running
    return adjusted


def _segment_results(rows: list[AggregateRow], alpha: float) -> list[SegmentResult]:
    groups: dict[str, dict[str, list[AggregateRow]]] = defaultdict(lambda: {'control': [], 'treatment': []})
    for row in rows:
        groups[row.segment][row.variant].append(row)

    raw: list[tuple[str, float, float, float, float | None]] = []
    for segment, arms in groups.items():
        if not arms['control'] or not arms['treatment']:
            continue
        c = _arm_summary(arms['control'])
        t = _arm_summary(arms['treatment'])
        p_value, _ = _two_proportion(c, t, alpha)
        lift = ((t.conversion_rate / c.conversion_rate) - 1) * 100 if c.conversion_rate else None
        raw.append((segment, c.conversion_rate, t.conversion_rate, p_value, lift))

    adjusted = _holm_adjust([(segment, p) for segment, _, _, p, _ in raw])
    return [
        SegmentResult(
            segment=segment,
            control_rate=cr,
            treatment_rate=tr,
            relative_lift_pct=lift,
            p_value=p,
            adjusted_p_value=adjusted[segment],
        )
        for segment, cr, tr, p, lift in sorted(raw, key=lambda x: x[0])
    ]


def _daily(rows: list[AggregateRow]) -> list[DailyPoint]:
    grouped: dict[str, dict[str, list[AggregateRow]]] = defaultdict(lambda: {'control': [], 'treatment': []})
    for row in rows:
        grouped[row.date][row.variant].append(row)
    points = []
    for date in sorted(grouped):
        arm = grouped[date]
        c = _arm_summary(arm['control']).conversion_rate if arm['control'] else None
        t = _arm_summary(arm['treatment']).conversion_rate if arm['treatment'] else None
        points.append(DailyPoint(date=date, control_rate=c, treatment_rate=t))
    return points


def analyze(request: AnalysisRequest) -> AnalysisResult:
    control_rows = [row for row in request.rows if row.variant == 'control']
    treatment_rows = [row for row in request.rows if row.variant == 'treatment']
    if not control_rows or not treatment_rows:
        raise ValueError('both control and treatment rows are required')

    control = _arm_summary(control_rows)
    treatment = _arm_summary(treatment_rows)
    p_value, ci = _two_proportion(control, treatment, request.alpha)
    srm_p = _srm_p_value(control.assigned, treatment.assigned, request.expected_treatment_share)
    observed_share = treatment.assigned / (control.assigned + treatment.assigned)
    absolute_lift = (treatment.conversion_rate - control.conversion_rate) * 100
    relative_lift = ((treatment.conversion_rate / control.conversion_rate) - 1) * 100 if control.conversion_rate else None
    latency_change = ((treatment.latency_ms / control.latency_ms) - 1) * 100 if control.latency_ms else 0.0
    error_change_pp = (treatment.error_rate - control.error_rate) * 100
    power = _power(control.conversion_rate, treatment.conversion_rate, control.assigned, treatment.assigned, request.alpha)
    mde = _mde_relative(control.conversion_rate, control.assigned, treatment.assigned, request.alpha, request.target_power)

    checks = [
        IntegrityCheck(
            id='assignment',
            name='Assignment integrity',
            passed=srm_p >= 0.001,
            severity='blocker' if srm_p < 0.001 else 'info',
            detail=f"50/50 sample-ratio check p = {srm_p:.4f}; observed treatment share {observed_share*100:.2f}%.",
        ),
        IntegrityCheck(
            id='latency',
            name='Latency guardrail',
            passed=latency_change <= request.max_latency_regression_pct,
            severity='blocker' if latency_change > request.max_latency_regression_pct else 'info',
            detail=f"Observed mean latency change {latency_change:+.1f}% vs +{request.max_latency_regression_pct:.1f}% limit.",
        ),
        IntegrityCheck(
            id='traffic',
            name='Planned traffic',
            passed=min(control.assigned, treatment.assigned) >= 500,
            severity='warning' if min(control.assigned, treatment.assigned) < 500 else 'info',
            detail=f"{min(control.assigned, treatment.assigned):,} users in the smaller arm; target MDE {request.min_detectable_relative_lift_pct:.1f}% relative.",
        ),
        IntegrityCheck(
            id='horizon',
            name='Analysis horizon',
            passed=len({r.date for r in request.rows}) >= 7,
            severity='warning' if len({r.date for r in request.rows}) < 7 else 'info',
            detail=f"{len({r.date for r in request.rows})} distinct experiment days in the submitted aggregate data.",
        ),
    ]

    blockers = [c for c in checks if not c.passed and c.severity == 'blocker']
    significant_win = p_value < request.alpha and treatment.conversion_rate > control.conversion_rate
    enough_power = power >= request.target_power

    if blockers:
        verdict = 'hold'
        verdict_title = 'Hold the release'
        verdict_reason = blockers[0].detail + ' Resolve the guardrail failure before rollout.'
    elif significant_win and enough_power:
        verdict = 'ship'
        verdict_title = 'Evidence supports rollout'
        verdict_reason = 'The treatment improves the primary metric, clears integrity checks and meets the target power threshold.'
    else:
        verdict = 'collect'
        verdict_title = 'Keep collecting evidence'
        verdict_reason = 'No blocking guardrail failed, but the evidence is not yet strong enough for a rollout decision.'

    score = 100
    score -= 35 * len(blockers)
    if p_value >= request.alpha:
        score -= 20
    if not enough_power:
        score -= 15
    if srm_p < 0.01:
        score -= 15
    confidence_score = max(5, min(99, int(round(score))))

    baseline = request.baseline_conversion_pct / 100 if request.baseline_conversion_pct is not None else control.conversion_rate
    return AnalysisResult(
        run_id=str(uuid4()),
        experiment_name=request.experiment_name,
        created_at=datetime.now(timezone.utc).isoformat(),
        verdict=verdict,
        verdict_title=verdict_title,
        verdict_reason=verdict_reason,
        confidence_score=confidence_score,
        control=control,
        treatment=treatment,
        absolute_lift_pp=absolute_lift,
        relative_lift_pct=relative_lift,
        p_value=p_value,
        confidence_interval_pp=(ci[0] * 100, ci[1] * 100),
        srm_p_value=srm_p,
        observed_treatment_share=observed_share,
        latency_change_pct=latency_change,
        error_rate_change_pp=error_change_pp,
        estimated_power=power,
        estimated_mde_relative_pct=_mde_relative(baseline, control.assigned, treatment.assigned, request.alpha, request.target_power),
        checks=checks,
        segments=_segment_results(request.rows, request.alpha),
        daily=_daily(request.rows),
        row_count=len(request.rows),
        methodology={
            'primary_metric': 'Two-proportion z-test with a two-sided confidence interval.',
            'assignment': 'Pearson chi-square sample-ratio mismatch check against the planned allocation.',
            'segments': 'Exploratory subgroup z-tests with Holm family-wise p-value adjustment.',
            'power': 'Normal-approximation planning diagnostic; not a substitute for a pre-registered power analysis.',
        },
    )
