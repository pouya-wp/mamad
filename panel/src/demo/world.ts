import { DATASET } from '@/demo/dataset'

/**
 * A whole café, generated in the browser: six months of orders, purchases,
 * expenses and shifts built from the real menu and recipes. Seeded by the day,
 * so the numbers stay put while someone is looking at them but always land on
 * "today" — the demo never goes stale.
 */

export type DemoItem = { item_code: string; qty: number; rate: number }
export type DemoOrder = {
  name: string
  date: Date
  /** the day this order belongs to (YYYY-MM-DD), so lookups never scan the whole year */
  day: string
  items: DemoItem[]
  total: number
  discount: number
  grand_total: number
  cogs: number
  mode: string
  type: string
  table: string | null
  is_return: 0 | 1
  return_against: string | null
  returned: boolean
}
export type DemoPurchase = {
  name: string
  supplier: string
  date: Date
  items: DemoItem[]
  total: number
  is_paid: 0 | 1
  bill_no: string | null
}
export type DemoExpense = { name: string; date: Date; account: string; amount: number; note: string | null; mode: string }
export type DemoMove = {
  date: Date
  item_code: string
  qty: number
  after: number
  value: number
  voucher_type: string
  voucher_no: string
}
export type DemoShift = {
  name: string
  date: Date
  opening: Date
  closing: Date | null
  opening_cash: number
  closing_cash: number | null
  note: string | null
}

const DAYS = 182
const RIAL = 10

/** mulberry32 — same seed, same café. */
function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export const ymd = (date: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
export const hms = (date: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate())
const addDays = (date: Date, days: number) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)

// how busy each hour of a café day is (8:00 → 23:00)
const HOUR_WEIGHT: Record<number, number> = {
  8: 3, 9: 6, 10: 11, 11: 12, 12: 9, 13: 7, 14: 5, 15: 5, 16: 6, 17: 8, 18: 11, 19: 14, 20: 13, 21: 10, 22: 6, 23: 2,
}

const pick = <T>(random: () => number, rows: readonly T[]) => rows[Math.floor(random() * rows.length)]

/** A draw table built once: thousands of orders are generated from it. */
function table(weights: Record<number, number>) {
  const keys = Object.keys(weights).map(Number)
  const cumulative: number[] = []
  let running = 0
  for (const key of keys) cumulative.push((running += weights[key]))
  return { keys, cumulative, total: running }
}

type Table = ReturnType<typeof table>

function draw(random: () => number, from: Table) {
  const roll = random() * from.total
  for (let i = 0; i < from.cumulative.length; i++) if (roll <= from.cumulative[i]) return from.keys[i]
  return from.keys[0]
}

export const MENU = DATASET.menu.map((m) => ({ ...m, description: m.description as string | null }))
export const RECIPES = DATASET.recipes as Record<string, { item_code: string; item_name: string; qty: number; uom: string; rate: number }[]>

/** Selling a drink costs what its recipe costs — worked out once per item. */
const COSTS = new Map<string, number>()
function costOf(code: string) {
  let cost = COSTS.get(code)
  if (cost === undefined) {
    cost = (RECIPES[code] ?? []).reduce((sum, row) => sum + row.qty * row.rate, 0)
    COSTS.set(code, cost)
  }
  return cost
}

// the popular end of the menu sells more than the rest
const POPULARITY: Record<string, number> = {
  'لاته': 14, 'آمریکانو': 9, 'اسپرسو': 8, 'کاپوچینو': 9, 'موکا': 6, 'ماچا لاته': 5, 'هات چاکلت': 5, 'دمی V60': 3,
  'آیس لاته': 7, 'آیس آمریکانو': 6, 'آیس وانیل کافه': 4, 'لیموناد': 4, 'موهیتو': 4,
  'چیزکیک': 5, 'کیک شکلاتی': 5, 'کارامل ماکیاتو': 4,
  'املت': 3, 'صبحانه انگلیسی': 2, 'پیتزا مارگاریتا': 3, 'پیتزا پپرونی': 3,
}

export type World = ReturnType<typeof buildWorld>

export function buildWorld() {
  const now = new Date()
  const today = startOfDay(now)
  const random = rng(Math.floor(today.getTime() / 86400000))

  const menuWeights: Record<number, number> = {}
  MENU.forEach((item, index) => (menuWeights[index] = POPULARITY[item.item_code] ?? 3))
  const menuTable = table(menuWeights)
  const hourTable = table(HOUR_WEIGHT)

  const orders: DemoOrder[] = []
  const shifts: DemoShift[] = []
  let serial = 1

  for (let back = DAYS - 1; back >= 0; back--) {
    const day = addDays(today, -back)
    const weekday = day.getDay() // 4 = Thursday, 5 = Friday in JS
    const busy = weekday === 4 || weekday === 5 ? 1.35 : weekday === 6 ? 1.1 : 1
    const count = Math.round((26 + random() * 18) * busy)

    const dayOrders: DemoOrder[] = []
    for (let i = 0; i < count; i++) {
      const hour = draw(random, hourTable)
      const at = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour, Math.floor(random() * 60), Math.floor(random() * 60))
      if (at > now) continue // today stops at the current hour

      const lines = 1 + Math.floor(random() * 3)
      const items: DemoItem[] = []
      for (let l = 0; l < lines; l++) {
        const menuItem = MENU[draw(random, menuTable)]
        const existing = items.find((row) => row.item_code === menuItem.item_code)
        if (existing) existing.qty += 1
        else items.push({ item_code: menuItem.item_code, qty: 1 + (random() > 0.82 ? 1 : 0), rate: menuItem.rate })
      }

      const total = items.reduce((sum, row) => sum + row.qty * row.rate, 0)
      const discount = random() > 0.93 ? Math.round((total * 0.1) / 10000) * 10000 : 0
      dayOrders.push({
        name: `ACC-SINV-${day.getFullYear()}-${String(serial++).padStart(5, '0')}`,
        date: at,
        day: ymd(at),
        items,
        total,
        discount,
        grand_total: total - discount,
        cogs: items.reduce((sum, row) => sum + row.qty * costOf(row.item_code), 0),
        mode: random() > 0.32 ? 'کارتخوان' : 'نقدی',
        type: random() > 0.75 ? (random() > 0.5 ? 'بیرون‌بر' : 'پیک') : 'سالن',
        table: random() > 0.75 ? null : `میز ${1 + Math.floor(random() * 12)}`,
        is_return: 0,
        return_against: null,
        returned: false,
      })
    }

    dayOrders.sort((a, b) => a.date.getTime() - b.date.getTime())
    orders.push(...dayOrders)

    // one shift a day: opens with a float, closes counted, occasionally a rial or two out
    const cash = dayOrders.filter((o) => o.mode === 'نقدی').reduce((sum, o) => sum + o.grand_total, 0)
    const openingCash = 2_000_000
    const isToday = back === 0
    shifts.push({
      name: `SHIFT-${ymd(day)}`,
      date: day,
      opening: new Date(day.getFullYear(), day.getMonth(), day.getDate(), 8, 30),
      closing: isToday ? null : new Date(day.getFullYear(), day.getMonth(), day.getDate(), 23, 30),
      opening_cash: openingCash,
      closing_cash: isToday ? null : openingCash + cash + (random() > 0.75 ? Math.round((random() - 0.5) * 40) * 10000 : 0),
      note: null,
    })
  }

  // ---- purchases: roughly twice a week, from the real suppliers
  const purchases: DemoPurchase[] = []
  const ingredients = DATASET.ingredients
  for (let back = DAYS - 1; back >= 0; back -= 3 + Math.floor(random() * 2)) {
    const day = addDays(today, -back)
    const supplier = pick(random, DATASET.suppliers)
    const lines = 2 + Math.floor(random() * 3)
    const items: DemoItem[] = []
    for (let l = 0; l < lines; l++) {
      const ing = pick(random, ingredients)
      if (items.some((row) => row.item_code === ing.item_code)) continue
      const qty = Math.round((ing.safety_stock || 10) * (1.5 + random() * 2))
      items.push({ item_code: ing.item_code, qty, rate: ing.valuation_rate })
    }
    const total = items.reduce((sum, row) => sum + row.qty * row.rate, 0)
    purchases.push({
      name: `ACC-PINV-${day.getFullYear()}-${String(purchases.length + 1).padStart(5, '0')}`,
      supplier: supplier.name,
      date: day,
      items,
      total,
      is_paid: random() > 0.25 ? 1 : 0,
      bill_no: random() > 0.5 ? `${1000 + Math.floor(random() * 8999)}` : null,
    })
  }

  // ---- running costs
  const expenses: DemoExpense[] = []
  const monthly: [string, number, string][] = [
    ['اجاره - CO', 180_000_000, 'اجاره ماهانه'],
    ['حقوق و دستمزد - CO', 420_000_000, 'حقوق پرسنل'],
    ['آب، برق و گاز - CO', 38_000_000, 'قبض آب و برق و گاز'],
    ['اینترنت و تلفن - CO', 6_000_000, 'اینترنت کافه'],
  ]
  for (let back = DAYS - 1; back >= 0; back--) {
    const day = addDays(today, -back)
    if (day.getDate() === 5) {
      for (const [account, amount, note] of monthly) {
        expenses.push({
          name: `ACC-JV-${day.getFullYear()}-${String(expenses.length + 1).padStart(5, '0')}`,
          date: day,
          account,
          amount: Math.round(amount * (0.92 + random() * 0.16)),
          note,
          mode: 'کارتخوان',
        })
      }
    }
    if (random() > 0.88) {
      const [account, note] = pick(random, [
        ['ملزومات و شوینده - CO', 'خرید ملزومات'],
        ['تعمیرات و نگهداری - CO', 'سرویس دستگاه اسپرسو'],
        ['تبلیغات و بازاریابی - CO', 'تبلیغات اینستاگرام'],
        ['سایر هزینه‌ها - CO', 'هزینه متفرقه'],
      ] as const)
      expenses.push({
        name: `ACC-JV-${day.getFullYear()}-${String(expenses.length + 1).padStart(5, '0')}`,
        date: day,
        account,
        amount: Math.round((3 + random() * 25) * 1_000_000),
        note,
        mode: random() > 0.5 ? 'کارتخوان' : 'نقدی',
      })
    }
  }

  // ---- stock: the dataset's quantities are "now", so movements are written backwards from them
  const stock: Record<string, number> = {}
  for (const ing of ingredients) stock[ing.item_code] = ing.actual_qty

  const moves: DemoMove[] = []
  const recent = orders.slice(-60)
  for (const order of recent) {
    for (const line of order.items) {
      for (const row of RECIPES[line.item_code] ?? []) {
        moves.push({
          date: order.date,
          item_code: row.item_code,
          qty: -row.qty * line.qty,
          after: stock[row.item_code] ?? 0,
          value: -row.qty * line.qty * row.rate,
          voucher_type: 'Sales Invoice',
          voucher_no: order.name,
        })
      }
    }
  }
  for (const purchase of purchases.slice(-8)) {
    for (const line of purchase.items) {
      moves.push({
        date: purchase.date,
        item_code: line.item_code,
        qty: line.qty,
        after: stock[line.item_code] ?? 0,
        value: line.qty * line.rate,
        voucher_type: 'Purchase Invoice',
        voucher_no: purchase.name,
      })
    }
  }
  moves.sort((a, b) => b.date.getTime() - a.date.getTime())

  // one bucket per day: every range query walks days, never the whole year
  const byDay = new Map<string, DemoOrder[]>()
  for (const order of orders) {
    const bucket = byDay.get(order.day)
    if (bucket) bucket.push(order)
    else byDay.set(order.day, [order])
  }

  return {
    today,
    orders,
    byDay,
    purchases,
    expenses,
    shifts,
    moves,
    stock,
    ingredients: ingredients.map((row) => ({ ...row })),
    menu: MENU.map((row) => ({ ...row })),
    suppliers: DATASET.suppliers.map((row) => ({ ...row })),
    accounts: DATASET.accounts.map((row) => ({ ...row })),
    groups: DATASET.groups,
    serial,
    costOf,
    RIAL,
  }
}

export const world = buildWorld()

/** New orders (till, assistant, the demo's own traffic) join both the list and the day index. */
export function addOrder(order: DemoOrder) {
  world.orders.push(order)
  const bucket = world.byDay.get(order.day)
  if (bucket) bucket.push(order)
  else world.byDay.set(order.day, [order])
}

export const ordersOfDay = (date: Date) => world.byDay.get(ymd(date)) ?? []

/** Every order between two days, inclusive — by day bucket, so cost follows the range, not the history. */
export function ordersBetween(start: Date, end: Date) {
  const rows: DemoOrder[] = []
  for (let day = startOfDay(start); day <= end; day = addDays(day, 1)) {
    const bucket = world.byDay.get(ymd(day))
    if (bucket) rows.push(...bucket)
  }
  return rows
}
