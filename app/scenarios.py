from __future__ import annotations

from datetime import date, timedelta

from .models import AggregateRow, AnalysisRequest

SEGMENTS = ['Desktop', 'Mobile', 'Tablet']


def _rows(control_rates, treatment_rates, control_n, treatment_n, latency_c, latency_t, error_c, error_t, days=14):
    start = date(2026, 9, 1)
    rows = []
    weights = [0.46, 0.41, 0.13]
    segment_mod = [1.12, 0.78, 0.91]
    treatment_mod = [1.01, 1.00, 1.03]
    for day in range(days):
        d = (start + timedelta(days=day)).isoformat()
        wave = 1 + ((day % 5) - 2) * 0.018
        for idx, segment in enumerate(SEGMENTS):
            cn = max(30, round(control_n / days * weights[idx]))
            tn = max(30, round(treatment_n / days * weights[idx]))
            cr = control_rates * segment_mod[idx] * wave
            tr = treatment_rates * segment_mod[idx] * treatment_mod[idx] * (1 + ((day + 2) % 4 - 1.5) * 0.012)
            rows.append(AggregateRow(date=d, segment=segment, variant='control', assigned=cn, conversions=min(cn, round(cn*cr)), latency_ms=latency_c*(1+(idx-1)*0.025), error_rate=error_c))
            rows.append(AggregateRow(date=d, segment=segment, variant='treatment', assigned=tn, conversions=min(tn, round(tn*tr)), latency_ms=latency_t*(1+(idx-1)*0.025), error_rate=error_t))
    return rows


def scenarios():
    return {
        'growth-reliability': AnalysisRequest(
            experiment_name='Growth, hidden regression',
            rows=_rows(.0947, .1061, 30770, 31198, 184, 225, .006, .0065),
            max_latency_regression_pct=10,
            min_detectable_relative_lift_pct=15,
        ),
        'healthy-winner': AnalysisRequest(
            experiment_name='Checkout simplification',
            rows=_rows(.082, .0915, 26000, 26050, 188, 192, .0058, .0056),
            max_latency_regression_pct=10,
            min_detectable_relative_lift_pct=10,
        ),
        'allocation-drift': AnalysisRequest(
            experiment_name='Recommendation ranking test',
            rows=_rows(.112, .121, 18500, 26300, 171, 174, .004, .0042),
            max_latency_regression_pct=10,
            min_detectable_relative_lift_pct=12,
        ),
        'noisy-experiment': AnalysisRequest(
            experiment_name='Landing page copy test',
            rows=_rows(.073, .075, 2600, 2570, 151, 153, .003, .003),
            max_latency_regression_pct=10,
            min_detectable_relative_lift_pct=15,
        ),
    }
