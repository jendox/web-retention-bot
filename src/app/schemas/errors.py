"""Shared OpenAPI models for HTTP error bodies (``HTTPException`` shape)."""

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    """JSON body for ``HTTPException`` when ``detail`` is a plain string."""

    code: str | None = None
    detail: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"code": "user_case.error_code", "detail": "Error message."},
            ],
        },
    )
