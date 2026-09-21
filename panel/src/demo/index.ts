import { demoDispatch, sell } from '@/demo/api'
import { type DemoOrder, world } from '@/demo/world'

/**
 * Demo mode: the panel runs with no backend at all, on a café generated in the
 * browser (see world.ts). Turned on by VITE_DEMO=1 — that is what the Vercel
 * build uses — so the same code still talks to ERPNext everywhere else.
 */
export const DEMO = import.meta.env.VITE_DEMO === '1'

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/** Answers like a server would: a little latency, so the panel's loaders are real. */
export async function demoRequest<T>(method: string, args?: Record<string, unknown>): Promise<T> {
  await wait(90 + Math.random() * 220)
  return demoDispatch(method, args ?? {}) as T
}

const POPULAR = ['لاته', 'آمریکانو', 'کاپوچینو', 'آیس لاته', 'اسپرسو', 'موکا', 'چیزکیک', 'کیک شکلاتی', 'ماچا لاته', 'هات چاکلت']

/** Every so often a barista rings something up, so the live pulse has a heartbeat. */
export function startDemoTraffic() {
  const ring = () => {
    const hour = new Date().getHours()
    if (hour >= 8 && hour < 24) {
      const lines = 1 + Math.floor(Math.random() * 2)
      const items = [] as DemoOrder['items']
      for (let i = 0; i < lines; i++) {
        const code = POPULAR[Math.floor(Math.random() * POPULAR.length)]
        const menuItem = world.menu.find((m) => m.item_code === code)
        if (!menuItem) continue
        const existing = items.find((row) => row.item_code === code)
        if (existing) existing.qty += 1
        else items.push({ item_code: code, qty: 1, rate: menuItem.rate })
      }
      const total = items.reduce((sum, row) => sum + row.qty * row.rate, 0)
      const order: DemoOrder = {
        name: `ACC-SINV-${new Date().getFullYear()}-${String(world.serial++).padStart(5, '0')}`,
        date: new Date(),
        items,
        total,
        discount: 0,
        grand_total: total,
        cogs: items.reduce((sum, row) => sum + row.qty * world.costOf(row.item_code), 0),
        mode: Math.random() > 0.35 ? 'کارتخوان' : 'نقدی',
        type: Math.random() > 0.8 ? 'بیرون‌بر' : 'سالن',
        table: `میز ${1 + Math.floor(Math.random() * 12)}`,
        is_return: 0,
        return_against: null,
        returned: false,
      }
      world.orders.push(order)
      sell(order)
    }
    window.setTimeout(ring, 35_000 + Math.random() * 40_000)
  }
  window.setTimeout(ring, 20_000)
}
