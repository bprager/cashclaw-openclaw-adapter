from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from cashclaw_adapter.app import create_app
from cashclaw_adapter.cashclaw_client import UpstreamHealth
from cashclaw_adapter.config import Settings
from cashclaw_adapter.memgraph import DependencyCheck
from cashclaw_adapter.models import TaskRecord, TaskStatus


class FakeCashClawClient:
    def __init__(self) -> None:
        self.health = UpstreamHealth(healthy=True, detail="ok")
        self.created_task = TaskRecord(
            task_id="task-123",
            status=TaskStatus.PENDING,
            title="Build adapter",
            instructions="Implement the first phase",
            project_id="proj-1",
            session_id="sess-1",
            requested_by="openclaw",
            metadata={"priority": "high"},
            upstream_payload={"task_id": "task-123", "status": "pending"},
        )
        self.fetched_task = self.created_task.model_copy(update={"status": TaskStatus.RUNNING})

    def check_health(self) -> UpstreamHealth:
        return self.health

    def create_task(self, _request: Any) -> TaskRecord:
        return self.created_task

    def get_task(self, _task_id: str) -> TaskRecord:
        return self.fetched_task


class FakeMemgraphStore:
    def __init__(self) -> None:
        self.health = DependencyCheck(healthy=True)
        self.tasks: list[TaskRecord] = []

    def ping(self) -> DependencyCheck:
        return self.health

    def upsert_task(self, task: TaskRecord) -> None:
        self.tasks.append(task)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        adapter_require_localhost=False,
        startup_validate_dependencies=False,
    )


@pytest.fixture
def fake_cashclaw_client() -> FakeCashClawClient:
    return FakeCashClawClient()


@pytest.fixture
def fake_memgraph_store() -> FakeMemgraphStore:
    return FakeMemgraphStore()


@pytest.fixture
def client(
    settings: Settings,
    fake_cashclaw_client: FakeCashClawClient,
    fake_memgraph_store: FakeMemgraphStore,
) -> TestClient:
    app = create_app(
        settings=settings,
        cashclaw_client_factory=lambda _settings: fake_cashclaw_client,
        memgraph_store_factory=lambda _settings: fake_memgraph_store,
    )
    return TestClient(app)
