/** Совпадает с `app/core/currency.py` (Currency). */
export const CURRENCIES = ['USD', 'EUR', 'BYN', 'RUB'] as const
export type CurrencyCode = (typeof CURRENCIES)[number]

export const DEFAULT_MASTER_CURRENCY: CurrencyCode = 'BYN'
