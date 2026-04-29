# Contributing

Thanks for helping improve Windows Network Recovery Toolkit.

## Project Principles

Contributions should keep the project:

- Beginner-friendly
- Safe by default
- Dependency-free
- Windows 10/11 compatible
- Clear about when settings are changed

## Before Opening A Pull Request

1. Keep changes focused.
2. Update documentation when behavior changes.
3. Use clear `.bat` comments for non-obvious commands.
4. Do not add third-party dependencies.
5. Do not add automatic firewall resets.
6. Do not disable network adapter bindings.

## Script Guidelines

Batch scripts should:

- Check Administrator permission before repairs.
- Print clear status messages.
- Ask before higher-risk changes.
- Remind users to restart when required.
- Use built-in Windows commands only.

## Documentation Guidelines

Docs should:

- Use simple English.
- Prefer practical steps over theory.
- Explain risk clearly.
- Match current script behavior.

## Testing

At minimum, check that scripts:

- Start correctly in Command Prompt.
- Show a clear Administrator warning when not elevated.
- Do not make changes during diagnosis-only paths.
- Handle missing optional registry values without failing noisily.
