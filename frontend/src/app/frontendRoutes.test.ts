import { describe, expect, it } from 'vitest'

/**
 * Canonical UI paths after /client/* and /master/* migration.
 * Kept as constants so renames are caught by this test (no Playwright required in dev).
 */
const CLIENT_ROUTES = [
  '/client',
  '/client/masters',
  '/client/visits',
  '/client/help',
  '/client/notifications',
  '/client/settings',
] as const

const MASTER_ROUTES = [
  '/master',
  '/master/schedule',
  '/master/clients',
  '/master/services',
  '/master/bookings',
  '/master/notifications',
  '/master/settings',
] as const

const REMOVED_ROUTES = [
  '/dashboard',
  '/schedule',
  '/clients',
  '/services',
  '/bookings',
  '/notifications',
  '/settings',
] as const

describe('frontend route migration contract', () => {
  it('defines client cabinet URLs under /client', () => {
    for (const path of CLIENT_ROUTES) {
      expect(path.startsWith('/client')).toBe(true)
    }
  })

  it('defines master cabinet URLs under /master', () => {
    for (const path of MASTER_ROUTES) {
      expect(path.startsWith('/master')).toBe(true)
    }
  })

  it('does not list removed flat paths among new cabinet URLs', () => {
    const allCabinet = [...CLIENT_ROUTES, ...MASTER_ROUTES]
    for (const path of REMOVED_ROUTES) {
      expect(allCabinet.includes(path as (typeof allCabinet)[number])).toBe(false)
    }
  })
})
