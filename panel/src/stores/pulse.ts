import { defineStore } from 'pinia'
import { ref } from 'vue'

import { get } from '@/lib/api'

type Pulse = {
  orders: number
  revenue: number
  last: { name: string; base_grand_total: number; posting_time: string; is_return: 0 | 1 } | null
}

/**
 * The café's heartbeat: a cheap poll of today's running totals, so the panel
 * reacts the moment the barista rings something up at the till.
 */
export const usePulse = defineStore('pulse', () => {
  const orders = ref(0)
  const revenue = ref(0)
  /** bumped on every new order, so views can flash, refresh or beat */
  const beat = ref(0)
  const lastAmount = ref(0)

  let timer: number | undefined
  let started = false

  async function tick() {
    if (document.hidden) return
    const data = await get<Pulse>('cafe_app.api.dashboard.pulse').catch(() => null)
    if (!data) return
    const isNew = started && data.orders > orders.value
    orders.value = data.orders
    revenue.value = data.revenue
    if (isNew) {
      lastAmount.value = data.last?.base_grand_total ?? 0
      beat.value++
    }
    started = true
  }

  function start(every = 15_000) {
    if (timer) return
    void tick()
    timer = window.setInterval(tick, every)
    document.addEventListener('visibilitychange', tick)
  }

  function stop() {
    clearInterval(timer)
    timer = undefined
    document.removeEventListener('visibilitychange', tick)
  }

  return { orders, revenue, beat, lastAmount, start, stop, tick }
})
