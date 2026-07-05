# Security model — RileyJarvis Windows Hybrid

## Risk levels

```text
low
medium
high
critical
```

## Risk primjeri

```text
low:
  - read notes
  - create artifact
  - list tools
  - health check
  - screenshot without OCR or external upload

medium:
  - open app
  - search web
  - read file from allowed workspace
  - inspect active window

high:
  - type text
  - click
  - press key
  - edit file
  - paste clipboard
  - interact with browser

critical:
  - delete files
  - run shell command
  - install package
  - send email/message
  - execute arbitrary PowerShell/Python
  - access secrets
```

## Permission pravila

1. `critical` tools are disabled by default.
2. `high` tools require computer mode and explicit confirmation.
3. `medium` tools may require confirmation depending on context.
4. `low` tools can run without confirmation.
5. No model-facing arbitrary shell command tool.
6. File tools are restricted to allowed folders.
7. Sensitive values must be redacted from logs.
8. Every tool call must be logged.
9. Computer-use tools must capture active window before and after execution.
10. `computer_type_text`, `computer_click`, `computer_press_key`, `computer_scroll` must not execute if active app is not allowed or if computer mode is disabled.

## Allowlist primjer (FAZA 11)

```json
{
  "allowed_apps": [
    "notepad.exe",
    "calc.exe",
    "chrome.exe",
    "code.exe"
  ],
  "blocked_apps": [
    "powershell.exe",
    "cmd.exe",
    "regedit.exe"
  ]
}
```

## Status implementacije

Ovaj sloj (`python_backend/app/security/`) je predviđen za FAZU 11 plana. Do tada, postojeći legacy PowerShell computer-use alati (trenutno implementirani direktno u `electron/main.cjs`) **rade bez ovog sloja** — to je poznat, privremen rizik dok se permission layer ne implementira, i treba ga imati na umu prije nego se computer-use alati dalje šire ili izlažu van lokalne mašine.

Vidi [TOOL_CONTRACTS.md](./TOOL_CONTRACTS.md) za polja `risk` i `requires_confirmation` u tool definiciji.
