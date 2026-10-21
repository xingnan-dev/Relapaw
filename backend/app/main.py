from pathlib import Path
import json
import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.api.errors import APIError
from app.api.router import api_router
from app.core.config import Settings, settings
from app.db.session import engine
from app.demo.dataset_v1 import SCHEMA_REVISION


EXPECTED_STATIC_DIR = (Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
request_logger = logging.getLogger("relapaw.request")


def error_payload(code: str, message: str, details=None):
    return {"error": {"code": code, "message": message, "details": details}}


def validate_static_dir(app_settings: Settings, *, expected_static_dir: Path = EXPECTED_STATIC_DIR) -> Path | None:
    configured = app_settings.static_dir
    if configured is None:
        if app_settings.environment == "demo":
            raise RuntimeError("RELAPAW_STATIC_DIR is required in demo mode")
        return None
    path = configured.expanduser()
    if not path.is_absolute():
        raise RuntimeError("RELAPAW_STATIC_DIR must be an absolute path")
    resolved = path.resolve()
    if resolved != expected_static_dir.resolve():
        raise RuntimeError("RELAPAW_STATIC_DIR must point to this repository's frontend/dist")
    if not resolved.is_dir():
        raise RuntimeError("RELAPAW_STATIC_DIR must be an existing directory")
    if not (resolved / "index.html").is_file():
        raise RuntimeError("RELAPAW_STATIC_DIR must contain index.html")
    return resolved


def create_app(app_settings: Settings = settings, *, expected_static_dir: Path = EXPECTED_STATIC_DIR) -> FastAPI:
    static_dir = validate_static_dir(app_settings, expected_static_dir=expected_static_dir)
    application = FastAPI(title=app_settings.app_name, version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)

    @application.middleware("http")
    async def request_observability(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_template = getattr(route, "path", None)
            if (
                isinstance(route_template, str)
                and request.url.path.startswith("/api/v1/")
                and not route_template.startswith("/api/v1/")
            ):
                route_template = f"/api/v1{route_template}"
            request_logger.info(json.dumps({
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": route_template if isinstance(route_template, str) else "<unmatched>",
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
                "environment": app_settings.environment,
                "deployment_version": app_settings.deployment_version,
            }, separators=(",", ":")))

    @application.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError):
        return JSONResponse(content=error_payload(exc.code, exc.message, exc.details), status_code=exc.status_code)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        details = [
            {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(content=error_payload("VALIDATION_ERROR", "Request validation failed", details), status_code=422)

    @application.exception_handler(IntegrityError)
    async def integrity_error_handler(_request: Request, _exc: IntegrityError):
        return JSONResponse(
            content=error_payload("RESOURCE_CONFLICT", "Resource conflicts with existing data"),
            status_code=409,
        )

    @application.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException):
        return JSONResponse(content=error_payload("HTTP_ERROR", str(exc.detail)), status_code=exc.status_code)

    @application.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, _exc: Exception):
        return JSONResponse(
            content=error_payload("INTERNAL_ERROR", "An unexpected error occurred"),
            status_code=500,
        )

    @application.get("/health")
    def health():
        return {
            "status": "ok",
            "phase": "0.1",
            "environment": app_settings.environment,
            "static_frontend": static_dir is not None,
            "deployment_version": app_settings.deployment_version,
        }

    @application.get("/ready")
    def ready():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "database": "unavailable", "schema": "unknown"},
            )
        if revision != SCHEMA_REVISION:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "database": "ok", "schema": "mismatch"},
            )
        return {"status": "ready", "database": "ok", "schema": "current", "deployment_version": app_settings.deployment_version}

    # Mount last so exact API and health routes always have priority.
    if static_dir is not None:
        application.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return application


app = create_app()
