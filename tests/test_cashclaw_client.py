from __future__ import annotations

from typing import Any

import pytest
import requests

from cashclaw_adapter.cashclaw_client import (
    CashClawClient,
    CashClawClientError,
    CashClawResponseError,
    CashClawServerError,
    CashClawTaskNotFoundError,
    CashClawUnavailableError,
)
from cashclaw_adapter.config import Settings
from cashclaw_adapter.models import TaskStatus


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
            FakeResponse(200, {"configured": True, "mode": "running"}),
            FakeResponse(200, {"running": True, "activeTasks": 2, "agentId": "agent-1"}),
        ]
    )
    client = build_client(session)

    health = client.check_health()

    assert health.healthy is True
    assert "active_tasks=2" in str(health.detail)
    assert len(session.calls) == 3
    assert session.calls[0][3] == (2.0, 9.0)
    assert session.calls[1][1] == "http://cashclaw.local/api/setup/status"
    assert session.calls[2][1] == "http://cashclaw.local/api/status"


def test_check_health_reports_setup_mode_when_not_configured() -> None:
    session = FakeSession(
        [
            FakeResponse(200, {"configured": False, "mode": "setup", "step": "wallet"})
        ]
    )
    client = build_client(session)

    health = client.check_health()

    assert health.healthy is False
    assert "not configured" in str(health.detail)


def test_list_tasks_parses_real_cashclaw_task_shape() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "tasks": [
                        {
                            "id": "task-1",
                            "task": "Build adapter\nImplement the first phase",
                            "status": "accepted",
                            "agentId": "agent-1",
                            "clientAddress": "0xabc",
                            "category": "development",
                            "budgetWei": "1000",
                            "quotedPriceWei": "900",
                            "quotedMessage": "I can do this",
                            "result": "Done",
                            "files": [
                                {
                                    "key": "artifact.txt",
                                    "name": "artifact.txt",
                                    "size": 42,
                                    "uploadedAt": 1700000000,
                                }
                            ],
                            "messages": [
                                {
                                    "sender": "client",
                                    "role": "user",
                                    "content": "Please build it",
                                    "timestamp": 1700000001,
                                }
                            ],
                        }
                    ],
                    "events": [],
                },
            )
        ]
    )
    client = build_client(session, retry_count=0)

    tasks = client.list_tasks()

    assert len(tasks) == 1
    assert tasks[0].task_id == "task-1"
    assert tasks[0].status is TaskStatus.ACCEPTED
    assert tasks[0].title == "Build adapter"
    assert tasks[0].agent_id == "agent-1"
    assert tasks[0].client_address == "0xabc"
    assert tasks[0].files[0].name == "artifact.txt"
    assert tasks[0].messages[0].content == "Please build it"


def test_list_tasks_raises_for_upstream_4xx() -> None:
    session = FakeSession([FakeResponse(404, {"error": "missing"}, reason="not found")])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawClientError) as exc_info:
        client.list_tasks()

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "missing"


def test_list_tasks_raises_for_upstream_5xx() -> None:
    session = FakeSession([FakeResponse(500, {"error": "crash"}, reason="server error")])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawServerError):
        client.list_tasks()


def test_list_tasks_rejects_non_object_json() -> None:
    session = FakeSession([FakeResponse(200, ["not", "a", "dict"])])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawResponseError):
        client.list_tasks()


def test_list_tasks_raises_when_required_fields_are_missing() -> None:
    session = FakeSession([FakeResponse(200, {"tasks": [{"status": "accepted"}]})])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawResponseError):
        client.list_tasks()


def test_get_task_raises_when_status_is_unknown() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "tasks": [
                        {
                            "id": "task-1",
                            "task": "Build",
                            "status": "mystery",
                        }
                    ]
                },
            )
        ]
    )
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawResponseError):
        client.get_task("task-1")


def test_get_task_filters_from_task_list() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "tasks": [
                        {"id": "task-1", "task": "Build", "status": "requested"},
                        {"id": "task-2", "task": "Ship", "status": "completed"},
                    ]
                },
            )
        ]
    )
    client = build_client(session, retry_count=0)

    task = client.get_task("task-2")

    assert task.task_id == "task-2"
    assert task.status is TaskStatus.COMPLETED


def test_get_task_raises_when_task_is_missing() -> None:
    session = FakeSession([FakeResponse(200, {"tasks": []})])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawTaskNotFoundError):
        client.get_task("task-404")


def test_list_tasks_raises_unavailable_when_cashclaw_is_in_setup_mode() -> None:
    session = FakeSession([FakeResponse(503, {"error": "Agent not configured", "mode": "setup"})])
    client = build_client(session, retry_count=0)

    with pytest.raises(CashClawUnavailableError):
        client.list_tasks()


def test_check_health_raises_after_retry_exhaustion() -> None:
    session = FakeSession([requests.Timeout("slow"), requests.Timeout("still slow")])
    client = build_client(session)

    with pytest.raises(CashClawUnavailableError):
        client.check_health()
