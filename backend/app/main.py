from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from app.api.errors import APIError
from app.api.router import api_router
from app.core.config import Settings, settings


EXPECTED_STATIC_DIR = (Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()


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
        }

    # Mount last so exact API and health routes always have priority.
    if static_dir is not None:
        application.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
    return application


app = create_app()
