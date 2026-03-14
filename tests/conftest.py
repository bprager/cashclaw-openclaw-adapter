from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cashclaw_adapter.app import create_app
from cashclaw_adapter.cashclaw_client import UpstreamHealth
from cashclaw_adapter.config import Settings
from cashclaw_adapter.memgraph import DependencyCheck
from cashclaw_adapter.models import TaskRecord, TaskStatus


class FakeCashClawClient:
    def __init__(self) -> None:
        self.health = UpstreamHealth(
            healthy=True,
            detail="mode=running, running=True, active_tasks=1, agent_id=agent-1",
        )
        self.created_task = TaskRecord(
            task_id="task-123",
            status=TaskStatus.ACCEPTED,
            title="Build adapter",
            instructions="Build adapter\nImplement the first phase",
            agent_id="agent-1",
            client_address="0xabc",
            requested_by="0xabc",
            category="development",
            budget_wei="1000",
            quoted_price_wei="900",
            revision_count=0,
            metadata={},
            upstream_payload={"id": "task-123", "status": "accepted"},
        )
        self.fetched_task = self.created_task.model_copy(update={"status": TaskStatus.SUBMITTED})
        self.listed_tasks = [self.created_task, self.fetched_task]

    def check_health(self) -> UpstreamHealth:
        return self.health

    def list_tasks(self) -> list[TaskRecord]:
        return self.listed_tasks

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
