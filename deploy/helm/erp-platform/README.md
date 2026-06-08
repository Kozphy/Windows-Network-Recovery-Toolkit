# ERP Platform Helm chart (scaffold)

Kubernetes packaging for the Endpoint Reliability Platform API, Prometheus, and Grafana — mirrors `docker-compose.yml`.

## Prerequisites

- Kubernetes 1.25+
- Helm 3.10+
- Container image published (see `.github/workflows/build.yml` → GHCR)

## Install

```bash
# Build image locally (optional)
docker build -t er-platform-api:local .

helm upgrade --install erp ./deploy/helm/erp-platform \
  --namespace erp \
  --create-namespace \
  --set image.repository=er-platform-api \
  --set image.tag=local \
  --set image.pullPolicy=Never
```

## GHCR example

```bash
helm upgrade --install erp ./deploy/helm/erp-platform \
  --namespace erp \
  --create-namespace \
  --set image.repository=ghcr.io/YOUR_ORG/windows-network-recovery-toolkit \
  --set image.tag=amd_version \
  --set api.existingSecret=erp-platform-secrets \
  --set grafana.adminPassword="$(openssl rand -hex 16)"
```

Create the secret first:

```bash
kubectl create secret generic erp-platform-secrets \
  --namespace erp \
  --from-literal=PLATFORM_API_KEY='change-me'
```

## Optional: Grafana dashboards

Dashboard JSON files live under `deploy/grafana/provisioning/dashboards/json/`. To mount them:

```bash
kubectl create configmap erp-grafana-dashboard-files \
  --namespace erp \
  --from-file=deploy/grafana/provisioning/dashboards/json/

# Chart expects optional ConfigMap name: {{ release }}-grafana-dashboard-files
# Rename to match fullname or patch grafana-deployment volume.
```

For production, prefer a `grafana-dashboard-files` subchart or `helm template` with `.Files.Glob`.

## Values reference

| Key | Default | Notes |
|-----|---------|-------|
| `image.repository` | `ghcr.io/kozphy/...` | Override for your registry |
| `api.env.PLATFORM_FIXTURE_MODE` | `"1"` | Set `"0"` for live endpoints |
| `api.persistence.enabled` | `true` | JSONL / platform data volume |
| `prometheus.enabled` | `true` | Scrapes API `/metrics` |
| `grafana.enabled` | `true` | Prometheus datasource provisioned |
| `ingress.enabled` | `false` | Enable for external access |

## Not included (see `docs/feature_inventory.md`)

- Managed Postgres / Redis / Kafka (use `docker-compose.scale.yml` as reference)
- `deploy.yml` GitHub Actions rollout
- TLS certificates, HPA, PodDisruptionBudgets
- Multi-tenant fleet ingest gateways

## Uninstall

```bash
helm uninstall erp --namespace erp
```
