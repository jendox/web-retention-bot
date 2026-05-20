from __future__ import annotations

from enum import StrEnum


class MessengerProvider(StrEnum):
    TELEGRAM = "telegram"

    @property
    def delivery_channel_value(self) -> str:
        return self.value
