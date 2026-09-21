import { reactive } from 'vue'

import { ApiError } from './api'
import { sound } from './sound'

export type Toast = { id: number; kind: 'success' | 'error' | 'info'; message: string; timeout: number }

export const toasts = reactive<Toast[]>([])
let nextId = 1

/** `sfx: false` when the caller already plays a more specific sound (e.g. the register "ka-ching"). */
export function toast(message: string, kind: Toast['kind'] = 'success', timeout = 3800, sfx = true) {
  const id = nextId++
  toasts.push({ id, kind, message, timeout })
  if (sfx) sound[kind]()
  setTimeout(() => dismiss(id), timeout)
}

export function dismiss(id: number) {
  const index = toasts.findIndex((t) => t.id === id)
  if (index !== -1) toasts.splice(index, 1)
}

export function toastError(error: unknown) {
  toast(error instanceof ApiError || error instanceof Error ? error.message : 'خطای ناشناخته', 'error', 6000)
}
