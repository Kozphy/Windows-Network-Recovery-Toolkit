"""Optional PyTorch recurrence model.

Importing this module does not require PyTorch. Call ``torch_available`` before
constructing the model, or install the ``ml`` project extra.
"""

from __future__ import annotations

from typing import Any

from .contracts import ModelRecommendation, RiskFeatures

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - exercised in environments without ml extra
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]


def torch_available() -> bool:
    return torch is not None and nn is not None


if nn is not None:

    class RecurrenceRiskMLP(nn.Module):
        """Small tabular MLP for governed experimentation, not remediation control."""

        def __init__(self, input_size: int = 10, hidden_size: int = 16) -> None:
            super().__init__()
            self.network = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(p=0.10),
                nn.Linear(hidden_size, 1),
                nn.Sigmoid(),
            )

        def forward(self, features: Any) -> Any:
            return self.network(features)

else:

    class RecurrenceRiskMLP:  # type: ignore[no-redef]
        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError("PyTorch is unavailable. Install with: pip install -e '.[ml]'")


def recommend_with_torch(
    model: Any,
    incident_id: str,
    features: RiskFeatures,
    *,
    model_version: str,
    evidence_refs: list[str] | None = None,
) -> ModelRecommendation:
    """Run governed inference and return an advisory recommendation."""
    if not torch_available():
        raise RuntimeError("PyTorch is unavailable. Install with: pip install -e '.[ml]'")

    model.eval()
    tensor = torch.tensor([features.as_vector()], dtype=torch.float32)
    with torch.no_grad():
        score = float(model(tensor).reshape(-1)[0].item())

    priority = "HIGH" if score >= 0.70 else "MEDIUM" if score >= 0.35 else "LOW"
    return ModelRecommendation(
        incident_id=incident_id,
        model_id="pytorch-recurrence-mlp",
        model_version=model_version,
        risk_score=round(score, 6),
        review_priority=priority,
        explanation=[
            "PyTorch MLP ranked this incident for human review.",
            "Use the deterministic baseline and evidence record for decision support.",
        ],
        evidence_refs=evidence_refs or [],
        limitations=[
            "Prediction requires validation, calibration, drift monitoring, and an approved model card.",
            "Neural-network output does not replace deterministic control-test conclusions.",
        ],
    )
