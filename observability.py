# observability.py
"""Observability module providing JSON logging, telemetry trace spans, and PII redaction."""

import json
import logging
import re
import time
from typing import Any, Dict, Generator
from contextlib import contextmanager

# Regular Expressions to scrub emails and API Keys
PII_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
GEMINI_KEY_REGEX = re.compile(r"AIza[0-9A-Za-z-_]{35}")

def redact_sensitive_data(text: str) -> str:
    """Active scrubbing mechanism to remove PII and API keys before writing logs."""
    if not isinstance(text, str):
        return text
    scrubbed = PII_EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
    scrubbed = GEMINI_KEY_REGEX.sub("[REDACTED_API_KEY]", scrubbed)
    return scrubbed

class JsonStructuredFormatter(logging.Formatter):
    """Custom formatter generating machine-readable structured logs."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_data(record.getMessage()),
        }
        if hasattr(record, "intent"):
            log_entry["intent"] = redact_sensitive_data(str(record.intent))
        if hasattr(record, "outcome"):
            log_entry["outcome"] = redact_sensitive_data(str(record.outcome))
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        return json.dumps(log_entry)

def configure_logger() -> logging.Logger:
    """Instantiate structured logger handler."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonStructuredFormatter())
    logger_instance = logging.getLogger("telemetry_agent")
    logger_instance.setLevel(logging.INFO)
    logger_instance.handlers = [handler]
    return logger_instance

structured_logger = configure_logger()

@contextmanager
def telemetry_span(name: str, intent_description: str, trace_id: str = "tr_001") -> Generator[Dict[str, Any], None, None]:
    """Capture agent intent vs actual outcome and trace spans."""
    start = time.time()
    structured_logger.info(
        f"Span Start: {name}", 
        extra={"intent": intent_description, "trace_id": trace_id}
    )
    outcome_payload = {"status": "success"}
    try:
        yield outcome_payload
    except Exception as exc:
        outcome_payload["status"] = "failed"
        outcome_payload["error"] = str(exc)
        raise
    finally:
        duration = round((time.time() - start) * 1000, 2)
        outcome_payload["duration_ms"] = duration
        structured_logger.info(
            f"Span End: {name}", 
            extra={"outcome": json.dumps(outcome_payload), "trace_id": trace_id}
        )
