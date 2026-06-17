# erp-platform Helm chart (optional)

**Default CD path:** VM + Docker Compose (`docs/production_deployment.md`).

## Immutable image deploy

```bash
export GITHUB_SHA="<full-40-char-commit-sha>"

helm upgrade --install erp-platform ./deploy/helm/erp-platform \
  --namespace erp --create-namespace \
  --set image.repository=ghcr.io/kozphy/windows-network-recovery-toolkit \
  --set image.tag="${GITHUB_SHA}" \
  --set ingress.enabled=true \
  --wait --timeout 5m
```

Never set `image.tag=latest` in production CD.

## Values

| Key | Purpose |
|-----|---------|
| `image.repository` | GHCR image path (lowercase) |
| `image.tag` | Full git SHA |
| `ingress.enabled` | Expose API via ingress |
