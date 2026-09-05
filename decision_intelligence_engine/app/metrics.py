from prometheus_client import Counter, Histogram

DECISIONS_ANALYZED = Counter(
    "di_decisions_analyzed_total",
    "Total decisions analyzed",
    ["domain"],
)
HUMAN_DECISIONS = Counter(
    "di_human_decisions_total",
    "Total human approval or rejection events",
    ["action"],
)
OUTCOMES_VERIFIED = Counter(
    "di_outcomes_verified_total",
    "Total verified decision outcomes",
    ["outcome"],
)
DECISION_CONFIDENCE = Histogram(
    "di_decision_confidence",
    "Distribution of recommendation confidence scores",
    buckets=(0.1, 0.25, 0.5, 0.75, 0.9, 1.0),
)
