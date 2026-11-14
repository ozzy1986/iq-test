export type Fig = {
  shape: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross' | 'arrow'
  count: number
  fill: 'solid' | 'none' | 'light'
  rot: number
  size?: number
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
export type Plan = {
  id: string
  title: string
  currency: string
  trial_amount: number
  trial_days: number
  amount: number
  period_days: number
}
export type Subscription = {
  trial: boolean
  plan: string
  status: 'active' | 'canceled'
  started_at: string
  current_period_end: string
  active: boolean
}
export type SessionState = {
  id: string
  profile_id: string
  status: 'started' | 'finished'
  questions: Question[]
  answers: Record<string, number>
  plan: Plan
  /** Что будет списано сейчас: пробный период для новых, полная цена для вернувшихся. */
  offer: { trial: boolean; amount: number; days: number }
  subscription: Subscription | null
  access: boolean
  email: string | null
  lead_email: string | null
  preview?: { duration_sec: number; answered: number; total: number; categories: string[] }
}
export type Result = {
  iq: number
  margin: number
  history: { id: string; finished_at: string; iq: number; current: boolean }[]
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
    figure: Question['figure'] | null
    difficulty: number
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

export type Offer = { plan: Plan; questions: number; minutes: number }
let planRequest: Promise<Offer> | undefined

export const api = {
  /** Тариф запрашивается один раз за визит: цена на всех экранах берётся с сервера. */
  plan: () => (planRequest ??= request<Offer>('GET', '/plan').catch((e) => {
    planRequest = undefined
    throw e
  })),
  /** Профиль связывает прохождения одного человека: на нём держатся подписка и история. */
  create: () => request<SessionState>('POST', '/sessions', { profile_id: saved.profile() }),
  get: (id: string) => request<SessionState>('GET', `/sessions/${id}`),
  answer: (id: string, qid: string, option: number) =>
    request<unknown>('PUT', `/sessions/${id}/answers/${qid}`, { option }),
  finish: (id: string) => request<SessionState>('POST', `/sessions/${id}/finish`),
  lead: (id: string, email: string) => request<SessionState>('POST', `/sessions/${id}/lead`, { email }),
  checkout: (id: string, email: string) => request<SessionState>('POST', `/sessions/${id}/checkout`, { email }),
  cancel: (id: string) => request<SessionState>('POST', `/sessions/${id}/subscription/cancel`),
  result: (id: string) => request<Result>('GET', `/sessions/${id}/result`),
  track: (name: string, session_id?: string) => {
    request('POST', '/events', { name, session_id }).catch(() => {})
  },
}

const KEY = 'iq.session'
const PROFILE_KEY = 'iq.profile'
const read = (key: string) => {
  try {
    return localStorage.getItem(key)
  } catch {
    return null // приватный режим — живём без сохранения
  }
}
const write = (key: string, value: string | null) => {
  try {
    if (value) localStorage.setItem(key, value)
    else localStorage.removeItem(key)
  } catch {
    /* см. выше */
  }
}
export const saved = {
  get: () => read(KEY),
  set: (id: string | null) => write(KEY, id),
  profile: () => read(PROFILE_KEY),
  /** Запоминаем и прохождение, и профиль: открытая на новом устройстве ссылка переносит подписку. */
  remember: (s: { id: string; profile_id: string }) => {
    write(KEY, s.id)
    write(PROFILE_KEY, s.profile_id)
  },
}

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))
export const isEmail = (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(value.trim())
export const price = (kopecks: number) => `${Math.round(kopecks / 100)} ₽`
export const clock = (sec: number) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
export const date = (iso: string) =>
  new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).replace(/\s*г\.$/, '')
