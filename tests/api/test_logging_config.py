from __future__ import annotations

import io
import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.logging import configure_logging, reset_request_id, set_request_id
from app.main import app


def test_configure_logging_emits_json_with_context() -> None:
    stream = io.StringIO()
    configure_logging(
        level="INFO",
        log_format="json",
        runtime_environment="non_local",
        log_file_path="/tmp/oge.gl/backend.log",
        stream=stream,
    )
    token = set_request_id("req-test-1")
    try:
        logging.getLogger("tests.logging").info("ingestion_job_finished", extra={"job_id": "job-123"})
    finally:
        reset_request_id(token)

    output = stream.getvalue().strip()
    assert output

    payload = json.loads(output.splitlines()[-1])
    assert payload["level"] == "INFO"
    assert payload["logger"] == "tests.logging"
    assert payload["event"] == "ingestion_job_finished"
    assert payload["request_id"] == "req-test-1"
    assert payload["job_id"] == "job-123"


def test_request_middleware_sets_request_id_and_logs_failed_request(caplog) -> None:
    caplog.set_level(logging.WARNING)
    client = TestClient(app)

    response = client.get("/not-a-real-route")

    assert response.status_code == 404
    assert response.headers.get("x-request-id") is None

    failed_records = [record for record in caplog.records if record.getMessage() == "api_request_failed"]
    assert failed_records
    assert getattr(failed_records[-1], "request_id", None)
    assert getattr(failed_records[-1], "status_code", None) == 404


def test_request_middleware_sanitizes_request_id_header(caplog) -> None:
    caplog.set_level(logging.WARNING)
    client = TestClient(app)

    response = client.get("/not-a-real-route", headers={"x-request-id": "bad\nvalue\t***"})

    assert response.status_code == 404
    failed_records = [record for record in caplog.records if record.getMessage() == "api_request_failed"]
    assert failed_records
    assert getattr(failed_records[-1], "request_id", None) == "badvalue"


def test_configure_logging_writes_same_event_to_stream_and_file(tmp_path) -> None:
    stream = io.StringIO()
    log_file_path = tmp_path / "backend.log"

    configure_logging(
        level="DEBUG",
        log_format="json",
        runtime_environment="local",
        log_file_path=str(log_file_path),
        stream=stream,
    )

    logging.getLogger("tests.logging").warning("api_request_failed", extra={"request_id": "req-sync-1"})

    stream_output = stream.getvalue().strip().splitlines()
    file_output = log_file_path.read_text().strip().splitlines()
    assert stream_output
    assert file_output

    stream_payload = json.loads(stream_output[-1])
    file_payload = json.loads(file_output[-1])

    assert stream_payload["event"] == "api_request_failed"
    assert file_payload["event"] == "api_request_failed"
    assert stream_payload["request_id"] == "req-sync-1"
    assert file_payload["request_id"] == "req-sync-1"


def test_configure_logging_warns_when_local_file_path_falls_back(monkeypatch, tmp_path) -> None:
    stream = io.StringIO()
    calls: list[str] = []

    class _FakeFileHandler(logging.Handler):
        def __init__(self, filename: str) -> None:
            super().__init__()
            self.baseFilename = filename

        def emit(self, record: logging.LogRecord) -> None:
            return None

    def _fake_file_handler(filename: str):
        target = str(filename)
        calls.append(target)
        if len(calls) == 1:
            raise OSError("permission denied")
        return _FakeFileHandler(target)

    monkeypatch.setattr("app.core.logging.logging.FileHandler", _fake_file_handler)

    configure_logging(
        level="INFO",
        log_format="json",
        runtime_environment="local",
        log_file_path=str(tmp_path / "requested.log"),
        stream=stream,
    )

    payloads = [json.loads(line) for line in stream.getvalue().strip().splitlines() if line.strip()]
    fallback_records = [payload for payload in payloads if payload.get("event") == "local_log_file_fallback_path"]

    assert fallback_records
    assert fallback_records[-1]["requested_path"] == str(tmp_path / "requested.log")
    assert fallback_records[-1]["resolved_path"] == str(Path("/tmp/oge.gl/backend.log"))
