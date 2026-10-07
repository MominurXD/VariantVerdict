from app.analysis import analyze
from app.models import AnalysisRequest, AggregateRow
from app.scenarios import scenarios


def test_growth_scenario_holds_for_latency():
    result = analyze(scenarios()['growth-reliability'])
    assert result.verdict == 'hold'
    assert result.relative_lift_pct > 0
    assert any(c.id == 'latency' and not c.passed for c in result.checks)


def test_healthy_winner_ships():
    result = analyze(scenarios()['healthy-winner'])
    assert result.verdict == 'ship'
    assert result.p_value < 0.05
    assert result.estimated_power >= 0.8


def test_allocation_drift_blocks():
    result = analyze(scenarios()['allocation-drift'])
    assert result.verdict == 'hold'
    assert result.srm_p_value < 0.001


def test_noisy_experiment_collects():
    result = analyze(scenarios()['noisy-experiment'])
    assert result.verdict == 'collect'


def test_relative_lift_positive_for_growth():
    result = analyze(scenarios()['growth-reliability'])
    assert result.relative_lift_pct > 8


def test_ci_contains_observed_difference():
    result = analyze(scenarios()['growth-reliability'])
    lo, hi = result.confidence_interval_pp
    assert lo < result.absolute_lift_pp < hi


def test_segments_have_adjusted_p_values():
    result = analyze(scenarios()['growth-reliability'])
    assert result.segments
    assert all(0 <= s.adjusted_p_value <= 1 for s in result.segments)


def test_daily_has_both_arms():
    result = analyze(scenarios()['healthy-winner'])
    assert len(result.daily) == 14
    assert all(p.control_rate is not None and p.treatment_rate is not None for p in result.daily)


def test_methodology_is_exposed():
    result = analyze(scenarios()['healthy-winner'])
    assert 'primary_metric' in result.methodology
    assert 'assignment' in result.methodology


def test_reject_missing_arm():
    rows = [AggregateRow(date='2026-01-01', segment='All', variant='control', assigned=100, conversions=10, latency_ms=100, error_rate=.01)] * 4
    request = AnalysisRequest(experiment_name='bad', rows=rows)
    try:
        analyze(request)
    except ValueError as exc:
        assert 'both control and treatment' in str(exc)
    else:
        raise AssertionError('expected ValueError')


def test_srm_near_one_for_balanced_assignment():
    result = analyze(scenarios()['healthy-winner'])
    assert result.srm_p_value > 0.1


def test_latency_change_detected():
    result = analyze(scenarios()['growth-reliability'])
    assert result.latency_change_pct > 20


def test_power_is_probability():
    result = analyze(scenarios()['healthy-winner'])
    assert 0 <= result.estimated_power <= 1


def test_mde_is_positive():
    result = analyze(scenarios()['healthy-winner'])
    assert result.estimated_mde_relative_pct > 0
