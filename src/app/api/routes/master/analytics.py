from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_master_profile
from app.models.master import MasterProfile
from app.schemas.analytics import AnalyticsPeriodPreset, MasterAnalyticsOut
from app.schemas.errors import ErrorDetail
from app.use_cases.analytics import GetMasterAnalyticsUseCase, get_master_analytics_use_case

router = APIRouter(prefix="/analytics", tags=["master-analytics"])


@router.get(
    path="",
    summary="Master analytics summary",
    description=(
        "Aggregates completed, cancelled and no-show bookings for the selected period. "
        "Money is based on booking snapshots and grouped by snapshot currency."
    ),
    response_model=MasterAnalyticsOut,
    status_code=status.HTTP_200_OK,
    response_description="Analytics summary for the current master.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorDetail, "description": "Invalid period parameters."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorDetail, "description": "Missing or invalid session cookie."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorDetail, "description": "Email not verified."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorDetail, "description": "Current user has no master profile."},
    },
)
async def get_master_analytics(
    master: Annotated[MasterProfile, Depends(require_master_profile)],
    use_case: Annotated[GetMasterAnalyticsUseCase, Depends(get_master_analytics_use_case)],
    period: Annotated[
        AnalyticsPeriodPreset | None,
        Query(description="Preset analytics period. Ignored when both from/to are provided."),
    ] = None,
    from_date: Annotated[
        date | None,
        Query(alias="from", description="Custom period start date in master's timezone."),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(alias="to", description="Custom period end date in master's timezone."),
    ] = None,
) -> MasterAnalyticsOut:
    try:
        return await use_case(
            master,
            preset=period,
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
