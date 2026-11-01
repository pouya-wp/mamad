<script setup lang="ts">
import { LoaderCircle, ReceiptText, RotateCcw, Search } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import Segmented from '@/components/Segmented.vue'
import SourcePaymentStatus from '@/components/SourcePaymentStatus.vue'
import CreditCustomers from '@/components/CreditCustomers.vue'
import { paymentExplanation } from '@/lib/payment-explanation'
import { get, post } from '@/lib/api'
import { faDigits, faNumber, isoDate, jDate, jDateTime, jShortDate, paymentLabel, shortTime, toman } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { OrderDetail, OrderRow, OrderTotals } from '@/lib/types'
import { usePulse } from '@/stores/pulse'

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
const paymentState = ref('all')
const paymentStates = [
  { value: 'all', label: 'همهٔ وضعیت‌ها' }, { value: 'paid', label: 'پرداخت‌شده' },
  { value: 'unpaid', label: 'پرداخت‌نشده' }, { value: 'credit', label: 'نسیهٔ تسویه‌نشده' },
  { value: 'partial', label: 'پرداخت ناقص' }, { value: 'review', label: 'نیازمند تطبیق تسویه' },
  { value: 'unknown', label: 'نیازمند بررسی داده' }, { value: 'cancelled', label: 'لغوشده' },
]
const orders = ref<OrderRow[]>([])
const totals = ref<OrderTotals | null>(null)
const loading = ref(false)
const hasMore = ref(false)
let loadId = 0

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

async function load(append = false) {
  if (append && loading.value) return
  const id = ++loadId
  const filters = { ...dates.value, search: search.value || undefined, payment_state: paymentState.value }
  const start = append ? orders.value.length : 0
  if (!append) {
    orders.value = []
    totals.value = null
    hasMore.value = false
  }
  loading.value = true
  try {
    const [rows, summary] = await Promise.all([
      get<OrderRow[]>('cafe_app.api.orders.list_orders', { ...filters, start, limit: PAGE }),
      append ? Promise.resolve(null) : get<OrderTotals>('cafe_app.api.orders.order_totals', filters),
    ])
    if (id !== loadId) return
    orders.value = append ? [...orders.value, ...rows] : rows
    if (summary) totals.value = summary
    hasMore.value = rows.length === PAGE
  } catch (error) {
    if (id === loadId) toastError(error)
  } finally {
    if (id === loadId) loading.value = false
  }
}

let searchTimer: number
watch(range, () => load())
watch(paymentState, () => load())
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => load(), 350)
})
load()

const pulse = usePulse()
watch(() => [pulse.beat, pulse.paymentBeat], async () => {
  if (loading.value) return
  const id = loadId
  const filters = { ...dates.value, search: search.value || undefined, payment_state: paymentState.value }
  const detailName = detailOpen.value ? detail.value?.name : undefined
  try {
    const [rows, summary, updatedDetail] = await Promise.all([
      get<OrderRow[]>('cafe_app.api.orders.list_orders', { ...filters, start: 0, limit: Math.max(PAGE, orders.value.length) }),
      get<OrderTotals>('cafe_app.api.orders.order_totals', filters),
      detailName ? get<OrderDetail>('cafe_app.api.orders.get_order', { name: detailName }) : Promise.resolve(null),
    ])
    if (id !== loadId) return
    orders.value = rows
    totals.value = summary
    if (updatedDetail && detailOpen.value && detail.value?.name === detailName) detail.value = updatedDetail
  } catch {
    // Preserve the last checked source snapshot during a transient connection failure.
  }
})

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

const orderType = (remarks: string | null) => {
  if (!remarks) return []
  const parts = remarks.split(' | ').filter(part => !part.startsWith('[Sepand:') && part !== 'SepandYar' && part !== 'روش پرداخت در سپهریار نامشخص')
  return parts.length ? parts.map(faDigits) : ['سپهریار']
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <Segmented v-model="range" :options="ranges" />
      <div class="relative min-w-56 flex-1 sm:max-w-xs">
        <Search class="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-ink-400" />
        <input v-model="search" class="field pr-10" placeholder="فاکتور، نام یا کد مشتری، یادداشت…" />
      </div>
      <select v-model="paymentState" aria-label="وضعیت پرداخت" class="field w-auto">
        <option v-for="state in paymentStates" :key="state.value" :value="state.value">{{ state.label }}</option>
      </select>
      <div class="flex-1" />
      <div v-if="totals" class="flex gap-6 text-sm">
        <div><span class="text-ink-400">سفارش </span><span class="num font-bold text-bone">{{ faNumber(totals.count) }}</span></div>
        <div><span class="text-ink-400">جمع </span><span class="num font-bold text-bone">{{ toman(totals.revenue) }}</span> <span class="text-xs text-ink-400">تومان</span></div>
        <div v-if="totals.returns"><span class="text-ink-400">مرجوعی </span><span class="num font-bold text-rose-400">{{ faNumber(totals.returns) }}</span></div>
      </div>
    </div>

    <div v-if="totals?.source_payments" class="flex flex-wrap gap-x-6 gap-y-2 rounded-2xl border border-white/[0.06] px-5 py-3 text-sm text-ink-300">
      <span>پرداخت‌شده: <b class="num text-mint-400">{{ faNumber(totals.source_payments.paid_count || 0) }}</b></span>
      <span>نسیه: <b class="num text-amber-300">{{ faNumber(totals.source_payments.credit_count) }}</b></span>
      <span>پرداخت ناقص: <b class="num text-amber-300">{{ faNumber(totals.source_payments.partial_count) }}</b></span>
      <span>پرداخت‌نشده: <b class="num text-amber-300">{{ faNumber(totals.source_payments.unpaid_count) }}</b></span>
      <span>نیازمند تطبیق: <b class="num text-sky-300">{{ faNumber(totals.source_payments.review_count || 0) }}</b></span>
      <span>ماندهٔ مشخصِ فاکتورها: <b class="num text-bone">{{ toman(totals.source_payments.outstanding) }}</b> تومان</span>
      <p v-if="totals.source_payments.unallocated_count || totals.source_payments.unknown_count" class="w-full text-xs leading-6 text-ink-400">
        {{ faNumber(totals.source_payments.unallocated_count) }} فاکتور نیازمند تطبیق ثبت‌های حساب مشتری و {{ faNumber(totals.source_payments.unknown_count) }} فاکتور در انتظار دریافت یا بررسی داده است؛ ماندهٔ نامشخص آن‌ها صفر فرض نشده و در جمع بالا نمی‌آید. ماندهٔ کل حساب مشتری‌ها در جدول نسیه جداست.
      </p>
      <p v-if="totals.source_payments.stale_debt_count" class="w-full text-xs leading-6 text-amber-300">آخرین بررسی {{ faNumber(totals.source_payments.stale_debt_count) }} فاکتور تسویه‌نشده بیش از ۱۵ دقیقه قبل بوده است؛ وضعیت بر اساس آخرین دادهٔ دریافت‌شده است. روشن و متصل بودن برنامهٔ صندوق را بررسی کنید.</p>
    </div>

    <details class="rounded-2xl border border-white/[0.06] p-5 text-sm text-ink-300">
      <summary class="cursor-pointer font-bold text-bone">راهنمای وضعیت پرداخت و مبنای مبلغ‌ها</summary>
      <div class="mt-4 grid gap-3 text-xs leading-7 sm:grid-cols-2">
        <p><b class="text-mint-400">پرداخت‌شده:</b> دریافت برابر مبلغ فاکتور است، یا کل حساب تأییدشدهٔ مشتری تسویه شده؛ مبنای آن در جزئیات آمده است.</p>
        <p><b class="text-amber-300">پرداخت‌نشده:</b> دریافت ثبت‌شده‌ای روی فاکتور وجود ندارد.</p>
        <p><b class="text-amber-300">نسیه:</b> مبلغ به بدهی مشتری منتقل شده و تسویهٔ آن تأیید نشده است؛ نسیه دریافت نقدی نیست.</p>
        <p><b class="text-amber-300">پرداخت ناقص:</b> بخشی دریافت شده و ماندهٔ مشخصی هنوز قابل پرداخت است.</p>
        <p><b class="text-sky-300">نیازمند تطبیق:</b> دریافت یا بستانکاری روی حساب مشتری ثبت شده اما شمارهٔ فاکتور ندارد؛ بدهی حساب مشخص است، ماندهٔ آن فاکتور قابل انتساب نیست.</p>
        <p><b>نامشخص:</b> داده یا جمع مبالغ قابل تأیید نیست؛ به‌عنوان بدهکار یا تسویه‌شدهٔ قطعی نمایش داده نمی‌شود.</p>
        <p class="sm:col-span-2">همهٔ مبلغ‌ها تومان هستند. جمع فروش، مبلغ فاکتورهای بازه است و با پول دریافت‌شده برابر نیست. مبالغ روش‌های پرداخت، مربوط به همین فاکتورها هستند؛ تاریخ واریزهای حساب مشتری ممکن است خارج از بازه باشد. داده حدود هر ۵ دقیقه با روشن و متصل بودن برنامهٔ صندوق به‌روز می‌شود؛ زمان آخرین بررسی در جزئیات آمده است.</p>
      </div>
    </details>

    <section v-if="totals?.payment_methods?.length" class="rounded-2xl border border-white/[0.06] p-5">
      <h2 class="mb-3 text-sm font-bold text-bone">روش‌های پرداخت مربوط به فاکتورهای این بازه</h2>
      <div class="flex flex-wrap gap-3">
        <div v-for="method in totals.payment_methods" :key="`${method.method_id}-${method.mode_of_payment}`" class="rounded-xl bg-white/[0.03] px-4 py-3 text-sm">
          <span class="text-ink-300">{{ paymentLabel(method.mode_of_payment) }}</span>
          <span class="num mr-3 font-bold text-bone">{{ toman(method.amount) }} تومان</span>
          <p v-if="method.account_name" class="mt-1 text-xs text-ink-400">حساب در سپهریار: {{ method.account_name }}</p>
        </div>
      </div>
      <p class="mt-3 text-xs leading-6 text-ink-400">نام روش و حساب از سپهریار دریافت می‌شود. «تسویه حساب مشتری» روش دستگاه پوز نیست؛ تأیید تسویهٔ بدهی در حساب مشتری است. دستگاه بیرون‌بر فقط وقتی جدا گزارش می‌شود که در سپهریار روش جداگانه داشته باشد.</p>
    </section>

    <CreditCustomers v-if="totals?.credit_report?.customers.length" :report="totals.credit_report" @open="open" />

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[760px] text-sm">
          <thead>
            <tr class="border-b border-white/[0.06] text-right text-xs text-ink-400">
              <th class="px-6 py-4 font-medium">فاکتور</th>
              <th class="px-4 py-4 font-medium">زمان</th>
              <th class="px-4 py-4 font-medium">نوع</th>
              <th class="px-4 py-4 font-medium">اقلام</th>
              <th class="px-4 py-4 font-medium">مشتری</th>
              <th class="px-4 py-4 font-medium">روش پرداخت</th>
              <th class="px-4 py-4 font-medium">وضعیت پرداخت</th>
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
              <td class="px-4 py-3.5 text-ink-300">{{ o.source_payment?.customer?.name || '—' }}<span v-if="o.source_payment?.customer?.id" class="block text-xs text-ink-500">کد {{ faNumber(o.source_payment.customer.id) }}</span></td>
              <td class="px-4 py-3.5 text-ink-300">{{ o.payment_modes.map(paymentLabel).join('، ') }}</td>
              <td class="px-4 py-3.5">
                <SourcePaymentStatus v-if="o.source_payment" :payment="o.source_payment" />
                <span v-else class="text-ink-400">—</span>
              </td>
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
          <span v-if="detail.remarks">{{ orderType(detail.remarks).join(' · ') }}</span>
        </div>
        <div v-if="detail.source_payment" class="space-y-3 rounded-2xl border border-white/[0.06] p-4">
          <div class="flex flex-wrap justify-between gap-2 text-sm text-ink-200"><span>مشتری: <b>{{ detail.source_payment.customer?.name || 'در سپهریار مشخص نشده' }}</b></span><span v-if="detail.source_payment.customer?.id" class="num text-xs text-ink-400">کد مشتری {{ faNumber(detail.source_payment.customer.id) }}</span></div>
          <p v-if="detail.source_payment.source_factor" class="num text-xs text-ink-500">شمارهٔ اصلی فاکتور در سپهریار: {{ faNumber(detail.source_payment.source_factor) }}</p>
          <p v-if="detail.source_items_current" class="text-xs leading-6 text-ink-400">اقلام و مبلغ بر اساس آخرین وضعیت فاکتور در سپهریار نمایش داده می‌شوند.</p>
          <div class="flex items-center justify-between gap-3">
            <span class="text-sm text-ink-300">وضعیت پرداخت در سپهریار</span>
            <SourcePaymentStatus :payment="detail.source_payment" />
          </div>
          <p class="rounded-xl bg-white/[0.03] p-3 text-xs leading-7 text-ink-200">{{ paymentExplanation(detail.source_payment) }}</p>
          <div v-if="detail.source_payment.received !== null" class="flex justify-between text-sm text-ink-300">
            <span>{{ detail.source_payment.basis === 'Customer Account' ? 'مبلغ تسویه‌شدهٔ تأییدشده' : 'دریافتِ ثبت‌شده روی همین فاکتور' }}</span><span class="num">{{ toman(detail.source_payment.received) }} تومان</span>
          </div>
          <div v-if="detail.source_payment.outstanding !== null" class="flex justify-between text-sm" :class="detail.source_payment.outstanding > 0 ? 'text-amber-300' : 'text-ink-400'">
            <span>ماندهٔ پرداخت</span><span class="num">{{ toman(detail.source_payment.outstanding) }} تومان</span>
          </div>
          <div v-if="detail.source_payment.credit && detail.source_payment.basis !== 'Customer Account'" class="flex justify-between text-sm text-amber-300">
            <span>نسیهٔ ثبت‌شده (ماندهٔ فعلی نیست)</span><span class="num">{{ toman(detail.source_payment.credit) }} تومان</span>
          </div>
          <div v-if="detail.source_payment.account_balance !== null" class="flex justify-between text-xs text-ink-400">
            <span>ماندهٔ کل حساب مشتری · همهٔ فاکتورها</span><span class="num">{{ toman(detail.source_payment.account_balance) }} تومان</span>
          </div>
          <p v-if="detail.source_payment.total !== null && Math.abs(detail.source_payment.total - detail.grand_total) > 1" class="text-xs text-amber-300">
            مبلغ فعلی این فاکتور در سپهریار {{ toman(detail.source_payment.total) }} تومان است و با مبلغ ثبت‌شدهٔ اولیه تفاوت دارد.
          </p>
          <p v-if="detail.source_payment.checked_at" class="text-xs text-ink-500">آخرین دریافت از سپهریار: {{ jDateTime(detail.source_payment.checked_at) }}</p>
          <p v-if="detail.source_payment.is_stale" class="text-xs leading-6 text-amber-300">آخرین بررسی بیش از ۱۵ دقیقه قبل بوده است؛ این نمایش بر اساس آخرین دادهٔ دریافت‌شده است و تغییرات تازه هنوز تأیید نشده‌اند.</p>
          <p v-else class="text-xs text-ink-500">وضعیت پرداخت این فاکتور هنوز از سپهریار دریافت نشده است.</p>
          <div v-for="method in detail.source_payment.methods.filter(m => m.account_name)" :key="method.method_id || method.mode_of_payment" class="text-xs leading-6 text-ink-400">{{ method.mode_of_payment }} ← حساب «{{ method.account_name }}» در سپهریار</div>
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
          <div v-if="detail.source_extra_amount" class="flex justify-between text-ink-300">
            <span>سایر مبالغ فاکتور</span><span class="num">{{ toman(detail.source_extra_amount) }}</span>
          </div>
          <div class="flex justify-between text-base">
            <span class="text-ink-200">جمع کل</span><span class="num font-black text-bone">{{ toman(detail.grand_total) }} تومان</span>
          </div>
          <div v-for="p in detail.payments" :key="`${p.method_id}-${p.mode_of_payment}`" class="flex justify-between text-ink-400">
            <span>{{ paymentLabel(p.mode_of_payment) }}</span><span class="num">{{ toman(p.amount) }}</span>
          </div>
        </div>
      </div>
      <template v-if="detail && !detail.is_return && !detail.source_payment" #footer>
        <span v-if="detail.has_return" class="text-sm text-rose-400">این سفارش مرجوع شده</span>
        <button v-else class="btn-ghost text-rose-400" :disabled="returning" @click="refund">
          <RotateCcw class="size-4" /> مرجوع کامل
        </button>
      </template>
    </Modal>
  </div>
</template>
