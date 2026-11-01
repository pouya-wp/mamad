<script setup lang="ts">
import dayjs from 'dayjs'
import {
  Cake,
  ChevronLeft,
  ChevronRight,
  FileSignature,
  HandCoins,
  LoaderCircle,
  Receipt,
  ShoppingBasket,
  Wallet,
} from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import AlertsStrip from '@/components/AlertsStrip.vue'
import { DIRECTION_LABELS, DIRECTION_TONES, KIND_LABELS, STATUS_LABELS, STATUS_TONES } from '@/lib/cheques'
import { faDigits, faNumber, isoDate, jDate, jWeekday, toman, tomanCompact } from '@/lib/format'
import { get } from '@/lib/api'
import { toastError } from '@/lib/toast'
import type { Alert, CalendarDay } from '@/lib/types'
import { useSession } from '@/stores/session'

const session = useSession()

const WEEKDAYS = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']

/** First day of the Shamsi month on screen. */
const cursor = ref(dayjs().calendar('jalali').startOf('month'))
const today = isoDate()
const selected = ref(today)

const days = ref<Record<string, CalendarDay>>({})
const alerts = ref<Alert[] | null>(null)
const loading = ref(false)

const title = computed(() => faDigits(cursor.value.locale('fa').format('MMMM YYYY')))

/** Whole weeks, Saturday first, covering the month. */
const grid = computed(() => {
  const first = cursor.value
  const last = first.endOf('month')
  const lead = (first.day() + 1) % 7
  const start = first.subtract(lead, 'day')
  const total = Math.ceil((lead + last.date()) / 7) * 7
  return Array.from({ length: total }, (_, i) => {
    const d = start.add(i, 'day')
    return {
      iso: d.calendar('gregory').format('YYYY-MM-DD'),
      day: d.date(),
      gregorianDay: d.calendar('gregory').date(),
      inMonth: d.month() === first.month(),
      friday: i % 7 === 6,
    }
  })
})

async function load() {
  loading.value = true
  try {
    const cells = grid.value
    days.value = await get<Record<string, CalendarDay>>(session.isBuyer ? 'cafe_app.api.purchasing.calendar_month' : 'cafe_app.api.daybook.month', {
      from_date: cells[0].iso,
      to_date: cells[cells.length - 1].iso,
    })
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  load()
  if (!session.isBuyer) alerts.value = await get<Alert[]>('cafe_app.api.daybook.alerts').catch(() => [])
})
watch(cursor, load)

function move(months: number) {
  cursor.value = cursor.value.add(months, 'month').startOf('month')
  // keep a day of the month on screen selected, preferably today
  const inMonth = grid.value.some((c) => c.inMonth && c.iso === today)
  selected.value = inMonth ? today : cursor.value.calendar('gregory').format('YYYY-MM-DD')
}
function goToday() {
  cursor.value = dayjs().calendar('jalali').startOf('month')
  selected.value = today
}

const detail = computed(() => days.value[selected.value])
const dayTotals = (d?: CalendarDay) => ({
  restaurant: d?.purchases.filter((p) => p.scope === 'Restaurant').reduce((s, p) => s + p.amount, 0) ?? 0,
  cafe: d?.purchases.filter((p) => p.scope === 'Cafe').reduce((s, p) => s + p.amount, 0) ?? 0,
  expenses: d?.expenses.reduce((s, e) => s + e.amount, 0) ?? 0,
})
const purchaseScopes = [
  { value: 'Restaurant', label: 'رستوران' },
  { value: 'Cafe', label: 'کافه' },
] as const
const EVENT_ICONS = { contract: FileSignature, payday: HandCoins, birthday: Cake }
const EVENT_TONES = { info: 'text-sky-300', warn: 'text-amber-300', ok: 'text-pink-300', danger: 'text-rose-400' }
</script>

<template>
  <div class="space-y-6">
    <AlertsStrip v-if="!session.isBuyer" :alerts="alerts" />

    <div class="grid gap-6 xl:grid-cols-[1fr_360px]">
      <section class="card p-4 sm:p-5">
        <div class="mb-4 flex items-center gap-2">
          <button class="grid size-9 place-items-center rounded-xl border border-white/10 text-ink-300 hover:text-bone" title="ماه قبل" @click="move(-1)">
            <ChevronRight class="size-4" />
          </button>
          <h2 class="min-w-32 text-center text-lg font-bold text-bone">{{ title }}</h2>
          <button class="grid size-9 place-items-center rounded-xl border border-white/10 text-ink-300 hover:text-bone" title="ماه بعد" @click="move(1)">
            <ChevronLeft class="size-4" />
          </button>
          <button class="btn-ghost h-9 px-3 text-xs" @click="goToday">امروز</button>
          <LoaderCircle v-if="loading" class="size-4 animate-spin text-ink-400" />
          <div class="flex-1" />
          <div class="hidden flex-wrap gap-3 text-[11px] text-ink-400 lg:flex">
            <span v-if="!session.isBuyer" class="flex items-center gap-1"><i class="size-2 rounded-full bg-rose-400" /> چک پرداختی</span>
            <span v-if="!session.isBuyer" class="flex items-center gap-1"><i class="size-2 rounded-full bg-amber-300" /> حقوق</span>
            <span class="flex items-center gap-1"><i class="size-2 rounded-full bg-sky-400" /> خرید رستوران</span>
            <span class="flex items-center gap-1"><i class="size-2 rounded-full bg-mint-400" /> خرید کافه</span>
          </div>
        </div>

        <div class="grid grid-cols-7 gap-1 text-center text-[11px] text-ink-500">
          <span v-for="w in WEEKDAYS" :key="w" class="pb-2"><span class="hidden sm:inline">{{ w }}</span><span class="sm:hidden">{{ w.charAt(0) }}</span></span>
        </div>
        <div class="grid grid-cols-7 gap-1">
          <button
            v-for="cell in grid"
            :key="cell.iso"
            class="relative flex min-h-16 flex-col rounded-xl border p-1.5 text-right transition sm:min-h-24 sm:p-2"
            :class="[
              cell.iso === selected ? 'border-one-500/70 bg-one-500/[0.08]' : 'border-white/[0.05] hover:border-white/15',
              cell.inMonth ? '' : 'opacity-35',
            ]"
            @click="selected = cell.iso"
          >
            <div class="flex items-start justify-between">
              <span
                class="grid size-6 place-items-center rounded-full text-sm font-bold"
                :class="cell.iso === today ? 'bg-one-500 text-white' : cell.friday ? 'text-rose-300' : 'text-ink-100'"
              >{{ faNumber(cell.day) }}</span>
              <span class="hidden text-[10px] text-ink-600 sm:inline">{{ faNumber(cell.gregorianDay) }}</span>
            </div>
            <template v-if="days[cell.iso]">
              <span v-if="!session.isBuyer && days[cell.iso].sales" class="num mt-auto hidden truncate text-[11px] text-ink-300 sm:block">
                {{ tomanCompact(days[cell.iso].sales!.revenue) }}
              </span>
              <div class="mt-auto flex flex-wrap gap-0.5 pt-1 sm:mt-1">
                <template v-if="!session.isBuyer">
                  <i v-for="c in days[cell.iso].cheques.filter((c) => c.direction === 'Issued')" :key="c.name" class="size-1.5 rounded-full bg-rose-400" />
                  <i v-for="(e, i) in days[cell.iso].events" :key="`e${i}`" class="size-1.5 rounded-full" :class="e.type === 'payday' ? 'bg-amber-300' : e.type === 'birthday' ? 'bg-pink-300' : 'bg-sky-400'" />
                </template>
                <i v-if="days[cell.iso].purchases.some((p) => p.scope === 'Restaurant')" class="size-1.5 rounded-full bg-sky-400/60" />
                <i v-if="days[cell.iso].purchases.some((p) => p.scope === 'Cafe')" class="size-1.5 rounded-full bg-mint-400/60" />
              </div>
            </template>
          </button>
        </div>
      </section>

      <!-- the selected day -->
      <aside class="card space-y-5 p-5 xl:sticky xl:top-24 xl:self-start">
        <div>
          <p class="text-xs text-ink-400">{{ jWeekday(selected) }}</p>
          <p class="text-xl font-black text-bone">{{ jDate(selected) }}</p>
        </div>

        <template v-if="detail">
          <div class="grid grid-cols-2 gap-2 text-center">
            <RouterLink v-if="!session.isBuyer" to="/orders" class="rounded-2xl bg-white/[0.03] p-3 hover:bg-white/[0.05]">
              <p class="text-[11px] text-ink-400">فروش</p>
              <p class="num mt-1 text-sm font-bold text-bone">{{ detail.sales ? tomanCompact(detail.sales.revenue) : '—' }}</p>
              <p v-if="detail.sales" class="text-[10px] text-ink-500">{{ faNumber(detail.sales.orders) }} سفارش</p>
            </RouterLink>
            <RouterLink to="/purchases" class="rounded-2xl bg-white/[0.03] p-3 hover:bg-white/[0.05]">
              <p class="text-[11px] text-ink-400">خرید رستوران</p>
              <p class="num mt-1 text-sm font-bold text-bone">{{ dayTotals(detail).restaurant ? tomanCompact(dayTotals(detail).restaurant) : '—' }}</p>
            </RouterLink>
            <RouterLink to="/purchases" class="rounded-2xl bg-white/[0.03] p-3 hover:bg-white/[0.05]">
              <p class="text-[11px] text-ink-400">خرید کافه</p>
              <p class="num mt-1 text-sm font-bold text-bone">{{ dayTotals(detail).cafe ? tomanCompact(dayTotals(detail).cafe) : '—' }}</p>
            </RouterLink>
            <RouterLink v-if="!session.isBuyer" to="/accounting" class="rounded-2xl bg-white/[0.03] p-3 hover:bg-white/[0.05]">
              <p class="text-[11px] text-ink-400">هزینه</p>
              <p class="num mt-1 text-sm font-bold text-bone">{{ dayTotals(detail).expenses ? tomanCompact(dayTotals(detail).expenses) : '—' }}</p>
            </RouterLink>
          </div>

          <div v-if="!session.isBuyer && detail.cheques.some((c) => c.direction === 'Issued')" class="space-y-2">
            <p class="flex items-center gap-2 text-sm font-bold text-bone"><Receipt class="size-4 text-one-500" /> چک‌های سررسید</p>
            <RouterLink v-for="c in detail.cheques.filter((c) => c.direction === 'Issued')" :key="c.name" to="/cheques" class="flex items-center gap-3 rounded-xl bg-white/[0.03] px-3 py-2.5 text-sm hover:bg-white/[0.05]">
              <div class="min-w-0 flex-1">
                <p class="truncate text-ink-100">{{ KIND_LABELS[c.kind] }} {{ DIRECTION_LABELS[c.direction] }} · {{ c.party }}</p>
                <span class="mt-1 inline-block rounded-full px-2 py-0.5 text-[10px]" :class="STATUS_TONES[c.status]">{{ STATUS_LABELS[c.status] }}</span>
              </div>
              <span class="num font-bold" :class="DIRECTION_TONES[c.direction]">{{ toman(c.amount) }}</span>
            </RouterLink>
          </div>

          <div v-if="!session.isBuyer && detail.events.length" class="space-y-2">
            <p class="flex items-center gap-2 text-sm font-bold text-bone"><FileSignature class="size-4 text-one-500" /> پرسنل</p>
            <RouterLink v-for="(e, i) in detail.events" :key="i" to="/staff" class="flex items-center gap-3 rounded-xl bg-white/[0.03] px-3 py-2.5 text-sm hover:bg-white/[0.05]">
              <component :is="EVENT_ICONS[e.type]" class="size-4 shrink-0" :class="EVENT_TONES[e.tone]" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-ink-100">{{ e.title }}</p>
                <p v-if="e.hint" class="text-[11px] text-ink-500">{{ e.hint }}</p>
              </div>
              <span v-if="e.amount" class="num text-ink-200">{{ toman(e.amount) }}</span>
            </RouterLink>
          </div>

          <div v-if="detail.purchases.length" class="space-y-3">
            <div v-for="scope in purchaseScopes" :key="scope.value" class="space-y-2">
              <p class="flex items-center gap-2 text-sm font-bold text-bone"><ShoppingBasket class="size-4 text-one-500" /> خرید {{ scope.label }}</p>
              <div v-for="p in detail.purchases.filter((p) => p.scope === scope.value)" :key="p.name" class="flex items-center gap-3 rounded-xl bg-white/[0.03] px-3 py-2.5 text-sm">
                <span class="min-w-0 flex-1 truncate text-ink-100">{{ p.supplier || 'خرید' }}</span>
                <span class="num text-ink-200">{{ toman(p.amount) }}</span>
              </div>
              <p v-if="!detail.purchases.some((p) => p.scope === scope.value)" class="text-xs text-ink-500">خریدی ثبت نشده</p>
            </div>
          </div>

          <div v-if="!session.isBuyer && detail.expenses.length" class="space-y-2">
            <p class="flex items-center gap-2 text-sm font-bold text-bone"><Wallet class="size-4 text-one-500" /> هزینه‌ها</p>
            <div v-for="e in detail.expenses" :key="e.name" class="flex items-center gap-3 rounded-xl bg-white/[0.03] px-3 py-2.5 text-sm">
              <span class="min-w-0 flex-1 truncate text-ink-100">{{ e.title }} <span v-if="e.note" class="text-xs text-ink-500">· {{ e.note }}</span></span>
              <span class="num text-ink-200">{{ toman(e.amount) }}</span>
            </div>
          </div>

          <p
            v-if="!detail.sales && !detail.cheques.length && !detail.events.length && !detail.purchases.length && !detail.expenses.length"
            class="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-center text-sm text-ink-400"
          >
            برای این روز چیزی ثبت نشده
          </p>
        </template>
        <div v-else class="h-32 animate-pulse rounded-2xl bg-white/[0.03]" />
      </aside>
    </div>
  </div>
</template>
