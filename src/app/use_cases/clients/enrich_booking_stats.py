from __future__ import annotations

from uuid import UUID

from app.repositories.bookings import BookingRepository
from app.schemas.client import ClientBookingStatsOut, ClientWithLinkResponse


async def enrich_clients_with_booking_stats(
    booking_repo: BookingRepository,
    *,
    master_id: UUID,
    items: list[ClientWithLinkResponse],
) -> None:
    if not items:
        return
    client_ids = [item.client.id for item in items]
    no_shows = await booking_repo.no_show_counts_by_client_ids(
        master_id=master_id,
        client_ids=client_ids,
    )
    completed = await booking_repo.completed_counts_by_client_ids(
        master_id=master_id,
        client_ids=client_ids,
    )
    for item in items:
        cid = item.client.id
        item.booking_stats = ClientBookingStatsOut(
            no_show_count=no_shows.get(cid, 0),
            completed_count=completed.get(cid, 0),
        )
