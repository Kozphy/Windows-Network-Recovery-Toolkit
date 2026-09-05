# Implementation Roadmap

## Phase 1 — Merge-safe foundation

- Keep the harness in verify-only mode.
- Run Python compile and repository evaluation in CI.
- Generate SBOM evidence when dependency manifests are present.
- Run CodeQL on pull requests.
- Validate Rego syntax and policy test cases before policy enforcement.
- Run the continuous agent in read-only mode with bounded configured checks.
- Persist state-change fingerprints, audit JSONL, and escalation evidence.
- Start the agent automatically through a restartable Windows startup task.

## Phase 2 — Runtime integration

- Instrument FastAPI, harness and continuous-agent operations with OpenTelemetry.
- Export decision latency, replay consistency, approval backlog and policy-denial metrics.
- Add application calls to OPA using a versioned input schema.
- Replace placeholder container images with signed, digest-pinned releases.
- Route continuous-agent alerts to an approved notification destination.

## Phase 3 — Reliability engineering

- Add k6 or Locust tests for diagnostic and evidence endpoints.
- Define measurable availability and latency objectives from real baselines.
- Add controlled fault tests for dependency timeouts, malformed evidence and stale state.
- Build Grafana dashboards from Prometheus metrics.
- Add heartbeat and missed-cycle alerts for the continuous agent.

## Phase 4 — AI-assisted explanation

- Add a provider-neutral explanation adapter behind a feature flag.
- Require structured JSON output, citations and confidence metadata.
- Evaluate groundedness and unsupported claims with the existing harness.
- Route high-risk or low-confidence cases to human review.
- Never allow model output to bypass deterministic policy decisions.

## Phase 5 — Enterprise delivery

- Add Terraform for a selected cloud target.
- Add environment promotion and approval stages in GitHub Actions or Harness CI/CD.
- Sign images and attest provenance with Sigstore-compatible tooling.
- Export control evidence to Power BI and governance reports.
- Package the continuous agent with a signed native service wrapper and dedicated low-privilege identity.

## Deliberately deferred

The following should not be added merely for résumé breadth:

- Kafka until event volume or decoupling requirements justify it.
- A vector database until a real retrieval use case exists.
- Redis until caching, rate limiting or durable work queues are necessary.
- Kubernetes operators until standard deployments become insufficient.
- Offensive security or malware execution features outside an isolated specialist lab.
