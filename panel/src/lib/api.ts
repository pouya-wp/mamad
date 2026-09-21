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
  if (typeof data.exception === 'string') return data.exception.split(': ').slice(1).join(': ') || data.exception
  return fallback
}

async function request<T>(method: 'GET' | 'POST', path: string, args?: Args): Promise<T> {
  if (DEMO) return demoRequest<T>(path.replace('/api/method/', ''), args)
  let url = path
  const init: RequestInit = {
    method,
    credentials: 'include',
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
export const get = <T>(method: string, args?: Args) => request<T>('GET', `/api/method/${method}`, args)

/** Whitelisted method that changes data (sends the CSRF token). */
export const post = <T>(method: string, args?: Args) => request<T>('POST', `/api/method/${method}`, args)
