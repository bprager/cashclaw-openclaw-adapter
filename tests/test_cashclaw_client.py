from __future__ import annotations

from typing import Any

import pytest
import requests

from cashclaw_adapter.cashclaw_client import (
    CashClawClient,
    CashClawClientError,
    CashClawResponseError,
    CashClawServerError,
    CashClawUnavailableError,
)
from cashclaw_adapter.config import Settings
from cashclaw_adapter.models import TaskCreateRequest, TaskStatus


class FakeResponse:
    def __init__(self, status_code: int, payload: Any, reason: str = "error") -> None:
        self.status_code = status_code
        self._payload = payload
        self.reason = reason

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any] | None, tuple[float, float]]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        timeout: tuple[float, float],
    ) -> Any:
        self.calls.append((method, url, json, timeout))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def build_client(session: FakeSession, retry_count: int = 1) -> CashClawClient:
    settings = Settings(
        cashclaw_base_url="http://cashclaw.local",
        cashclaw_timeout_sec=9.0,
        cashclaw_connect_timeout_sec=2.0,
        cashclaw_safe_retry_count=retry_count,
    )
    return CashClawClient(settings, session=session)


def test_check_health_retries_safe_requests() -> None:
    session = FakeSession(
        [
            requests.ConnectionError("boom"),
            FakeResponse(200, {"detail": "healthy"}),
        ]
    )
    client = build_client(session)

    health = client.check_health()

    assert health.healthy is True
    assert health.detail == "healthy"
    assert len(session.calls) == 2
    assert session.calls[0][3] == (2.0, 9.0)


def test_create_task_uses_fallback_fields_when_upstream_omits_them() -> None:
    session = FakeSession(
        [
            FakeResponse(
                201,
                {
                    "task_id": "task-1",
                    "status": "pending",
                },
                reason="created",
            )
        ]
    )
    client = build_client(session)

    task = client.create_task(
        TaskCreateRequest(
            title="Build",
            instructions="Implement",
            project_id="proj-1",
            session_id="sess-1",
            requested_by="openclaw",
        )
    )

    assert task.task_id == "task-1"
    assert task.title == "Build"
    assert task.instructions == "Implement"
    assert task.project_id == "proj-1"
    assert task.status is TaskStatus.PENDING


def test_get_task_raises_for_upstream_4xx() -> None:
    session = FakeSession([FakeResponse(404, {"detail": "missing"}, reason="not found")])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawClientError) as exc_info:
        client.get_task("task-404")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "missing"


def test_get_task_raises_for_upstream_5xx() -> None:
    session = FakeSession([FakeResponse(500, {"detail": "crash"}, reason="server error")])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawServerError):
        client.get_task("task-500")


def test_create_task_rejects_non_object_json() -> None:
    session = FakeSession([FakeResponse(200, ["not", "a", "dict"])])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawResponseError):
        client.create_task(TaskCreateRequest(title="Build", instructions="Implement"))


def test_get_task_raises_when_required_fields_are_missing() -> None:
    session = FakeSession([FakeResponse(200, {"status": "pending"})])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawResponseError):
        client.get_task("task-1")


def test_get_task_raises_when_status_is_unknown() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "task_id": "task-1",
                    "status": "mystery",
                    "title": "Build",
                    "instructions": "Implement",
                },
            )
        ]
    )
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawResponseError):
        client.get_task("task-1")


def test_check_health_raises_after_retry_exhaustion() -> None:
    session = FakeSession([requests.Timeout("slow"), requests.Timeout("still slow")])
    client = build_client(session)

    with pytest.raises(CashClawUnavailableError):
        client.check_health()
