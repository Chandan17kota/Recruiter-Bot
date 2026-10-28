"""One error envelope everywhere: {"error": {"code", "message", "details"}}.

Database exception text never reaches the client; it is logged server-side.
"""
import logging

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.matching_service import NotFoundError

log = logging.getLogger("recruiter_bot")


def envelope(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message, "details": details}})


async def _validation(_: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in e.get("loc", ()) if p not in ("query", "path")) or "request",
         "location": (e.get("loc") or ["request"])[0],
         "message": e.get("msg", "invalid value")}
        for e in exc.errors()
    ]
    return envelope(422, "VALIDATION_ERROR", "Request parameters are invalid", details)


async def _not_found(_: Request, exc: NotFoundError):
    return envelope(404, exc.code, exc.message)


async def _http(_: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return envelope(404, "ROUTE_NOT_FOUND", "No such route")
    if exc.status_code == 405:
        return envelope(405, "METHOD_NOT_ALLOWED", "Method not allowed on this route")
    return envelope(exc.status_code, "HTTP_ERROR", str(exc.detail))


async def _db_unavailable(_: Request, exc: psycopg.OperationalError):
    # Covers connection failures, PoolTimeout and QueryCanceled (statement_timeout),
    # all of which subclass OperationalError in psycopg 3.
    log.error("Database unavailable: %r", exc)
    return envelope(503, "DATABASE_UNAVAILABLE", "The database is unavailable, please retry shortly")


async def _db_error(_: Request, exc: psycopg.Error):
    log.exception("Database error", exc_info=exc)
    return envelope(500, "INTERNAL_ERROR", "An internal error occurred")


async def _unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)
    return envelope(500, "INTERNAL_ERROR", "An internal error occurred")


def register(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(NotFoundError, _not_found)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(psycopg.OperationalError, _db_unavailable)
    app.add_exception_handler(psycopg.Error, _db_error)
    app.add_exception_handler(Exception, _unhandled)
