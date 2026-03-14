"""Typed client for the upstream CashClaw API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from cashclaw_adapter.config import Settings
from cashclaw_adapter.models import TaskCreateRequest, TaskRecord, TaskStatus


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


@dataclass(slots=True)
class UpstreamHealth:
    """Health result returned by the upstream service."""

    healthy: bool
    detail: str | None = None


class CashClawClient:
    """Small typed wrapper around the placeholder CashClaw HTTP contract."""

    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self._settings = settings
        self._session = session or requests.Session()

    def check_health(self) -> UpstreamHealth:
        """Check upstream health."""

        payload = self._request_json("GET", "/api/health", retryable=True)
        detail = payload.get("detail")
        return UpstreamHealth(healthy=True, detail=detail if isinstance(detail, str) else None)

    def create_task(self, request: TaskCreateRequest) -> TaskRecord:
        """Create a task upstream using the current placeholder contract."""

        payload = self._request_json("POST", "/api/tasks", json=request.model_dump(mode="json"))
        return self._parse_task(payload, fallback=request)

    def get_task(self, task_id: str) -> TaskRecord:
        """Fetch a task upstream."""

        payload = self._request_json("GET", f"/api/tasks/{task_id}", retryable=True)
        return self._parse_task(payload)

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
        detail = payload.get("detail")
        return detail if isinstance(detail, str) else None

    def _parse_task(
        self,
        payload: dict[str, Any],
        *,
        fallback: TaskCreateRequest | None = None,
    ) -> TaskRecord:
        task_id = payload.get("task_id")
        title = payload.get("title") or (fallback.title if fallback else None)
        instructions = payload.get("instructions") or (fallback.instructions if fallback else None)
        status_value = payload.get("status", TaskStatus.PENDING.value)
        if not isinstance(task_id, str) or not isinstance(title, str) or not isinstance(
            instructions, str
        ):
            raise CashClawResponseError("CashClaw task payload is missing required fields")

        return TaskRecord(
            task_id=task_id,
            status=self._parse_status(status_value),
            title=title,
            instructions=instructions,
            project_id=self._optional_str(payload.get("project_id"))
            or (fallback.project_id if fallback else None),
            session_id=self._optional_str(payload.get("session_id"))
            or (fallback.session_id if fallback else None),
            requested_by=self._optional_str(payload.get("requested_by"))
            or (fallback.requested_by if fallback else None),
            callback_url=self._optional_str(payload.get("callback_url"))
            or (str(fallback.callback_url) if fallback and fallback.callback_url else None),
            metadata=self._coerce_dict(payload.get("metadata"))
            or (fallback.metadata if fallback else {}),
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

    def _coerce_dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}
