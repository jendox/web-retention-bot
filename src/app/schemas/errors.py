"""Shared OpenAPI models for HTTP error bodies (``HTTPException`` shape)."""

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    """JSON body for ``HTTPException`` when ``detail`` is a plain string."""

    detail: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"detail": "Error message."},
            ],
        },
    )
