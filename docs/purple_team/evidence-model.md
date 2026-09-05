# Evidence Model

Bundles (`purple_evidence_bundle.v1`) chain stage hashes:

pre_state → simulation → telemetry → detections → risk → response → verification → metrics

`python -m src.purple_team evidence verify <bundle.json>`

**Tamper-evident, not tamper-proof.** See trust assumptions embedded in each bundle.
