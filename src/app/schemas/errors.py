"""Shared OpenAPI models for HTTP error bodies."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    """JSON body for API errors."""

    code: str | None = None
    detail: str
    context: dict[str, Any] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"code": "user_case.error_code", "detail": "Error message."},
                {
                    "code": "schedule.booking_conflict",
                    "detail": "Schedule changes affect existing bookings.",
                    "context": {"conflicts": []},
                },
            ],
        },
    )
