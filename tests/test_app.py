from __future__ import annotations

from fastapi.testclient import TestClient

from cashclaw_adapter.app import _is_loopback_host, create_app
from cashclaw_adapter.cashclaw_client import (
    CashClawClientError,
    CashClawResponseError,
    CashClawServerError,
    CashClawTaskNotFoundError,
    CashClawUnavailableError,
    UpstreamHealth,
)
from cashclaw_adapter.config import Settings
from cashclaw_adapter.memgraph import DependencyCheck


def test_health_reports_ok_when_dependencies_are_healthy(
    client: TestClient,
    fake_memgraph_store,
) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert fake_memgraph_store.tasks == []


def test_health_reports_degraded_when_cashclaw_fails(
    client: TestClient,
    fake_cashclaw_client,
) -> None:
    fake_cashclaw_client.check_health = lambda: (_ for _ in ()).throw(
        CashClawUnavailableError("cashclaw offline")
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["cashclaw"]["healthy"] is False


def test_health_reports_degraded_when_memgraph_fails(
    client: TestClient,
    fake_memgraph_store,
) -> None:
    fake_memgraph_store.health = DependencyCheck(healthy=False, detail="memgraph offline")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["memgraph"]["detail"] == "memgraph offline"


def test_create_task_persists_to_memgraph(
    client: TestClient,
    fake_memgraph_store,
) -> None:
    response = client.post(
        "/tasks",
        json={
            "title": "Build adapter",
            "instructions": "Implement the first phase",
            "project_id": "proj-1",
        },
        headers={"x-request-id": "req-123"},
    )

    assert response.status_code == 501
    assert response.headers["x-request-id"] == "req-123"
    assert len(fake_memgraph_store.tasks) == 0
    assert "does not support task creation" in response.json()["detail"]


def test_list_tasks_persists_to_memgraph(
    client: TestClient,
    fake_memgraph_store,
) -> None:
    response = client.get("/tasks")

    assert response.status_code == 200
    assert len(response.json()["tasks"]) == 2
    assert len(fake_memgraph_store.tasks) == 2


def test_get_task_persists_to_memgraph(
    client: TestClient,
    fake_memgraph_store,
) -> None:
    response = client.get("/tasks/task-123")

    assert response.status_code == 200
    assert response.json()["status"] == "submitted"
    assert len(fake_memgraph_store.tasks) == 1
    assert fake_memgraph_store.tasks[0].status.value == "submitted"


def test_list_tasks_returns_502_for_upstream_4xx(
    client: TestClient,
    fake_cashclaw_client,
) -> None:
    fake_cashclaw_client.list_tasks = lambda: (_ for _ in ()).throw(
        CashClawClientError(400, "bad request")
    )

    response = client.get("/tasks")

    assert response.status_code == 502
    assert "CashClaw client error" in response.json()["detail"]


def test_get_task_returns_502_for_upstream_5xx(
    client: TestClient,
    fake_cashclaw_client,
) -> None:
    fake_cashclaw_client.get_task = lambda _task_id: (_ for _ in ()).throw(
        CashClawServerError(502, "boom")
    )

    response = client.get("/tasks/task-1")

    assert response.status_code == 502
    assert "CashClaw server error" in response.json()["detail"]


def test_get_task_returns_503_for_upstream_unavailable(
    client: TestClient,
    fake_cashclaw_client,
) -> None:
    fake_cashclaw_client.get_task = lambda _task_id: (_ for _ in ()).throw(
        CashClawUnavailableError("unreachable")
    )

    response = client.get("/tasks/task-1")

    assert response.status_code == 503
    assert response.json()["detail"] == "unreachable"


def test_get_task_returns_404_when_task_is_missing(
    client: TestClient,
    fake_cashclaw_client,
) -> None:
    fake_cashclaw_client.get_task = lambda _task_id: (_ for _ in ()).throw(
        CashClawTaskNotFoundError("task-404")
    )

    response = client.get("/tasks/task-404")

    assert response.status_code == 404
    assert "task-404" in response.json()["detail"]


def test_get_task_returns_502_for_bad_upstream_payload(
    client: TestClient,
    fake_cashclaw_client,
) -> None:
    fake_cashclaw_client.get_task = lambda _task_id: (_ for _ in ()).throw(
        CashClawResponseError("bad payload")
    )

    response = client.get("/tasks/task-1")

    assert response.status_code == 502
    assert response.json()["detail"] == "bad payload"


def test_list_tasks_returns_503_when_memgraph_write_fails(
    settings: Settings,
    fake_cashclaw_client,
) -> None:
    class FailingMemgraphStore:
        def ping(self) -> DependencyCheck:
            return DependencyCheck(healthy=True)

        def upsert_task(self, _task) -> None:
            raise RuntimeError("memgraph write failure")

    app = create_app(
        settings=settings,
        cashclaw_client_factory=lambda _settings: fake_cashclaw_client,
        memgraph_store_factory=lambda _settings: FailingMemgraphStore(),
    )
    client = TestClient(app)

    response = client.get("/tasks")

    assert response.status_code == 503
    assert response.json()["detail"] == "Memgraph write failed"


def test_is_loopback_host_accepts_only_local_values() -> None:
    assert _is_loopback_host("127.0.0.1") is True
    assert _is_loopback_host("::1") is True
    assert _is_loopback_host("testclient") is True
    assert _is_loopback_host("198.51.100.10") is False


def test_startup_validation_runs_when_enabled(fake_cashclaw_client, fake_memgraph_store) -> None:
    called = {"cashclaw": 0, "memgraph": 0}

    def check_health() -> UpstreamHealth:
        called["cashclaw"] += 1
        return UpstreamHealth(healthy=True)

    def ping() -> DependencyCheck:
        called["memgraph"] += 1
        return DependencyCheck(healthy=True)

    fake_cashclaw_client.check_health = check_health
    fake_memgraph_store.ping = ping

    app = create_app(
        settings=Settings(adapter_require_localhost=False, startup_validate_dependencies=True),
        cashclaw_client_factory=lambda _settings: fake_cashclaw_client,
        memgraph_store_factory=lambda _settings: fake_memgraph_store,
    )

    with TestClient(app):
        pass

    assert called == {"cashclaw": 1, "memgraph": 1}
