"""Typed client for the upstream CashClaw API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import requests

from cashclaw_adapter.config import Settings
from cashclaw_adapter.models import TaskFileRecord, TaskMessageRecord, TaskRecord, TaskStatus


class CashClawError(Exception):
    """Base class for upstream CashClaw errors."""


class CashClawUnavailableError(CashClawError):
    """Raised when the upstream service cannot be reached."""


class CashClawResponseError(CashClawError):
    """Raised when the upstream service returns an unexpected response."""


class CashClawClientError(CashClawError):
    """Raised for upstream 4xx responses."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class CashClawServerError(CashClawError):
    """Raised for upstream 5xx responses."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class CashClawTaskNotFoundError(CashClawError):
    """Raised when a task cannot be found in the active task list."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"CashClaw task not found: {task_id}")


@dataclass(slots=True)
class UpstreamHealth:
    """Health result returned by the upstream service."""

    healthy: bool
    detail: str | None = None


class CashClawClient:
    """Typed wrapper around the verified CashClaw dashboard HTTP contract."""

    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self._settings = settings
        self._session = session or requests.Session()

    def check_health(self) -> UpstreamHealth:
        """Check upstream health."""

        setup = self._request_json("GET", "/api/setup/status", retryable=True)
        configured = bool(setup.get("configured"))
        mode = self._optional_str(setup.get("mode")) or "unknown"
        step = self._optional_str(setup.get("step"))

        if not configured:
            detail = (
                "CashClaw reachable but not configured "
                f"(mode={mode}, step={step or 'unknown'})"
            )
            return UpstreamHealth(healthy=False, detail=detail)

        payload = self._request_json("GET", "/api/status", retryable=True)
        running = bool(payload.get("running"))
        active_tasks = self._optional_int(payload.get("activeTasks")) or 0
        agent_id = self._optional_str(payload.get("agentId"))
        detail = (
            f"mode={mode}, running={running}, active_tasks={active_tasks}, "
            f"agent_id={agent_id or 'unknown'}"
        )
        return UpstreamHealth(healthy=running, detail=detail)

    def list_tasks(self) -> list[TaskRecord]:
        """List active tasks from CashClaw."""

        payload = self._request_json("GET", "/api/tasks", retryable=True)
        raw_tasks = payload.get("tasks")
        if not isinstance(raw_tasks, list):
            raise CashClawResponseError("CashClaw tasks payload is missing the tasks list")
        return [self._parse_task(task) for task in raw_tasks]

    def get_task(self, task_id: str) -> TaskRecord:
        """Fetch a task by filtering CashClaw's active task list."""

        for task in self.list_tasks():
            if task.task_id == task_id:
                return task
        raise CashClawTaskNotFoundError(task_id)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> dict[str, Any]:
        attempts = 1 + (self._settings.cashclaw_safe_retry_count if retryable else 0)
        timeout = (
            self._settings.cashclaw_connect_timeout_sec,
            self._settings.cashclaw_timeout_sec,
        )
        url = f"{self._settings.cashclaw_base_url.rstrip('/')}{path}"
        last_error: Exception | None = None

        for _ in range(attempts):
            try:
                response = self._session.request(method, url, json=json, timeout=timeout)
                return self._handle_response(response)
            except requests.RequestException as exc:
                last_error = exc

        message = f"CashClaw request failed for {method} {path}"
        raise CashClawUnavailableError(message) from last_error

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        status_code = response.status_code
        data = self._parse_response_json(response)
        if 200 <= status_code < 300:
            return data

        if status_code == 503 and data.get("mode") == "setup":
            raise CashClawUnavailableError("CashClaw agent is not configured yet")
        detail = self._extract_detail(data) or response.reason or "CashClaw request failed"
        if 400 <= status_code < 500:
            raise CashClawClientError(status_code, detail)
        if status_code >= 500:
            raise CashClawServerError(status_code, detail)
        raise CashClawResponseError(f"Unexpected upstream status code: {status_code}")

    def _parse_response_json(self, response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise CashClawResponseError("CashClaw returned non-JSON data") from exc

        if not isinstance(payload, dict):
            raise CashClawResponseError("CashClaw returned a non-object JSON payload")
        return payload

    def _extract_detail(self, payload: dict[str, Any]) -> str | None:
        for key in ("detail", "error"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        return None

    def _parse_task(self, payload: Any) -> TaskRecord:
        if not isinstance(payload, dict):
            raise CashClawResponseError("CashClaw task entry is not a JSON object")

        task_id = payload.get("id")
        instructions = payload.get("task")
        status_value = payload.get("status")
        if not isinstance(task_id, str) or not isinstance(instructions, str):
            raise CashClawResponseError("CashClaw task payload is missing required fields")
        title = self._derive_title(instructions)

        return TaskRecord(
            task_id=task_id,
            status=self._parse_status(status_value),
            title=title,
            instructions=instructions,
            agent_id=self._optional_str(payload.get("agentId")),
            client_address=self._optional_str(payload.get("clientAddress")),
            requested_by=self._optional_str(payload.get("clientAddress")),
            category=self._optional_str(payload.get("category")),
            budget_wei=self._optional_str(payload.get("budgetWei")),
            quoted_price_wei=self._optional_str(payload.get("quotedPriceWei")),
            quoted_message=self._optional_str(payload.get("quotedMessage")),
            result=self._optional_str(payload.get("result")),
            tx_hash=self._optional_str(payload.get("txHash")),
            claimed_at=self._optional_int(payload.get("claimedAt")),
            quoted_at=self._optional_int(payload.get("quotedAt")),
            accepted_at=self._optional_int(payload.get("acceptedAt")),
            submitted_at=self._optional_int(payload.get("submittedAt")),
            completed_at=self._optional_int(payload.get("completedAt")),
            disputed_at=self._optional_int(payload.get("disputedAt")),
            resolved_at=self._optional_int(payload.get("resolvedAt")),
            rated_at=self._optional_int(payload.get("ratedAt")),
            rated_score=self._optional_int(payload.get("ratedScore")),
            rated_comment=self._optional_str(payload.get("ratedComment")),
            revision_count=self._optional_int(payload.get("revisionCount")),
            dispute_resolution=self._optional_str(payload.get("disputeResolution")),
            files=self._parse_files(payload.get("files")),
            messages=self._parse_messages(payload.get("messages")),
            metadata={},
            upstream_payload=payload,
        )

    def _parse_status(self, value: Any) -> TaskStatus:
        if not isinstance(value, str):
            raise CashClawResponseError("CashClaw task payload has an invalid status")
        try:
            return TaskStatus(value)
        except ValueError as exc:
            raise CashClawResponseError("CashClaw task payload has an unknown status") from exc

    def _optional_str(self, value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    def _optional_int(self, value: Any) -> int | None:
        return value if isinstance(value, int) else None

    def _parse_files(self, value: Any) -> list[TaskFileRecord]:
        if not isinstance(value, list):
            return []
        files: list[TaskFileRecord] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            name = item.get("name")
            size = item.get("size")
            uploaded_at = item.get("uploadedAt")
            is_valid_file = (
                isinstance(key, str)
                and isinstance(name, str)
                and isinstance(size, int)
                and isinstance(uploaded_at, int)
            )
            if is_valid_file:
                file_key = cast(str, key)
                file_name = cast(str, name)
                file_size = cast(int, size)
                file_uploaded_at = cast(int, uploaded_at)
                files.append(
                    TaskFileRecord(
                        key=file_key,
                        name=file_name,
                        size=file_size,
                        uploaded_at=file_uploaded_at,
                    )
                )
        return files

    def _parse_messages(self, value: Any) -> list[TaskMessageRecord]:
        if not isinstance(value, list):
            return []
        messages: list[TaskMessageRecord] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            sender = item.get("sender")
            role = item.get("role")
            content = item.get("content")
            timestamp = item.get("timestamp")
            if (
                isinstance(sender, str)
                and isinstance(role, str)
                and isinstance(content, str)
                and isinstance(timestamp, int)
            ):
                messages.append(
                    TaskMessageRecord(
                        sender=sender,
                        role=role,
                        content=content,
                        timestamp=timestamp,
                    )
                )
        return messages

    def _derive_title(self, instructions: str) -> str:
        first_line = instructions.strip().splitlines()[0]
        compact = " ".join(first_line.split())
        return compact[:80] if compact else "CashClaw task"
