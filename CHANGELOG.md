# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Automatic read-only diagnosis with `auto_diagnose.bat`.
- Guided repair flow with `auto_fix.bat`.
- Timestamped local diagnostic logs.
- Diagnosis decision tree documentation.
- Production-style documentation set:
  - Script reference
  - Operational runbook
  - Safety model
  - Design principles
  - FAQ
  - Contributing guide
  - Security policy

### Changed

- README now presents the recommended diagnose-first workflow.
- Documentation now emphasizes safe defaults and manual firewall reset.

## 0.1.0

### Added

- Initial Windows network repair scripts:
  - `one_click_fix.bat`
  - `check_network.bat`
  - `reset_dns.bat`
  - `reset_proxy.bat`
  - `reset_firewall.bat`
- Beginner troubleshooting documentation for proxy, DNS, and browser failure scenarios.
