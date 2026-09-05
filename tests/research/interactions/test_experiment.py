"""Tests for factorial case generation and evaluation."""

from research.interactions.analysis import analyze_experiment
from research.interactions.experiment import (
    EXPERIMENT_BUILDERS,
    evaluate_case,
    generate_factorial_cases,
    run_interaction_experiments,
)


def test_generate_factorial_case_count() -> None:
    spec = EXPERIMENT_BUILDERS[0]
    cases = generate_factorial_cases(spec, replicates=3)
    assert len(cases) == 12
    cells = {(c.x1, c.x2) for c in cases}
    assert cells == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_healthy_cell_zero_severity() -> None:
    spec = next(s for s in EXPERIMENT_BUILDERS if s["experiment_id"] == "proxy_x_firewall")
    cases = generate_factorial_cases(spec, replicates=1)
    healthy = next(c for c in cases if c.x1 == 0 and c.x2 == 0)
    assert healthy.y_failure == 0
    assert healthy.y_severity == 0.0


def test_evaluate_case_returns_platform_fields() -> None:
    spec = EXPERIMENT_BUILDERS[0]
    case = generate_factorial_cases(spec, replicates=1)[0]
    obs = evaluate_case(case)
    assert obs.incident_class
    assert 0.0 <= obs.y_platform_severity <= 1.0
    assert obs.y_platform_failure in (0, 1)


def test_run_interaction_experiments_count() -> None:
    observations, cases = run_interaction_experiments(replicates=2)
    assert len(cases) == len(observations)
    assert len(cases) == 6 * 4 * 2  # 6 experiments, 4 cells, 2 replicates


def test_fit_lpm_coefficients_on_factorial() -> None:
    from research.interactions.analysis import fit_lpm_coefficients

    spec = next(s for s in EXPERIMENT_BUILDERS if s["experiment_id"] == "dns_x_proxy")
    cases = generate_factorial_cases(spec, replicates=3)
    observations = [evaluate_case(c) for c in cases]
    b0, b1, b2, b3 = fit_lpm_coefficients(observations, "y_severity")
    assert b0 >= 0.0
    assert b1 > 0.0


def test_listener_x_process_severity_ordering() -> None:
    spec = next(s for s in EXPERIMENT_BUILDERS if s["experiment_id"] == "listener_x_process")
    cases = generate_factorial_cases(spec, replicates=1)
    worst = next(c for c in cases if c.x1 == 0 and c.x2 == 0)
    best = next(c for c in cases if c.x1 == 1 and c.x2 == 1)
    assert worst.y_severity > best.y_severity


def test_analyze_experiment_produces_effects() -> None:
    observations, _ = run_interaction_experiments(replicates=2, experiment_ids=["proxy_x_tls"])
    result = analyze_experiment(
        "proxy_x_tls",
        observations,
        factor_a_name="proxy_fault",
        factor_b_name="tls_path_fault",
        description="test",
    )
    assert result.sample_size == 8
    assert len(result.effects) == 4
    severity = next(e for e in result.effects if e.outcome == "y_severity")
    assert severity.interaction_effect > 0.05
    assert severity.lpm_beta_3 != 0.0 or abs(severity.lpm_beta_3) < 1e-9
