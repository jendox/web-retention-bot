import { describe, expect, it } from 'vitest'

import { cabinetFromPathname } from './appCabinet'

describe('cabinetFromPathname', () => {
  it('treats /master and nested paths as master cabinet', () => {
    expect(cabinetFromPathname('/master')).toBe('master')
    expect(cabinetFromPathname('/master/bookings')).toBe('master')
    expect(cabinetFromPathname('/master/notifications')).toBe('master')
    expect(cabinetFromPathname('/master/settings')).toBe('master')
  })

  it('treats /client and other app paths as client cabinet', () => {
    expect(cabinetFromPathname('/client')).toBe('client')
    expect(cabinetFromPathname('/client/visits')).toBe('client')
    expect(cabinetFromPathname('/client/notifications')).toBe('client')
    expect(cabinetFromPathname('/client/settings')).toBe('client')
  })
})
