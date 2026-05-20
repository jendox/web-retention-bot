from app.schemas.booking import BookingCancel, BookingReschedule, normalize_booking_comment


def test_normalize_booking_comment() -> None:
    assert normalize_booking_comment(None) is None
    assert normalize_booking_comment("   ") is None
    assert normalize_booking_comment("  Привет  ") == "Привет"


def test_booking_cancel_schema_strips_comment() -> None:
    payload = BookingCancel(comment="  текст  ")
    assert payload.comment == "текст"


def test_booking_reschedule_schema_strips_comment() -> None:
    from datetime import UTC, datetime

    payload = BookingReschedule(
        start_at=datetime(2026, 5, 20, 10, 0, tzinfo=UTC),
        comment="  перенос  ",
    )
    assert payload.comment == "перенос"
