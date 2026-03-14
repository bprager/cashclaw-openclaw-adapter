"""Pydantic models used by the adapter."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TaskStatus(StrEnum):
    """Normalized task statuses returned by the adapter."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
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


class TaskRecord(BaseModel):
    """Normalized task representation used by the adapter."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    status: TaskStatus
    title: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    project_id: str | None = None
    session_id: str | None = None
    requested_by: str | None = None
    callback_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    upstream_payload: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error payload returned by the adapter."""

    detail: str
