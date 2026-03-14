from __future__ import annotations

import pytest
from pydantic import ValidationError

from cashclaw_adapter.models import TaskCreateRequest, TaskRecord, TaskStatus


def test_task_create_request_requires_non_empty_title() -> None:
    with pytest.raises(ValidationError):
        TaskCreateRequest(title="", instructions="Do it")


def test_task_create_request_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TaskCreateRequest(title="Valid", instructions="Do it", unexpected=True)


def test_task_create_request_defaults_metadata() -> None:
    model = TaskCreateRequest(title="Valid", instructions="Do it")
    assert model.metadata == {}


def test_task_record_preserves_enum_and_upstream_payload() -> None:
    record = TaskRecord(
        task_id="task-1",
        status=TaskStatus.COMPLETED,
        title="Ship",
        instructions="Deploy",
        upstream_payload={"status": "completed"},
    )

    assert record.status is TaskStatus.COMPLETED
    assert record.upstream_payload["status"] == "completed"
