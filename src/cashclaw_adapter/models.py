"""Pydantic models used by the adapter."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TaskStatus(StrEnum):
    """Normalized task statuses returned by the adapter."""

    REQUESTED = "requested"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    SUBMITTED = "submitted"
    REVISION = "revision"
    COMPLETED = "completed"
    DECLINED = "declined"
    EXPIRED = "expired"
    DISPUTED = "disputed"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class DependencyHealth(BaseModel):
    """Health state for a single dependency."""

    healthy: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    """Adapter health response."""

    status: str
    service: str
    version: str
    cashclaw: DependencyHealth
    memgraph: DependencyHealth


class TaskCreateRequest(BaseModel):
    """Request payload accepted by the adapter."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1)
    project_id: str | None = Field(default=None, min_length=1, max_length=100)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)
    requested_by: str | None = Field(default=None, min_length=1, max_length=100)
    callback_url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskFileRecord(BaseModel):
    """File attached to a CashClaw task."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    size: int = Field(ge=0)
    uploaded_at: int = Field(ge=0)


class TaskMessageRecord(BaseModel):
    """Message attached to a CashClaw task."""

    model_config = ConfigDict(extra="forbid")

    sender: str = Field(min_length=1)
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)
    timestamp: int = Field(ge=0)


class TaskRecord(BaseModel):
    """Normalized task representation used by the adapter."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    status: TaskStatus
    title: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    agent_id: str | None = None
    client_address: str | None = None
    project_id: str | None = None
    session_id: str | None = None
    requested_by: str | None = None
    callback_url: str | None = None
    category: str | None = None
    budget_wei: str | None = None
    quoted_price_wei: str | None = None
    quoted_message: str | None = None
    result: str | None = None
    tx_hash: str | None = None
    claimed_at: int | None = None
    quoted_at: int | None = None
    accepted_at: int | None = None
    submitted_at: int | None = None
    completed_at: int | None = None
    disputed_at: int | None = None
    resolved_at: int | None = None
    rated_at: int | None = None
    rated_score: int | None = None
    rated_comment: str | None = None
    revision_count: int | None = None
    dispute_resolution: str | None = None
    files: list[TaskFileRecord] = Field(default_factory=list)
    messages: list[TaskMessageRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    upstream_payload: dict[str, Any] = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    """Collection of tasks returned by the adapter."""

    tasks: list[TaskRecord]


class ErrorResponse(BaseModel):
    """Error payload returned by the adapter."""

    detail: str
