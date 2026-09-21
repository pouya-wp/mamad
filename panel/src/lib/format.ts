import dayjs from 'dayjs'
import 'dayjs/locale/fa'
import jalaliday from 'jalaliday'

dayjs.extend(jalaliday)

const number = new Intl.NumberFormat('fa-IR')
const compact = new Intl.NumberFormat('fa-IR', { notation: 'compact', maximumFractionDigits: 1 })

/** Amounts are stored in Rial; the café thinks in Toman. */
export const RIAL_PER_TOMAN = 10

export const toToman = (rial: number | null | undefined) => Math.round((rial ?? 0) / RIAL_PER_TOMAN)
export const toRial = (toman: number | null | undefined) => Math.round((toman ?? 0) * RIAL_PER_TOMAN)

export const faNumber = (value: number | null | undefined, digits = 0) =>
  new Intl.NumberFormat('fa-IR', { maximumFractionDigits: digits }).format(value ?? 0)

export const toman = (rial: number | null | undefined) => number.format(toToman(rial))
export const tomanCompact = (rial: number | null | undefined) => compact.format(toToman(rial))

export const percent = (value: number | null | undefined, digits = 0) =>
  `${new Intl.NumberFormat('fa-IR', { maximumFractionDigits: digits }).format(value ?? 0)}٪`

export const faDigits = (text: string) => text.replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[+d])

// dayjs keeps Latin digits, and its short month names cut words ("شهریور" -> "شهر").
const jalali = (date: string | Date, pattern: string) => faDigits(dayjs(date).calendar('jalali').locale('fa').format(pattern))

export const jDate = (date: string | Date) => jalali(date, 'D MMMM YYYY')
export const jShortDate = (date: string | Date) => jalali(date, 'D MMMM')
export const jWeekday = (date: string | Date) => jalali(date, 'dddd')
export const jMonth = (date: string | Date) => jalali(date, 'MMMM')
export const jDateTime = (date: string | Date) => jalali(date, 'D MMMM · HH:mm')

/** Frappe returns posting_time as "HH:mm:ss(.ffffff)" */
export const shortTime = (time: string | null | undefined) => (time ? faDigits(time.slice(0, 5)) : '')

export const isoDate = (date: Date = new Date()) => dayjs(date).format('YYYY-MM-DD')

/** Change between two values as a percentage, or null when there is no baseline. */
export const delta = (current: number, previous: number) =>
  previous ? ((current - previous) / Math.abs(previous)) * 100 : null

export const UOM_LABELS: Record<string, string> = {
  Gram: 'گرم',
  Kg: 'کیلوگرم',
  Millilitre: 'میلی‌لیتر',
  Litre: 'لیتر',
  Nos: 'عدد',
  Unit: 'واحد',
}

export const uom = (value: string | null | undefined) => (value ? (UOM_LABELS[value] ?? value) : '')

export const PAYMENT_LABELS: Record<string, string> = {
  Cash: 'نقدی',
  'Credit Card': 'کارتخوان',
  'Wire Transfer': 'کارت به کارت',
}

export const paymentLabel = (mode: string) => PAYMENT_LABELS[mode] ?? mode
