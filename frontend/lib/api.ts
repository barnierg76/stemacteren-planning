/**
 * API Client for backend communication
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api'

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  }

  if (body) {
    config.body = JSON.stringify(body)
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }))
    throw new Error(error.detail?.message || error.message || 'Request failed')
  }

  return response.json()
}

// ============================================
// WORKSHOPS
// ============================================

export interface Workshop {
  id: string
  display_id: number
  display_code: string
  start_date: string
  end_date: string | null
  status: 'DRAFT' | 'PUBLISHED' | 'CONFIRMED' | 'CANCELLED' | 'COMPLETED'
  current_participants: number
  type: {
    id: string
    code: string
    name: string
  }
  location: {
    id: string
    code: string
    name: string
    address: string
  }
}

export const workshopsApi = {
  list: (params?: {
    status?: string
    location_id?: string
    type_id?: string
  }) => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.set('status', params.status)
    if (params?.location_id) searchParams.set('location_id', params.location_id)
    if (params?.type_id) searchParams.set('type_id', params.type_id)

    const query = searchParams.toString()
    return request<Workshop[]>(`/workshops${query ? `?${query}` : ''}`)
  },

  get: (id: string) => request<Workshop>(`/workshops/${id}`),

  create: (data: {
    type_id: string
    location_id: string
    start_date: string
    end_date?: string
    sessions?: Array<{
      session_number: number
      date: string
      start_time: string
      end_time: string
    }>
  }) => request<Workshop>('/workshops', { method: 'POST', body: data }),

  update: (id: string, data: Partial<Workshop>) =>
    request<Workshop>(`/workshops/${id}`, { method: 'PUT', body: data }),

  delete: (id: string) =>
    request<{ message: string }>(`/workshops/${id}`, { method: 'DELETE' }),

  validate: (data: {
    type_id: string
    location_id: string
    start_date: string
  }) => request<ValidationResult>('/workshops/validate', { method: 'POST', body: data }),
}

// ============================================
// TEAM
// ============================================

export interface Person {
  id: string
  name: string
  email: string | null
  phone: string | null
  type: 'INSTRUCTOR' | 'EXTERNAL_INSTRUCTOR' | 'TECHNICIAN'
  max_days_per_week: number | null
  preferred_location_id: string | null
  is_active: boolean
  notes: string | null
}

export const teamApi = {
  list: (params?: { type?: string; is_active?: boolean }) => {
    const searchParams = new URLSearchParams()
    if (params?.type) searchParams.set('type', params.type)
    if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active))

    const query = searchParams.toString()
    return request<Person[]>(`/team${query ? `?${query}` : ''}`)
  },

  get: (id: string) => request<Person>(`/team/${id}`),

  create: (data: Omit<Person, 'id'>) =>
    request<Person>('/team', { method: 'POST', body: data }),

  update: (id: string, data: Partial<Person>) =>
    request<Person>(`/team/${id}`, { method: 'PUT', body: data }),
}

// ============================================
// AVAILABILITY
// ============================================

export interface Availability {
  id: string
  person_id: string
  type: 'AVAILABLE' | 'UNAVAILABLE' | 'PREFERRED'
  start_date: string
  end_date: string
  reason: string | null
}

export const availabilityApi = {
  list: (params?: { person_id?: string; from_date?: string; to_date?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.person_id) searchParams.set('person_id', params.person_id)
    if (params?.from_date) searchParams.set('from_date', params.from_date)
    if (params?.to_date) searchParams.set('to_date', params.to_date)

    const query = searchParams.toString()
    return request<Availability[]>(`/availability${query ? `?${query}` : ''}`)
  },

  check: (person_id: string, date: string) =>
    request<{ available: boolean; reason: string | null }>(
      `/availability/check?person_id=${person_id}&check_date=${date}`
    ),

  create: (data: Omit<Availability, 'id'>) =>
    request<Availability>('/availability', { method: 'POST', body: data }),

  delete: (id: string) =>
    request<{ message: string }>(`/availability/${id}`, { method: 'DELETE' }),
}

// ============================================
// CONFIG
// ============================================

export interface Location {
  id: string
  code: string
  name: string
  address: string
  available_days: string[]
  is_active: boolean
}

export interface WorkshopType {
  id: string
  code: string
  name: string
  description: string | null
  duration_type: string
  session_count: number
  max_participants: number
  min_participants: number
  price: number
  requires_technician: boolean
  is_active: boolean
}

export const configApi = {
  locations: {
    list: () => request<Location[]>('/config/locations'),
    create: (data: Omit<Location, 'id'>) =>
      request<Location>('/config/locations', { method: 'POST', body: data }),
    update: (id: string, data: Partial<Location>) =>
      request<Location>(`/config/locations/${id}`, { method: 'PUT', body: data }),
  },

  workshopTypes: {
    list: () => request<WorkshopType[]>('/config/workshop-types'),
    create: (data: Omit<WorkshopType, 'id'>) =>
      request<WorkshopType>('/config/workshop-types', { method: 'POST', body: data }),
    update: (id: string, data: Partial<WorkshopType>) =>
      request<WorkshopType>(`/config/workshop-types/${id}`, { method: 'PUT', body: data }),
  },

  settings: {
    list: () => request<Setting[]>('/config/settings'),
    update: (key: string, value: unknown) =>
      request<Setting>(`/config/settings/${key}`, { method: 'PUT', body: { value } }),
  },
}

export interface Setting {
  id: string
  key: string
  value: unknown
  category: string
  label: string
}

// ============================================
// CHAT
// ============================================

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ChatResponse {
  session_id: string
  message: ChatMessage
  requires_confirmation: boolean
  pending_action?: {
    action_id: string
    tool: string
    description: string
  }
}

export const chatApi = {
  send: (content: string, session_id?: string) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: { content, session_id },
    }),

  history: (session_id: string) =>
    request<{ messages: ChatMessage[] }>(`/chat/history/${session_id}`),

  confirm: (session_id: string, action_id: string, confirmed: boolean) =>
    request<{ status: string }>(`/chat/confirm/${session_id}?action_id=${action_id}&confirmed=${confirmed}`, {
      method: 'POST',
    }),
}

// ============================================
// SCHEDULING
// ============================================

export interface ValidationResult {
  is_valid: boolean
  errors: Array<{ field: string; message: string; severity: string }>
  warnings: Array<{ field: string; message: string; severity: string }>
}

export const schedulingApi = {
  validate: (from_date: string, to_date: string) =>
    request<ValidationResult>(`/scheduling/validate?from_date=${from_date}&to_date=${to_date}`, {
      method: 'POST',
    }),

  suggestions: (params: {
    workshop_type_id?: string
    from_date: string
    to_date: string
    location_id?: string
  }) => {
    const searchParams = new URLSearchParams()
    if (params.workshop_type_id) searchParams.set('workshop_type_id', params.workshop_type_id)
    searchParams.set('from_date', params.from_date)
    searchParams.set('to_date', params.to_date)
    if (params.location_id) searchParams.set('location_id', params.location_id)

    return request<Array<{
      date: string
      day: string
      location: Location
      available_instructors: Array<{ id: string; name: string }>
      score: number
    }>>(`/scheduling/suggestions?${searchParams}`)
  },

  conflicts: (from_date: string, to_date: string) =>
    request<Array<{
      type: string
      date: string
      message: string
    }>>(`/scheduling/conflicts?from_date=${from_date}&to_date=${to_date}`),

  revenue: (from_date: string, to_date: string) =>
    request<{
      total_revenue: number
      by_workshop_type: Record<string, number>
      workshop_count: number
    }>(`/scheduling/revenue-forecast?from_date=${from_date}&to_date=${to_date}`),
}
