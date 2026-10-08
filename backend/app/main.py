from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.errors import APIError
from app.api.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


def error_payload(code: str, message: str, details=None):
    return {"error": {"code": code, "message": message, "details": details}}


@app.exception_handler(APIError)
async def api_error_handler(_request: Request, exc: APIError):
    return JSONResponse(content=error_payload(exc.code, exc.message, exc.details), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    details = [
        {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(content=error_payload("VALIDATION_ERROR", "Request validation failed", details), status_code=422)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, _exc: IntegrityError):
    return JSONResponse(
        content=error_payload("RESOURCE_CONFLICT", "Resource conflicts with existing data"),
        status_code=409,
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, exc: HTTPException):
    return JSONResponse(content=error_payload("HTTP_ERROR", str(exc.detail)), status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, _exc: Exception):
    return JSONResponse(
        content=error_payload("INTERNAL_ERROR", "An unexpected error occurred"),
        status_code=500,
    )


@app.get("/health")
def health():
    return {"status": "ok", "phase": "0.1"}
