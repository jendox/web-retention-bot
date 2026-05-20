"""Rules that split in-app notifications between client and master cabinets."""

from app.repositories.notification_cabinet import (
    notification_belongs_to_client_cabinet,
    notification_belongs_to_master_cabinet,
)
from app.services.notifications.mail_render import (
    BOOKING_EMAIL_AUDIENCE_CLIENT,
    BOOKING_EMAIL_AUDIENCE_MASTER,
)


def test_client_cabinet_matches_client_audience_literal():
    clause = notification_belongs_to_client_cabinet()
    assert clause is not None
    compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert BOOKING_EMAIL_AUDIENCE_CLIENT in compiled
    assert "%/client%" in compiled.lower() or "/client" in compiled


def test_master_cabinet_matches_master_audience_literal():
    clause = notification_belongs_to_master_cabinet()
    compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert BOOKING_EMAIL_AUDIENCE_MASTER in compiled
    assert "master" in compiled.lower()
