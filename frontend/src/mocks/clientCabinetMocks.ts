import type { BookingClientListItem } from '../api/bookings'
import type { ClientMyMasterItem } from '../api/clients'

export type ClientMasterView = ClientMyMasterItem

export type ClientNotificationMock = {
  id: string
  title: string
  body: string
  created_at: string
  unread: boolean
}

/** Услуги для демо-записи в кабинете клиента (без бэкенда). */
export type MockBookableService = {
  id: string
  master_id: string
  name: string
  duration_min: number
  price: string
  currency: string
}

export type MockTelegramBotInfo = {
  username: string
  display_name: string
  /** Ссылка вида https://t.me/BotName?start=... для привязки аккаунта. */
  deep_link: string
}

function addMinutes(isoStart: string, minutes: number): string {
  const t = new Date(isoStart).getTime() + minutes * 60_000
  return new Date(t).toISOString()
}

const MOCK_TELEGRAM_BOT: MockTelegramBotInfo = {
  username: 'RetentionStudioDemoBot',
  display_name: 'Retention Studio · напоминания',
  deep_link: 'https://t.me/RetentionStudioDemoBot?start=demo-client-token',
}

/** Свободные слоты для мастера: простые окна на ближайшие дни, без пересечения с уже существующими записями. */
export function mockFreeSlotsForMaster(
  masterId: string,
  existing: { master_id: string; start_at: string; duration_min: number; status: string }[],
  now = new Date(),
  maxSlots = 14,
  slotDurationMin = 60,
): string[] {
  const booked = existing.filter((b) => b.master_id === masterId && b.status === 'SCHEDULED')

  function overlaps(iso: string, durationMin: number) {
    const start = new Date(iso).getTime()
    const end = start + durationMin * 60_000
    for (const b of booked) {
      const bs = new Date(b.start_at).getTime()
      const be = bs + b.duration_min * 60_000
      if (start < be && end > bs) {
        return true
      }
    }
    return false
  }

  const slots: string[] = []
  const y = now.getFullYear()
  const mo = now.getMonth()
  const d = now.getDate()

  for (let dayOffset = 1; dayOffset <= 21 && slots.length < maxSlots; dayOffset++) {
    for (const [hh, mm] of [
      [10, 0],
      [11, 30],
      [13, 0],
      [14, 30],
      [16, 0],
      [17, 30],
    ] as const) {
      const iso = new Date(y, mo, d + dayOffset, hh, mm, 0).toISOString()
      if (new Date(iso) <= now) {
        continue
      }
      if (!overlaps(iso, slotDurationMin)) {
        slots.push(iso)
      }
      if (slots.length >= maxSlots) {
        break
      }
    }
  }

  return slots
}

/** Даты подстраиваются от «сегодня», чтобы в демо всегда были и прошлые, и будущие слоты. */
export function buildClientCabinetMocks(now = new Date()) {
  const y = now.getFullYear()
  const m = now.getMonth()
  const d = now.getDate()

  const todayNoon = new Date(y, m, d, 12, 0, 0)
  const isoDay = (dayOffset: number, h: number, min: number) =>
    new Date(y, m, d + dayOffset, h, min, 0).toISOString()

  const upcoming1Start = isoDay(1, 14, 30)
  const upcoming2Start = isoDay(5, 11, 0)
  const laterStart = isoDay(12, 16, 0)
  const past1Start = isoDay(-10, 15, 0)
  const past2Start = isoDay(-4, 10, 30)
  const cancelledStart = isoDay(3, 12, 0)

  const bookings: BookingClientListItem[] = [
    {
      id: 'mock-b1',
      master_id: 'mock-master-1',
      client_id: 'mock-client-self',
      service_id: 'mock-svc-a',
      start_at: upcoming1Start,
      end_at: addMinutes(upcoming1Start, 90),
      duration_min: 90,
      price_snapshot: '120.00',
      currency_snapshot: 'BYN',
      status: 'SCHEDULED',
      master_display_name: 'Студия «Линия»',
      service_name: 'Окрашивание корней',
    },
    {
      id: 'mock-b2',
      master_id: 'mock-master-2',
      client_id: 'mock-client-self',
      service_id: 'mock-svc-b',
      start_at: upcoming2Start,
      end_at: addMinutes(upcoming2Start, 60),
      duration_min: 60,
      price_snapshot: '85.00',
      currency_snapshot: 'BYN',
      status: 'SCHEDULED',
      master_display_name: 'Ирина Лебедева',
      service_name: 'Маникюр с покрытием',
    },
    {
      id: 'mock-b3',
      master_id: 'mock-master-1',
      client_id: 'mock-client-self',
      service_id: 'mock-svc-c',
      start_at: laterStart,
      end_at: addMinutes(laterStart, 45),
      duration_min: 45,
      price_snapshot: '55.00',
      currency_snapshot: 'BYN',
      status: 'SCHEDULED',
      master_display_name: 'Студия «Линия»',
      service_name: 'Стрижка и укладка',
    },
    {
      id: 'mock-b4',
      master_id: 'mock-master-2',
      client_id: 'mock-client-self',
      service_id: 'mock-svc-d',
      start_at: past1Start,
      end_at: addMinutes(past1Start, 60),
      duration_min: 60,
      price_snapshot: '90.00',
      currency_snapshot: 'BYN',
      status: 'SCHEDULED',
      master_display_name: 'Ирина Лебедева',
      service_name: 'Наращивание коррекция',
    },
    {
      id: 'mock-b5',
      master_id: 'mock-master-1',
      client_id: 'mock-client-self',
      service_id: 'mock-svc-e',
      start_at: past2Start,
      end_at: addMinutes(past2Start, 30),
      duration_min: 30,
      price_snapshot: '40.00',
      currency_snapshot: 'BYN',
      status: 'SCHEDULED',
      master_display_name: 'Студия «Линия»',
      service_name: 'Тонирование уход',
    },
    {
      id: 'mock-b6',
      master_id: 'mock-master-1',
      client_id: 'mock-client-self',
      service_id: 'mock-svc-f',
      start_at: cancelledStart,
      end_at: addMinutes(cancelledStart, 60),
      duration_min: 60,
      price_snapshot: '95.00',
      currency_snapshot: 'BYN',
      status: 'CANCELLED',
      master_display_name: 'Студия «Линия»',
      service_name: 'Сложное окрашивание',
    },
  ]

  const masters: ClientMasterView[] = [
    {
      master_id: 'mock-master-1',
      display_name: 'Студия «Линия»',
      public_slug: 'liniya-studio',
      link_id: 'mock-link-1',
      invitation_status: 'LINKED',
      client_id: 'mock-client-self',
      client_display_name: 'Елена Волкова',
      alias: 'Лена',
      contact_email: 'studio.liniya@example.com',
    },
    {
      master_id: 'mock-master-2',
      display_name: 'Ирина Лебедева',
      public_slug: null,
      link_id: 'mock-link-2',
      invitation_status: 'LINKED',
      client_id: 'mock-client-self',
      client_display_name: 'Елена Волкова',
      alias: null,
      contact_email: 'irina.lebedeva@example.com',
    },
  ]

  const bookableServices: MockBookableService[] = [
    {
      id: 'mock-svc-book-a',
      master_id: 'mock-master-1',
      name: 'Консультация и подбор ухода',
      duration_min: 45,
      price: '45.00',
      currency: 'BYN',
    },
    {
      id: 'mock-svc-book-b',
      master_id: 'mock-master-1',
      name: 'Стрижка',
      duration_min: 60,
      price: '55.00',
      currency: 'BYN',
    },
    {
      id: 'mock-svc-book-c',
      master_id: 'mock-master-2',
      name: 'Маникюр классический',
      duration_min: 75,
      price: '65.00',
      currency: 'BYN',
    },
    {
      id: 'mock-svc-book-d',
      master_id: 'mock-master-2',
      name: 'Педикюр',
      duration_min: 90,
      price: '90.00',
      currency: 'BYN',
    },
  ]

  const notifications: ClientNotificationMock[] = [
    {
      id: 'n1',
      title: 'Напоминание о визите',
      body: `Завтра в ${new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(upcoming1Start))} — Окрашивание корней, студия «Линия».`,
      created_at: todayNoon.toISOString(),
      unread: true,
    },
    {
      id: 'n2',
      title: 'Приглашение принято',
      body: 'Вы успешно связали аккаунт с мастером Ирина Лебедева.',
      created_at: addMinutes(todayNoon.toISOString(), -360),
      unread: true,
    },
    {
      id: 'n3',
      title: 'Запись отменена',
      body: 'Мастер отменил запись «Сложное окрашивание». Выберите новое время.',
      created_at: addMinutes(todayNoon.toISOString(), -720),
      unread: false,
    },
  ]

  return {
    bookings,
    masters,
    notifications,
    bookableServices,
    telegramBot: MOCK_TELEGRAM_BOT,
  }
}

/** Real API by default; set VITE_CLIENT_DASHBOARD_USE_MOCKS=true for offline UI demo. */
export function clientDashboardUsesMocks() {
  return import.meta.env.VITE_CLIENT_DASHBOARD_USE_MOCKS === 'true'
}
