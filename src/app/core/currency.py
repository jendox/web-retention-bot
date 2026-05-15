from __future__ import annotations

from enum import StrEnum


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    BYN = "BYN"
    RUB = "RUB"


DEFAULT_MASTER_CURRENCY = Currency.BYN
