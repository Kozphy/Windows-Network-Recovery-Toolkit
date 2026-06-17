#!/usr/bin/env bash
# Deploy production stack on a VM using immutable GHCR image tag.
# Usage: IMAGE_TAG=<full-git-sha> GHCR_IMAGE=ghcr.io/<owner>/<repo> ./scripts/deploy-compose-prod.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -z "${IMAGE_TAG:-}" ]; then
  echo "ERROR: IMAGE_TAG is required (full git SHA). CD must never deploy :latest." >&2
  exit 1
fi

if [ -z "${GHCR_IMAGE:-}" ]; then
  echo "ERROR: GHCR_IMAGE is required (e.g. ghcr.io/kozphy/windows-network-recovery-toolkit)." >&2
  exit 1
fi

if [ "${IMAGE_TAG}" = "latest" ]; then
  echo "ERROR: Refusing to deploy tag 'latest'. Set IMAGE_TAG to a full commit SHA." >&2
  exit 1
fi

DEPLOYED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== Deployment audit ==="
echo "deployed_image=${GHCR_IMAGE}:${IMAGE_TAG}"
echo "commit_sha=${IMAGE_TAG}"
echo "deployment_time=${DEPLOYED_AT}"

export IMAGE_TAG GHCR_IMAGE
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull api
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build

echo "Readiness check: GET /platform/ready"
curl -fsS http://localhost:8000/platform/ready
echo ""
echo "health_check=passed"
