from __future__ import annotations

from pydantic import BaseModel, Field


class CalibrationPoint(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    success: bool


class CalibrationRequest(BaseModel):
    points: list[CalibrationPoint] = Field(min_length=1)
    bins: int = Field(default=10, ge=2, le=50)


class CalibrationReport(BaseModel):
    samples: int
    brier_score: float
    expected_calibration_error: float


def evaluate_calibration(request: CalibrationRequest) -> CalibrationReport:
    points = request.points
    brier = sum((p.confidence - float(p.success)) ** 2 for p in points) / len(points)

    ece = 0.0
    for index in range(request.bins):
        low = index / request.bins
        high = (index + 1) / request.bins
        bucket = [
            p for p in points
            if low <= p.confidence < high or (index == request.bins - 1 and p.confidence == 1.0)
        ]
        if not bucket:
            continue
        avg_conf = sum(p.confidence for p in bucket) / len(bucket)
        accuracy = sum(float(p.success) for p in bucket) / len(bucket)
        ece += (len(bucket) / len(points)) * abs(avg_conf - accuracy)

    return CalibrationReport(
        samples=len(points),
        brier_score=round(brier, 6),
        expected_calibration_error=round(ece, 6),
    )
