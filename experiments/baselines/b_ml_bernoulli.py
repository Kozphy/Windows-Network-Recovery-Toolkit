"""B_ML — Bernoulli Naive Bayes on anonymized fixture features.

Trains only on ``development`` split cases. Does not use ground-truth fields as
features. Stdlib only (no scikit-learn). Small-n results are methodological —
not enterprise field claims.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1, load_cases, load_fixture, repo_root

FEATURE_NAMES: tuple[str, ...] = (
    "proxy_enabled",
    "localhost_proxy",
    "listener_found",
    "direct_probe_ok",
    "proxy_probe_ok",
    "has_path_health",
    "has_browser_stall",
    "has_timeline",
    "reverter_flag",
    "empty_proxy_state",
    "winhttp_direct",
    "has_proxy_owner",
)


def extract_features(fixture: dict[str, Any]) -> list[int]:
    """Binary features from fixture JSON — never includes labels or case ids."""
    proxy = fixture.get("proxy_state") or {}
    health = fixture.get("health_inject") or fixture.get("health") or {}
    owner = fixture.get("proxy_owner") or {}
    path = fixture.get("path_health") or {}
    browser = fixture.get("browser_stall") or {}
    timeline = fixture.get("timeline") or []

    server = str(proxy.get("wininet_proxy_server") or "")
    enabled = bool(proxy.get("wininet_proxy_enabled"))
    localhost = "127.0.0.1" in server or "localhost" in server.lower()
    empty_proxy = not proxy

    reverter = False
    if isinstance(timeline, list):
        for row in timeline:
            if isinstance(row, dict) and (
                row.get("reverter_suspected")
                or (row.get("reverter_diagnosis") or {}).get("status") == "REVERTER_SUSPECTED"
            ):
                reverter = True
                break

    values = [
        int(enabled),
        int(localhost),
        int(bool(owner.get("listener_found"))),
        int(health.get("direct_probe_ok") is True),
        int(health.get("proxy_probe_ok") is True),
        int(bool(path)),
        int(bool(browser)),
        int(bool(timeline)),
        int(reverter),
        int(empty_proxy),
        int(bool(proxy.get("winhttp_direct_access"))),
        int(bool(owner)),
    ]
    if len(values) != len(FEATURE_NAMES):
        raise RuntimeError("feature vector length mismatch")
    return values


@dataclass
class _NbModel:
    classes: list[str]
    class_log_prior: dict[str, float]
    # feature_index -> class -> (log_p_on, log_p_off)
    feature_log_prob: list[dict[str, tuple[float, float]]]
    train_size: int
    development_only: bool = True


@dataclass
class BernoulliNbBaseline:
    """Classical ML baseline (brief Baseline C) — Bernoulli NB."""

    seed: int = 42
    name: str = "B_ML"
    _model: _NbModel | None = field(default=None, init=False, repr=False)

    def fit(
        self,
        cases: list[BenchmarkCaseV1],
        fixtures: list[dict[str, Any]],
        *,
        seed: int = 42,
    ) -> None:
        if len(cases) != len(fixtures):
            raise ValueError("cases and fixtures length mismatch")
        self.seed = seed
        # Labels come only from training cases; features never include the label string.
        by_class: dict[str, list[list[int]]] = {}
        for case, fixture in zip(cases, fixtures, strict=True):
            label = case.expected_incident_class.strip().upper()
            by_class.setdefault(label, []).append(extract_features(fixture))

        if not by_class:
            raise ValueError("B_ML fit requires at least one training case")

        n = sum(len(v) for v in by_class.values())
        classes = sorted(by_class)
        class_log_prior = {c: math.log(len(by_class[c]) / n) for c in classes}
        feature_log_prob: list[dict[str, tuple[float, float]]] = []
        alpha = 1.0  # Laplace
        for j in range(len(FEATURE_NAMES)):
            per_class: dict[str, tuple[float, float]] = {}
            for c in classes:
                rows = by_class[c]
                ones = sum(row[j] for row in rows)
                total = len(rows)
                p_on = (ones + alpha) / (total + 2 * alpha)
                p_off = 1.0 - p_on
                per_class[c] = (math.log(p_on), math.log(max(p_off, 1e-15)))
            feature_log_prob.append(per_class)

        self._model = _NbModel(
            classes=classes,
            class_log_prior=class_log_prior,
            feature_log_prob=feature_log_prob,
            train_size=n,
            development_only=True,
        )

    def _ensure_fitted(self) -> _NbModel:
        if self._model is None:
            raise RuntimeError("B_ML must be fit before predict")
        return self._model

    def predict_proba(
        self, case: BenchmarkCaseV1, fixture: dict[str, Any]
    ) -> dict[str, float] | None:
        model = self._ensure_fitted()
        feats = extract_features(fixture)
        scores: dict[str, float] = {}
        for c in model.classes:
            score = model.class_log_prior[c]
            for j, bit in enumerate(feats):
                log_on, log_off = model.feature_log_prob[j][c]
                score += log_on if bit else log_off
            scores[c] = score
        # Log-sum-exp normalize
        max_s = max(scores.values())
        exps = {c: math.exp(s - max_s) for c, s in scores.items()}
        z = sum(exps.values()) or 1.0
        return {c: exps[c] / z for c in model.classes}

    def predict(self, case: BenchmarkCaseV1, fixture: dict[str, Any]) -> BaselinePrediction:
        model = self._ensure_fitted()
        proba = self.predict_proba(case, fixture) or {}
        predicted = max(proba, key=proba.get) if proba else "ERROR_INSUFFICIENT_DATA"
        confidence = float(proba.get(predicted, 0.0))
        abstained = predicted in {"ERROR_INSUFFICIENT_DATA", "INSUFFICIENT_DATA"}
        evidence = [
            f"feature:{name}={value}"
            for name, value in zip(FEATURE_NAMES, extract_features(fixture), strict=True)
            if value
        ]
        return BaselinePrediction(
            case_id=case.case_id,
            baseline=self.name,
            predicted_incident_class=predicted,
            proof_tier="T0_OBSERVATION_ONLY",
            policy_posture="PREVIEW_ONLY",
            remediation_posture="PREVIEW_ONLY",
            supporting_evidence=evidence,
            limitations=[
                "B_ML is Bernoulli NB on coarse fixture features — not calibrated probabilities.",
                "Trained on development split only; small-n results are methodological.",
                "Observation is not proof.",
            ],
            abstained=abstained,
            raw={
                "confidence": confidence,
                "train_size": model.train_size,
                "feature_names": list(FEATURE_NAMES),
            },
        )

    def metadata(self) -> dict[str, Any]:
        model = self._model
        return {
            "baseline": self.name,
            "kind": "bernoulli_naive_bayes",
            "trainable": True,
            "seed": self.seed,
            "feature_names": list(FEATURE_NAMES),
            "train_size": None if model is None else model.train_size,
            "classes": None if model is None else list(model.classes),
            "notes": "Fits development split only; stdlib implementation",
        }


def fit_b_ml_from_dataset(
    *,
    seed: int = 42,
    dataset_dir: Any = None,
    root: Any = None,
) -> BernoulliNbBaseline:
    """Fit B_ML on all development-split cases from the canonical dataset."""
    base = repo_root() if root is None else root
    train_cases = load_cases(dataset_dir, split="development")
    if not train_cases:
        raise ValueError("no development cases available to train B_ML")
    fixtures = [load_fixture(c, root=base) for c in train_cases]
    model = BernoulliNbBaseline(seed=seed)
    model.fit(train_cases, fixtures, seed=seed)
    return model


def predict_b_ml(
    case: BenchmarkCaseV1,
    fixture: dict[str, Any],
    *,
    model: BernoulliNbBaseline,
) -> BaselinePrediction:
    return model.predict(case, fixture)
