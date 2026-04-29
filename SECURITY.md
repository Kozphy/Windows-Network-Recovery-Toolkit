# Security Policy

## Supported Versions

This project targets the latest committed version on the main branch.

## Reporting A Security Issue

If you find a security concern, open a GitHub issue with:

- A clear description of the concern
- The affected script or document
- Steps to reproduce, if applicable
- Why the behavior could be unsafe

Do not include sensitive logs, credentials, private proxy URLs, or internal network details in public issues.

## Safety Boundaries

The toolkit should not:

- Collect credentials
- Upload logs
- Disable antivirus
- Disable firewall automatically
- Disable network adapter bindings
- Bypass enterprise policy

## Local Logs

Diagnostic logs are written to the local `logs` folder.

Before sharing logs, review them for:

- Internal hostnames
- Proxy URLs
- Usernames
- Private IP addresses
- Work or school network details
