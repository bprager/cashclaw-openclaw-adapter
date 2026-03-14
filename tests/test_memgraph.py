from __future__ import annotations

from typing import Any

from cashclaw_adapter.memgraph import MemgraphStore
from cashclaw_adapter.models import TaskRecord, TaskStatus


class FakeConnection:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        self.executed.append((query, parameters))

    def execute_and_fetch(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, int]]:
        self.executed.append((query, parameters))
        if self.should_fail:
            raise RuntimeError("cannot reach memgraph")
        return [{"ok": 1}]


def build_task() -> TaskRecord:
    return TaskRecord(
        task_id="task-1",
        status=TaskStatus.ACCEPTED,
        title="Build",
        instructions="Implement",
        agent_id="agent-1",
        client_address="0xabc",
        requested_by="0xabc",
        callback_url="https://example.com/callback",
        category="development",
        budget_wei="1000",
        quoted_price_wei="900",
        result="Done",
        metadata={"priority": "high"},
        upstream_payload={"id": "task-1"},
    )


def test_ping_returns_healthy_when_query_succeeds() -> None:
    store = MemgraphStore(FakeConnection())
    status = store.ping()
    assert status.healthy is True
    assert status.detail is None


def test_ping_returns_error_detail_when_query_fails() -> None:
    store = MemgraphStore(FakeConnection(should_fail=True))
    status = store.ping()
    assert status.healthy is False
    assert "cannot reach memgraph" in str(status.detail)


def test_upsert_task_emits_expected_parameters() -> None:
    connection = FakeConnection()
    store = MemgraphStore(connection)

    store.upsert_task(build_task())

    assert len(connection.executed) == 1
    query, parameters = connection.executed[0]
    assert "MERGE (task:Task" in query
    assert parameters == {
        "task_id": "task-1",
        "status": "accepted",
        "title": "Build",
        "instructions": "Implement",
        "agent_id": "agent-1",
        "client_address": "0xabc",
        "project_id": None,
        "session_id": None,
        "requested_by": "0xabc",
        "callback_url": "https://example.com/callback",
        "category": "development",
        "budget_wei": "1000",
        "quoted_price_wei": "900",
        "result": "Done",
        "metadata": {"priority": "high"},
    }
