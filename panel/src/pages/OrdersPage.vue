<script setup lang="ts">
import { LoaderCircle, ReceiptText, RotateCcw, Search } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import Segmented from '@/components/Segmented.vue'
import { get, post } from '@/lib/api'
import { faDigits, faNumber, isoDate, jDate, jShortDate, paymentLabel, shortTime, toman } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { OrderDetail, OrderRow } from '@/lib/types'

type Range = 'today' | 'week' | 'month' | 'all'
const PAGE = 40

const range = ref<Range>('today')
const ranges: { value: Range; label: string }[] = [
  { value: 'today', label: 'امروز' },
  { value: 'week', label: '۷ روز' },
  { value: 'month', label: '۳۰ روز' },
  { value: 'all', label: 'همه' },
]
const search = ref('')
const orders = ref<OrderRow[]>([])
const loading = ref(false)
const hasMore = ref(false)

const detail = ref<OrderDetail | null>(null)
const detailOpen = ref(false)
const returning = ref(false)

const dates = computed(() => {
  if (range.value === 'all') return {}
  const days = { today: 0, week: 6, month: 29 }[range.value]
  const from = new Date()
  from.setDate(from.getDate() - days)
  return { from_date: isoDate(from), to_date: isoDate() }
})

const totals = computed(() => {
  const sales = orders.value.filter((o) => !o.is_return)
  return {
    count: sales.length,
    revenue: orders.value.reduce((sum, o) => sum + o.base_grand_total, 0),
    returns: orders.value.filter((o) => o.is_return).length,
  }
})

async function load(append = false) {
  loading.value = true
  try {
    const rows = await get<OrderRow[]>('cafe_app.api.orders.list_orders', {
      ...dates.value,
      search: search.value || undefined,
      start: append ? orders.value.length : 0,
      limit: PAGE,
    })
    orders.value = append ? [...orders.value, ...rows] : rows
    hasMore.value = rows.length === PAGE
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}

let searchTimer: number
watch(range, () => load())
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => load(), 350)
})
load()

async function open(name: string) {
  detailOpen.value = true
  detail.value = null
  try {
    detail.value = await get<OrderDetail>('cafe_app.api.orders.get_order', { name })
  } catch (error) {
    toastError(error)
    detailOpen.value = false
  }
}

async function refund() {
  if (!detail.value || !confirm(`سفارش ${detail.value.name} کامل مرجوع شود؟ مواد اولیه به انبار برمی‌گردد.`)) return
  returning.value = true
  try {
    const name = await post<string>('cafe_app.api.orders.return_order', { name: detail.value.name })
    toast(`مرجوعی ${name} ثبت شد`)
    detailOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    returning.value = false
  }
}

const orderType = (remarks: string | null) => (remarks ? faDigits(remarks).split(' | ') : [])
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <Segmented v-model="range" :options="ranges" />
      <div class="relative min-w-56 flex-1 sm:max-w-xs">
        <Search class="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-ink-400" />
        <input v-model="search" class="field pr-10" placeholder="شماره فاکتور، میز یا یادداشت…" />
      </div>
      <div class="flex-1" />
      <div class="flex gap-6 text-sm">
        <div><span class="text-ink-400">سفارش </span><span class="num font-bold text-bone">{{ faNumber(totals.count) }}</span></div>
        <div><span class="text-ink-400">جمع </span><span class="num font-bold text-bone">{{ toman(totals.revenue) }}</span> <span class="text-xs text-ink-400">تومان</span></div>
        <div v-if="totals.returns"><span class="text-ink-400">مرجوعی </span><span class="num font-bold text-rose-400">{{ faNumber(totals.returns) }}</span></div>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[760px] text-sm">
          <thead>
            <tr class="border-b border-white/[0.06] text-right text-xs text-ink-400">
              <th class="px-6 py-4 font-medium">فاکتور</th>
              <th class="px-4 py-4 font-medium">زمان</th>
              <th class="px-4 py-4 font-medium">نوع</th>
              <th class="px-4 py-4 font-medium">اقلام</th>
              <th class="px-4 py-4 font-medium">پرداخت</th>
              <th class="px-4 py-4 font-medium">صندوقدار</th>
              <th class="px-6 py-4 text-left font-medium">مبلغ (تومان)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.04]">
            <tr v-for="o in orders" :key="o.name" class="cursor-pointer transition hover:bg-white/[0.02]" @click="open(o.name)">
              <td class="px-6 py-3.5">
                <span class="num font-medium text-ink-100" dir="ltr">{{ o.name }}</span>
                <span v-if="o.is_return" class="mr-2 rounded-full bg-rose-400/10 px-2 py-0.5 text-[11px] text-rose-400">مرجوعی</span>
              </td>
              <td class="px-4 py-3.5 text-ink-300">{{ jShortDate(o.posting_date) }} · {{ shortTime(o.posting_time) }}</td>
              <td class="px-4 py-3.5 text-ink-300">
                <span v-for="(part, i) in orderType(o.remarks).slice(0, 2)" :key="i" class="ml-1.5 inline-block rounded-md bg-white/[0.04] px-2 py-0.5 text-xs">{{ part }}</span>
              </td>
              <td class="num px-4 py-3.5 text-ink-300">{{ faNumber(o.items_count) }}</td>
              <td class="px-4 py-3.5 text-ink-300">{{ o.payment_modes.map(paymentLabel).join('، ') }}</td>
              <td class="px-4 py-3.5 text-ink-400">{{ o.owner_name }}</td>
              <td class="num px-6 py-3.5 text-left font-bold" :class="o.is_return ? 'text-rose-400' : 'text-bone'">{{ toman(o.base_grand_total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-if="!loading && !orders.length" :icon="ReceiptText" title="سفارشی در این بازه نیست" />
      <div v-if="loading" class="flex justify-center py-6"><LoaderCircle class="size-5 animate-spin text-ink-400" /></div>
      <div v-else-if="hasMore" class="border-t border-white/[0.05] p-4 text-center">
        <button class="btn-ghost" @click="load(true)">نمایش بیشتر</button>
      </div>
    </div>

    <Modal v-model="detailOpen" :title="detail ? `فاکتور ${detail.name}` : 'فاکتور'">
      <div v-if="!detail" class="flex justify-center py-10"><LoaderCircle class="size-6 animate-spin text-ink-400" /></div>
      <div v-else class="space-y-5">
        <div class="flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-400">
          <span>{{ jDate(detail.posting_date) }} · {{ shortTime(detail.posting_time) }}</span>
          <span>صندوقدار: {{ detail.owner_name }}</span>
          <span v-if="detail.remarks">{{ faDigits(detail.remarks) }}</span>
        </div>
        <ul class="divide-y divide-white/[0.05] rounded-2xl border border-white/[0.06] px-4">
          <li v-for="item in detail.items" :key="item.item_code" class="flex items-center gap-3 py-3 text-sm">
            <span class="num w-8 text-ink-400">{{ faNumber(item.qty) }}×</span>
            <span class="flex-1 text-ink-100">{{ item.item_name }}</span>
            <span class="num text-ink-200">{{ toman(item.amount) }}</span>
          </li>
        </ul>
        <div class="space-y-2 text-sm">
          <div v-if="detail.discount_amount" class="flex justify-between text-one-400">
            <span>تخفیف</span><span class="num">− {{ toman(detail.discount_amount) }}</span>
          </div>
          <div class="flex justify-between text-base">
            <span class="text-ink-200">جمع کل</span><span class="num font-black text-bone">{{ toman(detail.grand_total) }} تومان</span>
          </div>
          <div v-for="p in detail.payments" :key="p.mode_of_payment" class="flex justify-between text-ink-400">
            <span>{{ paymentLabel(p.mode_of_payment) }}</span><span class="num">{{ toman(p.amount) }}</span>
          </div>
        </div>
      </div>
      <template v-if="detail && !detail.is_return" #footer>
        <span v-if="detail.has_return" class="text-sm text-rose-400">این سفارش مرجوع شده</span>
        <button v-else class="btn-ghost text-rose-400" :disabled="returning" @click="refund">
          <RotateCcw class="size-4" /> مرجوع کامل
        </button>
      </template>
    </Modal>
  </div>
</template>
