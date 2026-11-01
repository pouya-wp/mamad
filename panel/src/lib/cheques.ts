import type { ChequeDirection, ChequeKind, ChequeStatus } from '@/lib/types'

export const DIRECTION_LABELS: Record<ChequeDirection, string> = { Received: 'دریافتی', Issued: 'پرداختی' }

export const KIND_LABELS: Record<ChequeKind, string> = { Regular: 'چک', Guarantee: 'چک ضمانت', Promissory: 'سفته' }

export const STATUS_LABELS: Record<ChequeStatus, string> = {
  Pending: 'در جریان',
  Cleared: 'وصول / پاس شد',
  Bounced: 'برگشتی',
  Transferred: 'خرج شد (واگذار)',
  Returned: 'عودت داده شد',
  Cancelled: 'باطل',
}

export const STATUS_TONES: Record<ChequeStatus, string> = {
  Pending: 'bg-amber-300/10 text-amber-300',
  Cleared: 'bg-mint-400/10 text-mint-400',
  Bounced: 'bg-rose-400/10 text-rose-400',
  Transferred: 'bg-sky-400/10 text-sky-300',
  Returned: 'bg-white/[0.06] text-ink-300',
  Cancelled: 'bg-white/[0.06] text-ink-400 line-through',
}

/** Received cheques bring money in, issued ones take it out. */
export const DIRECTION_TONES: Record<ChequeDirection, string> = { Received: 'text-mint-400', Issued: 'text-rose-400' }
