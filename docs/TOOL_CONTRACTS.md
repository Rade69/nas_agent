# Tool contracts — RileyJarvis Windows Hybrid

Svi toolovi moraju imati isti format, bez obzira da li su implementirani u Electron legacy sloju (PowerShell) ili u Python backend-u.

## Tool definition schema

```json
{
  "name": "screen_snapshot",
  "description": "Capture current desktop screenshot.",
  "input_schema": {
    "type": "object",
    "properties": {
      "monitor": {
        "type": "string",
        "enum": ["all", "primary", "active"],
        "default": "all"
      }
    },
    "required": []
  },
  "risk": "low",
  "requires_confirmation": false,
  "requires_computer_mode": false,
  "allowed_in_background": true,
  "timeout_ms": 5000,
  "implemented_by": "python",
  "enabled": true
}
```

## Tool execution request

```json
{
  "tool_name": "computer_type_text",
  "arguments": {
    "text": "Hello world"
  },
  "context": {
    "computer_mode": true,
    "conversation_id": "optional-id",
    "request_id": "optional-id"
  }
}
```

## Tool execution response

```json
{
  "ok": true,
  "tool_name": "computer_type_text",
  "result": {
    "typed_chars": 11
  },
  "artifact_ids": [],
  "event_ids": [],
  "action_log_id": "uuid",
  "duration_ms": 230
}
```

## Error response

```json
{
  "ok": false,
  "tool_name": "computer_type_text",
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Tool requires computer mode and explicit confirmation.",
    "details": {
      "risk": "high",
      "requires_computer_mode": true
    }
  },
  "action_log_id": "uuid"
}
```

## Napomena

Ovaj contract važi za sve nove Python toolove od FAZE 4 nadalje. Legacy PowerShell toolovi (`electron/tools_legacy/powershell/`) ne moraju odmah biti prepravljeni na ovaj format, ali svaki novi Python tool mora ga poštovati da bi tool bridge (FAZA 6) i permission layer (FAZA 11) mogli da rade bez tool-specific izuzetaka.

Vidi [SECURITY_MODEL.md](./SECURITY_MODEL.md) za značenje `risk` i `requires_confirmation` polja.
