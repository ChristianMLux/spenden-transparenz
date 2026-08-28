"""JSON logging for both services.

One event is one line of JSON on stderr. No emojis: these logs are read in Railway, in CI and in a
Windows console, and a pictograph that renders in one of those renders as a box in the others.

Secrets registered with configure_logging are redacted from the formatted line, so an accidental
`extra={"header": auth_header}` cannot ship a key to the log drain.

The formatter API was read from the installed python-json-logger 4.2.0 rather than from memory:
JsonFormatter moved to pythonjsonlogger.json in 4.x, and `timestamp`, `static_fields` and
`rename_fields` are keyword-only.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from pythonjsonlogger.json import JsonFormatter

LOGGER_ROOT = "spenden"
REDACTED = "[redacted]"

# Fields the formatter must not copy out of the LogRecord into the JSON line.
# color_message is uvicorn's: it duplicates the message with ANSI escape codes in it, and terminal
# control codes in a structured log are junk at best and a terminal-injection vector at worst.
_RESERVED = (
    "args,asctime,created,exc_text,filename,funcName,levelno,lineno,module,msecs,"
    "msg,name,pathname,process,processName,relativeCreated,stack_info,thread,threadName,taskName,"
    "color_message"
).split(",")


class _RedactingFormatter(JsonFormatter):
    """Formats as JSON, then removes every registered secret from the finished line.

    Redaction happens on the rendered string rather than per field, because a secret can arrive
    inside a longer value ("Bearer sk-..."), inside a nested structure, or inside a traceback.
    The secret list is short (at most a handful) and formatting only happens for records that
    already passed the level filter, so scanning the line is not on any hot path.
    """

    def __init__(self, *args: Any, secrets: tuple[str, ...] = (), **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Longest first: redacting a prefix before the full value would leave a tail behind.
        self._secrets = tuple(sorted((s for s in secrets if s), key=len, reverse=True))

    def add_fields(
        self,
        log_data: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_data, record, message_dict)
        # Drop keys that are null for this record. The first real uvicorn run emitted
        # "exc_info": null on every line, which is noise in a drain and makes grep-by-key useless.
        for key in [k for k, value in log_data.items() if value is None]:
            del log_data[key]

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        for secret in self._secrets:
            line = line.replace(secret, REDACTED)
        return line


UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def configure_logging(
    level: str = "INFO",
    service: str = "api",
    secrets: list[str] | tuple[str, ...] = (),
    capture_uvicorn: bool = False,
) -> None:
    """Install exactly one JSON handler on the `spenden` logger tree.

    Calling this twice is safe and does not double-log: the previous handlers are removed first.

    capture_uvicorn routes uvicorn's own loggers through the same handler. Without it, production
    logs are half JSON and half "INFO:     Started server process", which no drain can parse as
    one stream.
    """
    logger = logging.getLogger(LOGGER_ROOT)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = _RedactingFormatter(
        "%(levelname)s %(message)s",
        rename_fields={"levelname": "level"},
        static_fields={"service": service},
        reserved_attrs=_RESERVED,
        timestamp=True,
        secrets=tuple(secrets),
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(level.upper())
    # Never hand records to the root logger: it would print them a second time, unformatted.
    logger.propagate = False

    for name in UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        for existing in list(uvicorn_logger.handlers):
            uvicorn_logger.removeHandler(existing)
        if capture_uvicorn:
            uvicorn_logger.addHandler(handler)
            uvicorn_logger.setLevel(level.upper())
            uvicorn_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Logger under the configured tree. `get_logger("ingest")` -> `spenden.ingest`."""
    return logging.getLogger(f"{LOGGER_ROOT}.{name}")
