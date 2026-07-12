# LinkedIn release-draft automation

Optional maintainer workflow: when a **GitHub Release** is published, generate a professional LinkedIn **draft** for manual review. Nothing is posted to LinkedIn automatically.

## How it works

1. Trigger: `release` (type `published`) or manual `workflow_dispatch`.
2. Script `scripts/generate_linkedin_release_post.py` formats a draft from release metadata.
3. Draft is written to `artifacts/linkedin/linkedin-{tag}.md` and uploaded as a workflow artifact.
4. The full draft appears in the GitHub Actions **Step Summary**.
5. A review issue titled `LinkedIn draft: {release name}` is created or **updated** (idempotent via hidden marker `<!-- linkedin-release-draft:{tag} -->`).
6. If repository secret `ZAPIER_LINKEDIN_WEBHOOK_URL` is set, a JSON payload is POSTed to Zapier with `approval_required: true`. The webhook must **not** auto-publish.

Workflow file: [`.github/workflows/linkedin-release-draft.yml`](../.github/workflows/linkedin-release-draft.yml)

## Publish a GitHub Release

1. Tag and create a Release in GitHub (include bullet-style notes for best “What’s new” extraction).
2. Wait for workflow **LinkedIn release draft** to finish.
3. Open the run → **Summary** tab to read the draft.
4. Open the linked issue and complete the approval checklist before posting anywhere.

## Run manually (test)

GitHub → **Actions** → **LinkedIn release draft** → **Run workflow**.

Provide at least:

| Input | Example |
|-------|---------|
| `tag` | `v0.2.0` |
| `release_name` | optional display name |
| `notes` | markdown with `-` bullets |
| `validation_summary` | only verified local facts (no secrets) |

Local dry-run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
@'
{
  "repository": "Kozphy/Windows-Network-Recovery-Toolkit",
  "release_name": "v0.2.0",
  "tag": "v0.2.0",
  "release_url": "https://github.com/Kozphy/Windows-Network-Recovery-Toolkit/releases/tag/v0.2.0",
  "notes": "- Evidence-based proxy drift diagnostics\n- Policy-gated remediation previews",
  "published_at": "2026-07-12T00:00:00Z",
  "validation_summary": "Generator unit tests passed."
}
'@ | Set-Content -Encoding utf8 .\release-payload.mock.json

python scripts/generate_linkedin_release_post.py --release-json .\release-payload.mock.json --write-artifact
```

## Where to review the draft

| Location | Purpose |
|----------|---------|
| Actions Step Summary | Immediate review |
| Artifact `linkedin-draft-{tag}` | Downloadable markdown/JSON |
| `artifacts/linkedin/linkedin-{tag}.md` in the job workspace | Same content |
| GitHub Issue `LinkedIn draft: …` | Checklist + idempotent updates |

## Optional Zapier webhook

1. In Zapier, create a Zap: **Webhooks by Zapier → Catch Hook**.
2. Add a path that stores or emails the draft for **manual** LinkedIn scheduling (do **not** wire “Create Share” without a human filter).
3. Copy the Catch Hook URL.
4. In GitHub → **Settings → Secrets and variables → Actions**, add secret:

   `ZAPIER_LINKEDIN_WEBHOOK_URL` = that URL

5. Re-run the workflow. If the secret is absent, the webhook step is skipped.

### Payload shape

```json
{
  "repository": "owner/repo",
  "release_name": "…",
  "tag": "vX.Y.Z",
  "release_url": "https://github.com/…/releases/tag/…",
  "draft": "…full post text…",
  "approval_required": true
}
```

## Keep manual approval enabled

- Do not add LinkedIn “Create Share” as an unconditional Zap action.
- Require the GitHub issue checklist before publishing.
- Treat Zapier as transport for a draft, not as an auto-poster.

## Disable the integration

| Goal | Action |
|------|--------|
| Stop Zapier only | Delete `ZAPIER_LINKEDIN_WEBHOOK_URL` |
| Stop all automation | Disable or delete `.github/workflows/linkedin-release-draft.yml` |

## Security and privacy

- Never put webhook URLs, LinkedIn tokens, GitHub PATs, or emails in source, docs, issues, or artifacts.
- The workflow does not print `ZAPIER_LINKEDIN_WEBHOOK_URL`.
- Release notes lines that look like secrets (`api_key`, `token`, `ghp_…`) are skipped when extracting bullets.
- Do not invent test counts, customers, or security certifications in `validation_summary`.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Workflow did not run | Release must be **published** (not draft-only); or use `workflow_dispatch` |
| Duplicate issues | Marker must appear in body; search uses `<!-- linkedin-release-draft:{tag} -->` |
| Empty “What’s new” | Add `-` / `*` bullets to release notes |
| Webhook skipped | Secret missing or empty (expected) |
| Webhook HTTP error | Zap Catch Hook URL expired or Zap off — rotate secret after fixing |

## Tests

```powershell
pytest -q tests/test_linkedin_release_post.py
```
