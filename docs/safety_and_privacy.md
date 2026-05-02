# Safety and privacy (platform prototype)

## Allowed data (default prototype)

- **Hashed endpoint identity** (`stable_endpoint_hash`) — no raw hostname stored in platform JSONL.
- **OS family / coarse version** (e.g. `Windows`, `10.0.26200`).
- **Agent/backend version strings**.
- **Sanitized network state**: booleans and coarse flags (e.g. proxy enabled, DNS OK).
- **Process names** (basenames); paths **redacted** if under user profile.
- **Public test domains** for probes (e.g. `google.com`, `microsoft.com`, `cloudflare.com`) when used as probe targets.
- **Localhost** `127.0.0.1` / `::1` and **ports**.
- **FailureBlock IDs**, rule IDs, **risk_level**, **recommended_fix** text (may still contain operator-visible language—review before sharing).

## Forbidden or restricted

| Data | Rule |
| --- | --- |
| Raw hostname | **Do not persist**; use **hash** only. |
| Username | **Do not persist**; redact path segments. |
| Private IP addresses | **Mask** (e.g. `192.168.x.x`) or omit. |
| Wi-Fi SSID / MAC | **Do not collect** in platform payloads. |
| Corporate internal domains | **Redact** unless explicitly allowlisted as public probe names. |
| Tokens, secrets, browser history | **Never** collect. |
| Full registry values | **Avoid**; key paths may appear with **values redacted**. |

## Sanitization

Implemented in `platform_core/privacy.py`:

- `stable_endpoint_hash(hostname, os_version, machine_hint)` — SHA-256 hex **prefix** (truncated for display).
- `sanitize_ip`, `sanitize_domain`, `redact_text` — conservative defaults for portfolio demos.

## Repair risk levels

- **read_only** — diagnostics, export, inspect.
- **low** — cache flush previews, proxy status; repairs only with confirmation where documented.
- **medium** — DNS/proxy/Winsock/TCP stack resets — **typed confirmation**; **not** from API unless policy explicitly allows and executor allowlists script.
- **high** — firewall reset, adapter disable, killing unknown processes — **not executable via platform API** in this prototype; **manual instructions only**.
- **forbidden** — silent adapter disable, automatic firewall reset, arbitrary shell from API, external log upload, unrelated registry edits.

## Approval rules

- Every **execute** requires **matching preview_id**, valid **confirmation_phrase**, and **policy allow**.
- **API** rejects **high**/**forbidden** execution regardless of client UI.

## Rollback expectations

Rollback plans come from **FailureBlock** / toolkit docs and are **best-effort human steps**—not guaranteed automated rollback in the prototype executor.

## Why no high-risk auto repair

Enterprise endpoints require **evidence**, **change control**, and **blast-radius limits**. Automatic firewall or adapter mutation can **disconnect** the device or **open attack surface**; this project prioritizes **explainability** and **operator consent**.
