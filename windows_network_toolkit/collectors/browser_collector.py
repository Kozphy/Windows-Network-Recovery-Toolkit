"""Browser / HTTPS path probe facade."""

from __future__ import annotations

from typing import Any


def collect_browser_signals(feature_vector: Any | None = None) -> dict[str, Any]:
    """Derive browser-path stress signals from a FeatureVector or return empty shell."""
    if feature_vector is None:
        return {
            "browser_https_ok": None,
            "browser_path_stress": None,
            "source": "browser_probe",
        }
    from src.observability.browser_probe import browser_path_stress_signal

    stress = browser_path_stress_signal(feature_vector)
    return {
        "browser_https_ok": getattr(feature_vector, "https_ok", None),
        "browser_path_stress": stress,
        "curl_https_ok": getattr(feature_vector, "curl_https_ok", None),
        "source": "browser_probe",
    }
