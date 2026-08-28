"""Logs are JSON, one line per event, no emojis, no secrets."""

import json
import logging

import pytest
from core.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_logging():
    yield
    root = logging.getLogger("spenden")
    for handler in list(root.handlers):
        root.removeHandler(handler)


def test_a_record_is_one_line_of_json_with_service_level_and_extras(capsys):
    configure_logging(level="INFO", service="pipeline")
    get_logger("ingest").info("ingest_started", extra={"job": "seed_reference", "rows": 77})
    err = capsys.readouterr().err.strip()
    assert "\n" not in err, "one event must be one line"
    payload = json.loads(err)
    assert payload["message"] == "ingest_started"
    assert payload["service"] == "pipeline"
    assert payload["level"] == "INFO"
    assert payload["job"] == "seed_reference"
    assert payload["rows"] == 77
    assert payload["timestamp"]


def test_output_carries_no_emoji(capsys):
    configure_logging(service="api")
    get_logger("t").info("job_finished")
    out = capsys.readouterr().err
    assert all(ord(ch) < 0x2100 for ch in out), "log output must not contain pictographs or emojis"


def test_configure_logging_twice_does_not_double_log(capsys):
    configure_logging(service="api")
    configure_logging(service="api")
    get_logger("t").info("once")
    lines = [line for line in capsys.readouterr().err.strip().splitlines() if line]
    assert len(lines) == 1


def test_a_multiline_message_stays_on_one_line(capsys):
    configure_logging(service="api")
    get_logger("t").info("line one\nline two")
    err = capsys.readouterr().err.strip()
    assert len(err.splitlines()) == 1
    assert json.loads(err)["message"] == "line one\nline two"


def test_a_registered_secret_is_redacted(capsys):
    configure_logging(service="api", secrets=["sk-ant-super-secret"])
    get_logger("t").info("calling model", extra={"header": "Bearer sk-ant-super-secret"})
    err = capsys.readouterr().err
    assert "sk-ant-super-secret" not in err
    assert "[redacted]" in err


def test_an_exception_is_serialised_into_the_same_line(capsys):
    configure_logging(service="api")
    try:
        raise ValueError("boom")
    except ValueError:
        get_logger("t").exception("job_failed")
    err = capsys.readouterr().err.strip()
    assert len(err.splitlines()) == 1
    payload = json.loads(err)
    assert payload["message"] == "job_failed"
    assert "ValueError: boom" in payload["exc_info"]


def test_a_plain_record_carries_no_null_valued_keys(capsys):
    """The first real uvicorn run emitted "exc_info": null on every single line. A key whose value
    is always null is noise in a log drain, and it makes grep-by-key useless."""
    configure_logging(service="api")
    get_logger("t").info("api_started", extra={"env": "development"})
    payload = json.loads(capsys.readouterr().err.strip())
    assert None not in payload.values(), f"null-valued keys: {[k for k, v in payload.items() if v is None]}"
    assert "exc_info" not in payload


def test_uvicorn_logs_go_through_the_same_json_handler(capsys):
    """Otherwise production logs are half JSON and half 'INFO:     Started server process'."""
    configure_logging(service="api", capture_uvicorn=True)
    logging.getLogger("uvicorn.error").info("Application startup complete.")
    err = capsys.readouterr().err.strip()
    assert len(err.splitlines()) == 1
    payload = json.loads(err)
    assert payload["message"] == "Application startup complete."
    assert payload["service"] == "api"


def test_ansi_escape_codes_never_reach_the_log(capsys):
    """uvicorn attaches a color_message extra full of ANSI escapes. Terminal control codes in a
    structured log are junk at best and a terminal-injection vector at worst."""
    configure_logging(service="api", capture_uvicorn=True)
    logging.getLogger("uvicorn.error").info(
        "Started server process [%d]",
        1234,
        extra={"color_message": "Started server process [\x1b[36m%d\x1b[0m]"},
    )
    err = capsys.readouterr().err
    assert "\\u001b" not in err and "\x1b" not in err
    assert "color_message" not in err


def test_uvicorn_capture_is_opt_in(capsys):
    configure_logging(service="api")
    assert logging.getLogger("uvicorn.error").handlers == []


def test_level_filters_debug_by_default(capsys):
    configure_logging(service="api")
    get_logger("t").debug("noise")
    assert capsys.readouterr().err.strip() == ""
