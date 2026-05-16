"""Replace weekly rules + overrides in one transaction."""

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.structured_logging import get_logger, log_context
from app.models.schedule import WeeklyScheduleRule, WorkdayOverride
from app.repositories.schedules import ScheduleRepository
from app.schemas.master import WeeklyScheduleRuleIn, WorkdayOverrideIn
from app.services.availability import parse_clock

logger = get_logger("app.schedule")


async def replace_master_schedule(
    session: AsyncSession,
    master_id: UUID,
    *,
    weekly: list[WeeklyScheduleRuleIn],
    overrides: list[WorkdayOverrideIn],
) -> None:
    with log_context(use_case="replace_master_schedule", master_id=str(master_id)):
        schedule_repo = ScheduleRepository(session)

        weekly_models: list[WeeklyScheduleRule] = []
        for rule in weekly:
            weekly_models.append(
                WeeklyScheduleRule(
                    master_id=master_id,
                    weekday=rule.weekday,
                    start_time=parse_clock(rule.start_time),
                    end_time=parse_clock(rule.end_time),
                ),
            )

        override_models: list[WorkdayOverride] = []
        for ov in overrides:
            start_t = parse_clock(ov.start_time) if ov.start_time else None
            end_t = parse_clock(ov.end_time) if ov.end_time else None
            if not ov.is_closed and ((start_t is None) ^ (end_t is None)):
                logger.warning("failed", reason="invalid_override_window", override_date=ov.override_date)
                msg = "Override requires both window edges unless marked closed."
                raise ValueError(msg)

            parsed_date = date.fromisoformat(ov.override_date)
            override_models.append(
                WorkdayOverride(
                    master_id=master_id,
                    override_date=parsed_date,
                    is_closed=ov.is_closed,
                    start_time=start_t,
                    end_time=end_t,
                    note=ov.note,
                ),
            )

        await schedule_repo.replace_weekly_rules(master_id, weekly_models)
        await schedule_repo.replace_overrides(master_id, override_models)
        await session.flush()
        logger.info("replaced", weekly_count=len(weekly_models), override_count=len(override_models))


__all__ = ["replace_master_schedule"]
