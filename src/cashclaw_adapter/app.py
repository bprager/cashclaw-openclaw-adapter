"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from cashclaw_adapter import __version__
from cashclaw_adapter.cashclaw_client import (
    CashClawClient,
    CashClawClientError,
    CashClawError,
    CashClawResponseError,
    CashClawServerError,
    CashClawTaskNotFoundError,
    CashClawUnavailableError,
)
from cashclaw_adapter.config import Settings, get_settings
from cashclaw_adapter.memgraph import MemgraphStore
from cashclaw_adapter.models import (
    DependencyHealth,
    ErrorResponse,
    HealthResponse,
    TaskCreateRequest,
    TaskListResponse,
    TaskRecord,
)


def configure_logging(level: str) -> None:
    """Configure application logging once."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s %(message)s",
    )


def build_cashclaw_client(settings: Settings) -> CashClawClient:
    """Construct the default CashClaw client."""

    return CashClawClient(settings)


def build_memgraph_store(settings: Settings) -> MemgraphStore:
    """Construct the default Memgraph store."""

    return MemgraphStore.from_settings(settings)


def create_app(
    *,
    settings: Settings | None = None,
    cashclaw_client_factory: Callable[[Settings], CashClawClient] = build_cashclaw_client,
    memgraph_store_factory: Callable[[Settings], MemgraphStore] = build_memgraph_store,
) -> FastAPI:
    """Create the FastAPI application."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    logger = logging.getLogger("cashclaw_adapter.app")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if resolved_settings.startup_validate_dependencies:
            _validate_dependencies(app.state.cashclaw_client, app.state.memgraph_store)
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.cashclaw_client = cashclaw_client_factory(resolved_settings)
    app.state.memgraph_store = memgraph_store_factory(resolved_settings)

    @app.middleware("http")
    async def add_request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        logger.info(
            "request.start method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request.finish method=%s path=%s status=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
        )
        return response

    @app.middleware("http")
    async def require_localhost(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not resolved_settings.adapter_require_localhost:
            return await call_next(request)
        client_host = request.client.host if request.client else None
        if not _is_loopback_host(client_host):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=ErrorResponse(detail="Adapter only accepts localhost traffic").model_dump(),
            )
        return await call_next(request)

    @app.exception_handler(CashClawClientError)
    async def handle_cashclaw_client_error(
        _request: Request,
        exc: CashClawClientError,
    ) -> JSONResponse:
        detail = f"CashClaw client error ({exc.status_code}): {exc.detail}"
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(detail=detail).model_dump(),
        )

    @app.exception_handler(CashClawServerError)
    async def handle_cashclaw_server_error(
        _request: Request,
        exc: CashClawServerError,
    ) -> JSONResponse:
        detail = f"CashClaw server error ({exc.status_code}): {exc.detail}"
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(detail=detail).model_dump(),
        )

    @app.exception_handler(CashClawUnavailableError)
    async def handle_cashclaw_unavailable_error(
        _request: Request,
        exc: CashClawUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )

    @app.exception_handler(CashClawTaskNotFoundError)
    async def handle_cashclaw_task_not_found_error(
        _request: Request,
        exc: CashClawTaskNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )

    @app.exception_handler(CashClawResponseError)
    async def handle_cashclaw_response_error(
        _request: Request,
        exc: CashClawResponseError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(detail=str(exc)).model_dump(),
        )

    def get_cashclaw_client(request: Request) -> CashClawClient:
        return cast(CashClawClient, request.app.state.cashclaw_client)

    def get_memgraph_store(request: Request) -> MemgraphStore:
        return cast(MemgraphStore, request.app.state.memgraph_store)

    @app.get("/health", response_model=HealthResponse)
    async def health(
        cashclaw_client: CashClawClient = Depends(get_cashclaw_client),
        memgraph_store: MemgraphStore = Depends(get_memgraph_store),
    ) -> HealthResponse:
        cashclaw = _health_from_cashclaw(cashclaw_client)
        memgraph = memgraph_store.ping()
        status_value = "ok" if cashclaw.healthy and memgraph.healthy else "degraded"
        return HealthResponse(
            status=status_value,
            service=resolved_settings.app_name,
            version=__version__,
            cashclaw=DependencyHealth(healthy=cashclaw.healthy, detail=cashclaw.detail),
            memgraph=DependencyHealth(healthy=memgraph.healthy, detail=memgraph.detail),
        )

    @app.post("/tasks", response_model=TaskRecord, status_code=status.HTTP_201_CREATED)
    async def create_task(
        _payload: TaskCreateRequest,
    ) -> TaskRecord:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "CashClaw's local HTTP API does not support task creation; "
                "use GET /tasks to monitor inbox tasks."
            ),
        )

    @app.get("/tasks", response_model=TaskListResponse)
    async def list_tasks(
        request: Request,
        cashclaw_client: CashClawClient = Depends(get_cashclaw_client),
        memgraph_store: MemgraphStore = Depends(get_memgraph_store),
    ) -> TaskListResponse:
        tasks = cashclaw_client.list_tasks()
        _write_tasks(memgraph_store, tasks, request.state.request_id, logger)
        return TaskListResponse(tasks=tasks)

    @app.get("/tasks/{task_id}", response_model=TaskRecord)
    async def get_task(
        task_id: str,
        request: Request,
        cashclaw_client: CashClawClient = Depends(get_cashclaw_client),
        memgraph_store: MemgraphStore = Depends(get_memgraph_store),
    ) -> TaskRecord:
        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="task_id is required",
            )
        task = cashclaw_client.get_task(task_id)
        _write_task(memgraph_store, task, request.state.request_id, logger)
        return task

    return app


def _health_from_cashclaw(client: CashClawClient) -> DependencyHealth:
    try:
        health = client.check_health()
    except CashClawUnavailableError as exc:
        return DependencyHealth(healthy=False, detail=str(exc))
    except CashClawError as exc:
        return DependencyHealth(healthy=False, detail=str(exc))
    return DependencyHealth(healthy=health.healthy, detail=health.detail)


def _is_loopback_host(client_host: str | None) -> bool:
    return client_host in {"127.0.0.1", "::1", "testclient"}


def _validate_dependencies(cashclaw_client: CashClawClient, memgraph_store: MemgraphStore) -> None:
    try:
        health = cashclaw_client.check_health()
    except CashClawError as exc:
        raise RuntimeError("CashClaw startup validation failed") from exc

    if not health.healthy:
        raise RuntimeError("CashClaw startup validation failed: upstream reported unhealthy")

    memgraph_status = memgraph_store.ping()
    if not memgraph_status.healthy:
        raise RuntimeError(f"Memgraph startup validation failed: {memgraph_status.detail}")


def _write_task(
    memgraph_store: MemgraphStore,
    task: TaskRecord,
    request_id: str,
    logger: logging.Logger,
) -> None:
    try:
        memgraph_store.upsert_task(task)
    except Exception as exc:
        logger.exception(
            "memgraph.write_failed task_id=%s request_id=%s error=%s",
            task.task_id,
            request_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memgraph write failed",
        ) from exc

    logger.info("memgraph.write_ok task_id=%s request_id=%s", task.task_id, request_id)


def _write_tasks(
    memgraph_store: MemgraphStore,
    tasks: list[TaskRecord],
    request_id: str,
    logger: logging.Logger,
) -> None:
    for task in tasks:
        _write_task(memgraph_store, task, request_id, logger)


app = create_app()
