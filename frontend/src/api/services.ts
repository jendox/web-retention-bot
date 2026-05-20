/** Shared service types and re-exports from master API module. */

export type Service = {
  id: string
  master_id: string
  name: string
  description: string | null
  duration_min: number
  price: string
  currency: string
  is_active: boolean
  sort_order: number
}

export type PaginatedServices = {
  items: Service[]
  total: number
  page: number
  page_size: number
}

export type ServiceCreatePayload = {
  name: string
  description?: string | null
  duration_min: number
  price: string
  currency?: string | null
  is_active?: boolean
  sort_order?: number
}

export {
  servicesListApi,
  servicesCreateApi,
} from './master/services'

export { servicesUpdateApi as servicePatchApi, servicesDeleteApi as serviceDeleteApi } from './master/services'
