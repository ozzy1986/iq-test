export type Fig = {
  shape: 'circle' | 'square' | 'triangle' | 'arrow'
  count: number
  fill: 'solid' | 'none' | 'light'
  rot: number
}
export type Option = { text?: string; fig?: Fig }
export type Question = {
  id: string
  prompt: string
  series?: string
  figure?: { cols: number; cells: (Fig | null)[] }
  options: Option[]
  category: string
}
export type Plan = { id: string; title: string; amount: number; currency: string; period_days: number }
export type Subscription = {
  plan: string
  status: 'active' | 'canceled'
  started_at: string
  current_period_end: string
  active: boolean
}
export type SessionState = {
  id: string
  status: 'started' | 'finished'
  questions: Question[]
  answers: Record<string, number>
  plan: Plan
  subscription: Subscription | null
  access: boolean
  email: string | null
  preview?: { duration_sec: number; answered: number; total: number; categories: string[] }
}
export type Result = {
  iq: number
  percentile: number
  level: { title: string; text: string }
  correct: number
  total: number
  duration_sec: number
  breakdown: { key: string; title: string; correct: number; total: number }[]
  insights: string[]
  review: {
    n: number
    category: string
    prompt: string
    series: string | null
    your: Option | null
    right: Option
    is_correct: boolean
    explain: string
  }[]
  subscription: Subscription
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

const TIMEOUT_MS = 15_000
const FALLBACK = 'Что-то пошло не так. Попробуйте ещё раз.'

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch('/api' + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
  } catch {
    throw new ApiError(0, 'Нет соединения. Проверьте интернет и попробуйте ещё раз.')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new ApiError(res.status, typeof data?.detail === 'string' ? data.detail : FALLBACK)
  }
  return res.status === 204 ? (undefined as T) : res.json()
}

let planRequest: Promise<{ plan: Plan; questions: number }> | undefined

export const api = {
  /** Тариф запрашивается один раз за визит: цена на всех экранах берётся с сервера. */
  plan: () => (planRequest ??= request<{ plan: Plan; questions: number }>('GET', '/plan').catch((e) => {
    planRequest = undefined
    throw e
  })),
  create: () => request<SessionState>('POST', '/sessions'),
  get: (id: string) => request<SessionState>('GET', `/sessions/${id}`),
  answer: (id: string, qid: string, option: number) =>
    request<unknown>('PUT', `/sessions/${id}/answers/${qid}`, { option }),
  finish: (id: string) => request<SessionState>('POST', `/sessions/${id}/finish`),
  checkout: (id: string, email: string) => request<SessionState>('POST', `/sessions/${id}/checkout`, { email }),
  cancel: (id: string) => request<SessionState>('POST', `/sessions/${id}/subscription/cancel`),
  result: (id: string) => request<Result>('GET', `/sessions/${id}/result`),
  track: (name: string, session_id?: string) => {
    request('POST', '/events', { name, session_id }).catch(() => {})
  },
}

const KEY = 'iq.session'
export const saved = {
  get: () => {
    try {
      return localStorage.getItem(KEY)
    } catch {
      return null
    }
  },
  set: (id: string | null) => {
    try {
      if (id) localStorage.setItem(KEY, id)
      else localStorage.removeItem(KEY)
    } catch {
      /* приватный режим — живём без сохранения */
    }
  },
}

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))
export const isEmail = (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(value.trim())
export const price = (kopecks: number) => `${Math.round(kopecks / 100)} ₽`
export const clock = (sec: number) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
export const date = (iso: string) =>
  new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).replace(/\s*г\.$/, '')
