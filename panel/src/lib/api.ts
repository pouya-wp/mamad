import { DEMO, demoRequest } from '@/demo'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly excType?: string,
  ) {
    super(message)
  }

  get isAuthError() {
    return this.status === 401 || this.status === 403
  }
}

let csrfToken = ''

export function setCsrfToken(token: string) {
  csrfToken = token
}

type Args = Record<string, unknown>

/** Frappe packs user-facing errors into `_server_messages`: a JSON array of JSON-encoded objects. */
function extractMessage(data: Record<string, unknown>, fallback: string) {
  try {
    const messages = JSON.parse(String(data._server_messages ?? '[]')) as string[]
    const first = messages.map((m) => JSON.parse(m) as { message?: string }).find((m) => m.message)
    if (first?.message) return first.message.replace(/<[^>]+>/g, '')
  } catch {
    // not a Frappe message payload
  }
  if (typeof data.message === 'string' && data.message.trim()) {
    return data.message.replace(/<[^>]+>/g, '')
  }
  if (typeof data.exception === 'string') return data.exception.split(': ').slice(1).join(': ') || data.exception
  return fallback
}

async function request<T>(method: 'GET' | 'POST', path: string, args?: Args, timeoutMs?: number): Promise<T> {
  if (DEMO) return demoRequest<T>(path.replace('/api/method/', ''), args)
  let url = path
  const init: RequestInit = {
    method,
    credentials: 'include',
    ...(timeoutMs ? { signal: AbortSignal.timeout(timeoutMs) } : {}),
    headers: {
      Accept: 'application/json',
      ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}),
      ...(csrfToken ? { 'X-Frappe-CSRF-Token': csrfToken } : {}),
    },
  }

  if (method === 'GET' && args) {
    const query = new URLSearchParams()
    for (const [key, value] of Object.entries(args)) {
      if (value === undefined || value === null) continue
      query.set(key, typeof value === 'object' ? JSON.stringify(value) : String(value))
    }
    url += `?${query}`
  } else if (args) {
    init.body = JSON.stringify(args)
  }

  const response = await fetch(url, init)
  const data = (await response.json().catch(() => ({}))) as Record<string, unknown>

  if (!response.ok) {
    throw new ApiError(extractMessage(data, 'خطا در ارتباط با سرور'), response.status, data.exc_type as string)
  }
  return data.message as T
}

/** Read-only whitelisted method. */
export const get = <T>(method: string, args?: Args, timeoutMs?: number) => request<T>('GET', `/api/method/${method}`, args, timeoutMs)

/** Whitelisted method that changes data (sends the CSRF token). */
export const post = <T>(method: string, args?: Args) => request<T>('POST', `/api/method/${method}`, args)

/** Upload a short microphone recording without exposing the server's AI key. */
export async function postAudio<T>(method: string, audio: Blob): Promise<T> {
  if (DEMO) throw new ApiError('ویس فقط در نسخه متصل به سرور فعال است', 400)
  const body = new FormData()
  body.append('file', audio, audio.type.includes('mp4') ? 'voice.mp4' : audio.type.includes('ogg') ? 'voice.ogg' : 'voice.webm')
  const response = await fetch(`/api/method/${method}`, {
    method: 'POST', credentials: 'include', body,
    headers: { Accept: 'application/json', ...(csrfToken ? { 'X-Frappe-CSRF-Token': csrfToken } : {}) },
    signal: AbortSignal.timeout(70_000),
  })
  const data = (await response.json().catch(() => ({}))) as Record<string, unknown>
  if (!response.ok) throw new ApiError(extractMessage(data, 'ارسال ویس انجام نشد'), response.status, data.exc_type as string)
  return data.message as T
}

/** Send one assistant attachment without persisting it as a Frappe File. */
export async function postAgentFile<T>(message: string, history: { role: string; content: string }[], file: File): Promise<T> {
  if (DEMO) throw new ApiError('خواندن فایل فقط در نسخه متصل به سرور فعال است', 400)
  const body = new FormData()
  body.append('message', message)
  body.append('history', JSON.stringify(history))
  body.append('file', file, file.name)
  const response = await fetch('/api/method/cafe_app.api.agent.chat', {
    method: 'POST', credentials: 'include', body,
    headers: { Accept: 'application/json', ...(csrfToken ? { 'X-Frappe-CSRF-Token': csrfToken } : {}) },
    signal: AbortSignal.timeout(120_000),
  })
  const data = (await response.json().catch(() => ({}))) as Record<string, unknown>
  if (!response.ok) throw new ApiError(extractMessage(data, 'ارسال فایل انجام نشد'), response.status, data.exc_type as string)
  return data.message as T
}
