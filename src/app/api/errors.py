from typing import NoReturn

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


def app_error_status_code(error: AppError) -> int:
    if isinstance(error, UnauthorizedError):
        return status.HTTP_401_UNAUTHORIZED
    if isinstance(error, ForbiddenError):
        return status.HTTP_403_FORBIDDEN
    if isinstance(error, NotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, ConflictError):
        return status.HTTP_409_CONFLICT
    if isinstance(error, ValidationError):
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_400_BAD_REQUEST


def raise_http_error(error: AppError) -> NoReturn:
    raise HTTPException(status_code=app_error_status_code(error), detail=error.message) from None


async def app_error_handler(_request: Request, error: AppError) -> Response:
    return JSONResponse(
        status_code=app_error_status_code(error),
        content={"code": error.code, "detail": error.message},
    )
