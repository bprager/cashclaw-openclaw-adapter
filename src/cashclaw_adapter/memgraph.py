"""Memgraph persistence layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from gqlalchemy import Memgraph  # type: ignore[import-untyped]

from cashclaw_adapter.config import Settings
from cashclaw_adapter.models import TaskRecord


class MemgraphConnection(Protocol):
    """Protocol for the subset of Memgraph operations the adapter needs."""

    def execute(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a write query."""

    def execute_and_fetch(self, query: str, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a read query and fetch results."""


@dataclass(slots=True)
class DependencyCheck:
    """Health result for Memgraph."""

    healthy: bool
    detail: str | None = None


class MemgraphStore:
    """Encapsulate graph writes for durable adapter state."""

    def __init__(self, connection: MemgraphConnection):
        self._connection = connection

    @classmethod
    def from_settings(cls, settings: Settings) -> MemgraphStore:
        """Create a store from application settings."""

        connection = Memgraph(
            host=settings.memgraph_host,
            port=settings.memgraph_port,
            username=settings.memgraph_username or None,
            password=settings.memgraph_password or None,
            encrypted=settings.memgraph_encrypted,
        )
        return cls(connection)

    def ping(self) -> DependencyCheck:
        """Check whether Memgraph can answer a trivial query."""

        try:
            list(self._connection.execute_and_fetch("RETURN 1 AS ok"))
        except Exception as exc:
            return DependencyCheck(healthy=False, detail=str(exc))
        return DependencyCheck(healthy=True)

    def upsert_task(self, task: TaskRecord) -> None:
        """Write a normalized task node into Memgraph."""

        query = """
        MERGE (task:Task {task_id: $task_id})
        SET task.status = $status,
            task.title = $title,
            task.instructions = $instructions,
            task.agent_id = $agent_id,
            task.client_address = $client_address,
            task.project_id = $project_id,
            task.session_id = $session_id,
            task.requested_by = $requested_by,
            task.callback_url = $callback_url,
            task.category = $category,
            task.budget_wei = $budget_wei,
            task.quoted_price_wei = $quoted_price_wei,
            task.result = $result,
            task.metadata = $metadata
        """
        self._connection.execute(query, parameters=self._task_params(task))

    def _task_params(self, task: TaskRecord) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "title": task.title,
            "instructions": task.instructions,
            "agent_id": task.agent_id,
            "client_address": task.client_address,
            "project_id": task.project_id,
            "session_id": task.session_id,
            "requested_by": task.requested_by,
            "callback_url": task.callback_url,
            "category": task.category,
            "budget_wei": task.budget_wei,
            "quoted_price_wei": task.quoted_price_wei,
            "result": task.result,
            "metadata": task.metadata,
        }
