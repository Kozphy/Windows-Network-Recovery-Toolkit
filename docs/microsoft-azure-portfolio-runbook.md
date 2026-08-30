# Microsoft Azure portfolio runbook

This runbook turns the Windows Network Recovery Toolkit into a focused Microsoft interview demo for Windows, Azure support, cloud reliability, and SRE-oriented roles.

## What this upgrade proves

The repository remains a local-first, evidence-driven Windows reliability platform. The Azure layer adds a production-shaped deployment target and observability path without changing the core safety posture.

The demo now shows this chain:

```text
Windows endpoint symptom
  -> deterministic evidence collection
  -> root-cause classification with limitations
  -> FastAPI platform surface
  -> policy-gated remediation preview
  -> append-only audit evidence
  -> OpenTelemetry trace
  -> Azure Monitor / Application Insights
  -> Container Apps health and revision telemetry
```

This is intentionally not presented as antivirus, EDR, malware attribution, autonomous remediation, or a formal audit product.

## Azure-specific files

| File | Purpose |
|---|---|
| `Dockerfile.azure` | Azure-ready non-root image with the Azure Monitor OpenTelemetry distro installed |
| `requirements-azure.txt` | Optional Azure + Postgres dependency set |
| `infra/azure/main.bicep` | Container Apps + Log Analytics + Application Insights deployment |
| `backend/tracing.py` | Opt-in Azure Monitor export with graceful local fallback |
| `tests/test_azure_observability.py` | Safety tests for explicit opt-in behavior |

## Build the Azure image

```bash
docker build -f Dockerfile.azure -t wnrt-api:azure .
docker run --rm -p 8000:8000 \
  -e WNRT_AZURE_MONITOR_ENABLED=0 \
  wnrt-api:azure
```

Check the existing platform health endpoint:

```bash
curl http://127.0.0.1:8000/platform/health
```

Azure export stays disabled in the command above. This is the expected local default.

## Enable Azure Monitor locally

Create an Application Insights resource and copy its connection string. Never commit that string.

```bash
export WNRT_AZURE_MONITOR_ENABLED=1
export APPLICATIONINSIGHTS_CONNECTION_STRING='InstrumentationKey=...'
python -m backend
```

The tracing layer does not print the connection string. If the Azure package or connection string is missing, the API continues without Azure export.

## Deploy the infrastructure

Prerequisites:

- Azure CLI authenticated with `az login`
- an existing resource group
- an OCI image reachable by Azure Container Apps
- the image built from `Dockerfile.azure`

Example:

```bash
az deployment group create \
  --resource-group <resource-group> \
  --template-file infra/azure/main.bicep \
  --parameters appName=wnrt-api containerImage=<registry>/<image>:<tag>
```

The Bicep template creates:

- Log Analytics workspace
- Application Insights workspace-based component
- Azure Container Apps managed environment
- Container App with external HTTPS ingress
- liveness/readiness probes against `/platform/health`
- Application Insights connection string stored as a Container Apps secret
- `WNRT_AZURE_MONITOR_ENABLED=1`
- `PLATFORM_SAFE_MODE=1`
- scale-to-zero-friendly minimum replica configuration for a demo environment

## Microsoft interview scenario

### Scenario

A Windows endpoint is technically online, but browser and enterprise application traffic fails. Evidence suggests WinINET/WinHTTP proxy drift or a dead localhost proxy. The interviewer asks how you would diagnose the issue without creating additional risk.

### Walkthrough

1. **Observe, do not assume**
   - collect proxy, listener, TLS, DNS, and connectivity evidence
   - distinguish symptom from proof

2. **Classify deterministically**
   - use the repository's state machine / rule path
   - return explicit limitations rather than a malware claim

3. **Expose the incident through the API**
   - demonstrate `/trisk/*` or `/platform/*` surfaces
   - show health and platform telemetry

4. **Gate remediation**
   - keep safe mode on
   - produce a preview instead of automatically mutating Windows networking state

5. **Preserve evidence**
   - show append-only / hash-chained audit output
   - explain how replay supports incident review

6. **Observe the cloud service**
   - show the matching trace or request path in Application Insights
   - use Container Apps revision/health telemetry to separate endpoint failure from API/platform failure

### What to say in an interview

> I treated the Windows symptom and the cloud service as two different reliability domains. The endpoint collector produces deterministic evidence and limitations. The platform never converts a weak signal into a security accusation, and remediation stays preview-only until policy and human approval allow it. In Azure, I export OpenTelemetry into Application Insights so I can correlate application behavior with Container Apps health without weakening those local safety boundaries.

## Useful Application Insights questions

After generating traffic, inspect request/trace failures, dependency latency, and exception trends. The exact table names and fields depend on the Azure Monitor experience and SDK version, so use the Application Insights Logs schema presented by the deployed resource rather than hard-coding a portfolio claim.

Questions to answer during the demo:

- Did the API receive the incident request?
- Was latency introduced in the API or already present at the endpoint?
- Did any dependency fail?
- Is the Container App healthy while the endpoint remains unhealthy?
- Can the trace id connect application activity to the audit/replay story?

## Resume bullet

A concise version suitable for a Microsoft-oriented resume:

> Extended a Windows endpoint reliability platform with an Azure Container Apps deployment target and opt-in OpenTelemetry export to Application Insights, preserving deterministic diagnosis, policy-gated remediation, health probes, audit replay, and local-first safe defaults.

## Scope statement

This is a portfolio-grade, production-shaped reference deployment. It demonstrates engineering judgment, deployment architecture, observability, and incident reasoning; it does not claim enterprise certification, production SLO history, Microsoft endorsement, or autonomous remediation capability.
