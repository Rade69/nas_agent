from __future__ import annotations

import logging


class SecretRedactionFilter(logging.Filter):
    """Replace configured secret values with a placeholder in every log record.

    Security Gate 0 (docs/SECURITY_HARDENING_PLAN.md section 18) requires log
    redaction. This is intentionally a simple value-substring filter over the
    handful of real secrets this backend ever holds (OpenAI/Exa API keys, the
    local session token) rather than a general PII/regex redaction engine —
    matches the "MVP" scope of the self-test checklist.
    """

    def __init__(self, secrets: list[str]) -> None:
        super().__init__()
        self._secrets = [s for s in secrets if s]

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._secrets:
            return True
        if isinstance(record.msg, str):
            for secret in self._secrets:
                if secret in record.msg:
                    record.msg = record.msg.replace(secret, "[REDACTED]")
        if record.args:
            record.args = tuple(_redact_value(arg, self._secrets) for arg in record.args)
        return True


def _redact_value(value: object, secrets: list[str]) -> object:
    if isinstance(value, str):
        for secret in secrets:
            if secret in value:
                value = value.replace(secret, "[REDACTED]")
        return value
    return value


def configure_logging(secrets: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    root = logging.getLogger()
    # Each call reflects the current process's actual secret set — drop any
    # filter a previous configure_logging() call left behind (matters across
    # repeated create_app() calls in tests; a real production process only
    # calls this once at startup).
    for existing in list(root.filters):
        if isinstance(existing, SecretRedactionFilter):
            root.removeFilter(existing)
    # A caller may pass e.g. [settings.openai_api_key, settings.local_token]
    # where some entries are None — filter those out here so an all-None list
    # (itself still a truthy, non-empty Python list) doesn't add a filter that
    # has nothing real to redact.
    real_secrets = [s for s in secrets if s] if secrets else []
    if real_secrets:
        root.addFilter(SecretRedactionFilter(real_secrets))


def is_redaction_enabled() -> bool:
    return any(isinstance(f, SecretRedactionFilter) for f in logging.getLogger().filters)
