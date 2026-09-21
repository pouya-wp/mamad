<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { ArrowLeft, Instagram, PackageCheck, Printer, ReceiptText, TriangleAlert } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import VChart from 'vue-echarts'

import AgentInsights from '@/components/agent/AgentInsights.vue'
import CupDonut from '@/components/charts/CupDonut.vue'
import DayReceipt from '@/components/DayReceipt.vue'
import HourClock from '@/components/charts/HourClock.vue'
import EmptyState from '@/components/EmptyState.vue'
import Marquee from '@/components/fx/Marquee.vue'
import RollingNumber from '@/components/fx/RollingNumber.vue'
import Panel from '@/components/Panel.vue'
import Segmented from '@/components/Segmented.vue'
import StatCard from '@/components/StatCard.vue'
import StoryCard from '@/components/StoryCard.vue'
import { get } from '@/lib/api'
import { CHART, tooltipBase } from '@/lib/charts'
import {
  delta,
  faNumber,
  jDate,
  jShortDate,
  paymentLabel,
  percent,
  shortTime,
  toman,
  tomanCompact,
  uom,
} from '@/lib/format'
import type { DashboardSummary } from '@/lib/types'
import { useLoader } from '@/lib/useLoader'
import { usePulse } from '@/stores/pulse'
import { useSession } from '@/stores/session'

type Period = 'today' | 'week' | 'month'

const session = useSession()
const period = ref<Period>('today')
const periods: { value: Period; label: string }[] = [
  { value: 'today', label: 'امروز' },
  { value: 'week', label: '۷ روز' },
  { value: 'month', label: '۳۰ روز' },
]

const { data, loading, load } = useLoader(() =>
  get<DashboardSummary>('cafe_app.api.dashboard.summary', { period: period.value }),
)
watch(period, load, { immediate: true })

// a sale at the till refreshes the numbers under the owner's eyes
const pulse = usePulse()
watch(() => pulse.beat, load)

const kpis = computed(() => data.value?.kpis)
const prev = computed(() => data.value?.previous)
const compareHint = computed(() => ({ today: 'نسبت به دیروز', week: 'نسبت به هفته قبل', month: 'نسبت به ماه قبل' })[period.value])
const margin = computed(() => (kpis.value?.revenue ? (kpis.value.gross_profit / kpis.value.revenue) * 100 : 0))

const greeting = computed(() => {
  const hour = new Date().getHours()
  const name = session.user?.full_name?.split(' ')[0] ?? ''
  return `${hour < 12 ? 'صبح بخیر' : hour < 18 ? 'عصر بخیر' : 'شب بخیر'}${name ? `، ${name}` : ''}`
})

const receiptOpen = ref(false)
const storyOpen = ref(false)
const receiptLabel = computed(() => ({ today: 'رسید امروز', week: 'رسید ۷ روز اخیر', month: 'رسید ۳۰ روز اخیر' })[period.value])

const heroLabel = computed(() => ({ today: 'فروش امروز تا این لحظه', week: 'فروش ۷ روز اخیر', month: 'فروش ۳۰ روز اخیر' })[period.value])
const revenueChange = computed(() => (kpis.value && prev.value ? delta(kpis.value.revenue, prev.value.revenue) : null))

const marquee = computed(() => {
  const word = { today: 'امروز', week: 'این هفته', month: 'این ماه' }[period.value]
  const top = data.value?.top_items[0]
  return [
    'ONE GOOD COFFEE',
    jDate(new Date()),
    kpis.value ? `${faNumber(kpis.value.orders)} سفارش ${word}` : 'O N E 1 C A F E',
    'ONE GOOD CAFE',
    top ? `محبوب‌ترین ${word}: ${top.item_name}` : 'YAZD · IRAN',
    'یزد · بلوار دانشگاه · کوچه فرساد',
  ]
})

const axisLabel = { color: CHART.axis, fontFamily: CHART.font, fontSize: 11 }

const trendOption = computed<EChartsOption>(() => {
  const trend = data.value?.trend ?? []
  const labels = trend.map((d) => jShortDate(d.date))

  // a glowing point that keeps travelling along the revenue curve
  const comet = {
    type: 'lines',
    coordinateSystem: 'cartesian2d',
    polyline: true,
    silent: true,
    data: [{ coords: trend.map((d, i) => [labels[i], d.revenue]) }],
    lineStyle: { width: 0, opacity: 0 },
    effect: { show: true, period: 7, trailLength: 0.3, symbol: 'circle', symbolSize: 7, color: '#ffe1d3', loop: true },
  }

  return {
    grid: { top: 12, right: 4, bottom: 4, left: 4, containLabel: true },
    tooltip: {
      ...tooltipBase,
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      formatter: (params: unknown) => {
        const i = (params as { dataIndex: number }[])[0].dataIndex
        const d = trend[i]
        return `<div style="font-family:${CHART.font}"><div style="color:#9d9da6">${jDate(d.date)}</div><b style="font-size:15px">${toman(d.revenue)} تومان</b><div style="color:#9d9da6">${faNumber(d.orders)} سفارش</div></div>`
      },
    },
    xAxis: {
      type: 'category',
      inverse: true,
      boundaryGap: false,
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { ...axisLabel, interval: 6 },
    },
    yAxis: {
      type: 'value',
      position: 'right',
      splitLine: { lineStyle: { color: CHART.grid } },
      axisLabel: { ...axisLabel, formatter: (v: number) => tomanCompact(v) },
    },
    series: [
      {
        type: 'line',
        smooth: 0.35,
        showSymbol: false,
        data: trend.map((d) => d.revenue),
        lineStyle: { width: 2.5, color: CHART.one, shadowBlur: 18, shadowColor: 'rgba(255,79,26,0.9)' },
        itemStyle: { color: CHART.one },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(255,79,26,0.34)' },
              { offset: 1, color: 'rgba(255,79,26,0)' },
            ],
          },
        },
      },
      comet,
    ] as unknown as EChartsOption['series'],
  }
})

const peakHours = computed(() =>
  [...(data.value?.hourly ?? [])]
    .filter((h) => h.orders > 0)
    .sort((a, b) => b.orders - a.orders)
    .slice(0, 4),
)
const peakMax = computed(() => Math.max(1, ...peakHours.value.map((h) => h.orders)))

const groupTotal = computed(() => (data.value?.by_group ?? []).reduce((sum, g) => sum + g.revenue, 0))
const paymentsTotal = computed(() => (data.value?.payments ?? []).reduce((sum, p) => sum + p.amount, 0))
const topMax = computed(() => Math.max(1, ...(data.value?.top_items ?? []).map((t) => t.qty)))

const orderType = (remarks: string | null) => remarks?.split(' | ')[0] || 'سفارش'
</script>

<template>
  <div class="stagger space-y-7">
    <!-- Editorial hero -->
    <section class="space-y-8">
      <Marquee :items="marquee" />
      <div class="flex flex-wrap items-end justify-between gap-6">
        <div class="min-w-0">
          <p class="mask-line text-base text-ink-300"><span>{{ greeting }}</span></p>
          <p class="mask-line mt-5 text-sm text-ink-400"><span class="[animation-delay:120ms]">{{ heroLabel }}</span></p>
          <div class="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-2">
            <RollingNumber
              v-if="kpis"
              class="text-[clamp(2.75rem,7.2vw,6.25rem)] leading-none font-extralight tracking-tight text-bone"
              :value="kpis.revenue"
              :format="toman"
            />
            <span v-else class="block h-20 w-80 animate-pulse rounded-2xl bg-white/[0.03]" />
            <span class="text-xl font-light text-ink-400">تومان</span>
            <span
              v-if="revenueChange !== null"
              class="rounded-full px-3 py-1 text-sm"
              :class="revenueChange >= 0 ? 'bg-mint-400/10 text-mint-400' : 'bg-rose-400/10 text-rose-400'"
            >
              {{ revenueChange >= 0 ? '▲' : '▼' }} {{ percent(Math.abs(revenueChange)) }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="data"
            data-ripple
            class="btn-ghost h-10"
            title="رسید این بازه را چاپ کن"
            @click="receiptOpen = true"
          >
            <Printer class="size-4" /> رسید
          </button>
          <button v-if="data" data-ripple class="btn-ghost h-10" title="استوری اینستاگرام بساز" @click="storyOpen = true">
            <Instagram class="size-4" /> استوری
          </button>
          <Segmented v-model="period" :options="periods" />
        </div>
      </div>
    </section>

    <DayReceipt v-if="data" v-model="receiptOpen" :data="data" :label="receiptLabel" />
    <StoryCard v-if="data" v-model="storyOpen" :data="data" :label="heroLabel" />

    <AgentInsights />

    <!-- KPIs -->
    <div class="grid gap-4 transition-opacity sm:grid-cols-2 xl:grid-cols-4" :class="loading && data ? 'opacity-60' : ''">
      <template v-if="kpis && prev">
        <StatCard
          accent
          label="فروش"
          :value="kpis.revenue"
          format="toman"
          unit="تومان"
          :change="delta(kpis.revenue, prev.revenue)"
          :hint="compareHint"
        />
        <StatCard label="سفارش‌ها" :value="kpis.orders" format="number" unit="سفارش" :change="delta(kpis.orders, prev.orders)" :hint="compareHint" />
        <StatCard
          label="میانگین هر فاکتور"
          :value="kpis.avg_ticket"
          format="toman"
          unit="تومان"
          :change="delta(kpis.avg_ticket, prev.avg_ticket)"
          :hint="compareHint"
        />
        <StatCard label="سود ناخالص" :value="kpis.gross_profit" format="toman" unit="تومان" :hint="`حاشیه سود ${percent(margin)}`" />
      </template>
      <div v-for="i in 4" v-else :key="i" class="card h-[150px] animate-pulse" />
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <Panel title="روند فروش" subtitle="۳۰ روز گذشته" class="xl:col-span-2">
        <!-- the height lives on the wrapper: vue-echarts forces height:100% on its own element -->
        <div class="h-64 sm:h-72 xl:h-80">
          <VChart v-if="data" :option="trendOption" autoresize />
          <div v-else class="h-full animate-pulse rounded-xl bg-white/[0.02]" />
        </div>
      </Panel>

      <Panel title="سهم دسته‌ها" subtitle="از فروش این بازه">
        <template v-if="data?.by_group.length">
          <CupDonut :groups="data.by_group" :palette="CHART.palette" />
          <ul class="mt-6 space-y-2.5">
            <li v-for="(g, i) in data.by_group" :key="g.item_group" class="flex items-center gap-3 text-sm">
              <span class="size-2.5 rounded-full" :style="{ background: CHART.palette[i % CHART.palette.length] }" />
              <span class="flex-1 text-ink-200">{{ g.item_group }}</span>
              <span class="num text-ink-400">{{ percent(groupTotal ? (g.revenue / groupTotal) * 100 : 0) }}</span>
            </li>
          </ul>
        </template>
        <EmptyState v-else :icon="ReceiptText" title="هنوز فروشی ثبت نشده" />
      </Panel>
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <Panel title="ساعات شلوغی" subtitle="ضربان کافه در ۲۴ ساعت" class="xl:col-span-2">
        <div v-if="data" class="flex flex-col items-center gap-8 md:flex-row md:justify-around">
          <HourClock :hours="data.hourly" />
          <div class="w-full max-w-xs">
            <p class="mb-4 text-xs text-ink-400">ساعت‌های اوج</p>
            <ul v-if="peakHours.length" class="space-y-4">
              <li v-for="(h, i) in peakHours" :key="h.hour">
                <div class="flex items-baseline justify-between text-sm">
                  <span :class="i === 0 ? 'text-bone' : 'text-ink-200'">ساعت {{ faNumber(h.hour) }} تا {{ faNumber(h.hour + 1) }}</span>
                  <span class="num text-ink-400">{{ faNumber(h.orders) }} سفارش</span>
                </div>
                <div class="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.05]">
                  <div
                    class="h-full rounded-full transition-all duration-1000"
                    :class="i === 0 ? 'bg-one-500 shadow-[0_0_10px_rgba(255,79,26,0.8)]' : 'bg-bone/35'"
                    :style="{ width: `${(h.orders / peakMax) * 100}%` }"
                  />
                </div>
              </li>
            </ul>
            <p v-else class="text-sm text-ink-500">هنوز سفارشی نیست.</p>
          </div>
        </div>
        <div v-else class="h-72 animate-pulse rounded-xl bg-white/[0.02]" />
      </Panel>

      <Panel title="پرفروش‌ترین‌ها">
        <ul v-if="data?.top_items.length" class="space-y-4">
          <li v-for="(item, i) in data.top_items" :key="item.item_code">
            <div class="flex items-center gap-3 text-sm">
              <span class="num w-5 text-center text-xs" :class="i === 0 ? 'font-bold text-one-500' : 'text-ink-500'">{{ faNumber(i + 1) }}</span>
              <span class="flex-1 truncate text-ink-100">{{ item.item_name }}</span>
              <span class="num text-ink-300">{{ faNumber(item.qty) }}</span>
            </div>
            <div class="mt-2 mr-8 h-1 overflow-hidden rounded-full bg-white/[0.05]">
              <div
                class="h-full rounded-full transition-all duration-700"
                :class="i === 0 ? 'bg-one-500 shadow-[0_0_10px_rgba(255,79,26,0.8)]' : 'bg-bone/40'"
                :style="{ width: `${(item.qty / topMax) * 100}%` }"
              />
            </div>
          </li>
        </ul>
        <EmptyState v-else :icon="ReceiptText" title="هنوز فروشی ثبت نشده" />
      </Panel>
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <Panel title="هشدار موجودی" subtitle="مواد زیر حد مجاز">
        <template #actions>
          <RouterLink to="/inventory" class="inline-flex items-center gap-1 text-xs text-ink-400 hover:text-one-400">انبار <ArrowLeft class="size-3.5" /></RouterLink>
        </template>
        <ul v-if="data?.low_stock.length" class="space-y-1">
          <li v-for="item in data.low_stock" :key="item.item_code" class="flex items-center gap-3 rounded-xl py-2.5">
            <div
              class="grid size-9 place-items-center rounded-xl"
              :class="item.actual_qty <= 0 ? 'bg-rose-400/10 text-rose-400' : 'bg-amber-300/10 text-amber-300'"
            >
              <TriangleAlert class="size-4" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm text-ink-100">{{ item.item_name }}</p>
              <p class="text-xs text-ink-400">حد مجاز {{ faNumber(item.safety_stock) }} {{ uom(item.stock_uom) }}</p>
            </div>
            <span class="num text-sm font-medium" :class="item.actual_qty <= 0 ? 'text-rose-400' : 'text-amber-300'">
              {{ faNumber(item.actual_qty) }} <span class="text-xs font-normal text-ink-400">{{ uom(item.stock_uom) }}</span>
            </span>
          </li>
        </ul>
        <EmptyState v-else :icon="PackageCheck" title="موجودی همه‌چیز کافیه" />
      </Panel>

      <Panel title="روش پرداخت">
        <div v-if="data?.payments.length" class="space-y-5">
          <div class="flex h-3 overflow-hidden rounded-full bg-white/[0.05]">
            <div
              v-for="(p, i) in data.payments"
              :key="p.mode_of_payment"
              class="h-full"
              :style="{ width: `${(p.amount / paymentsTotal) * 100}%`, background: CHART.palette[i % CHART.palette.length] }"
            />
          </div>
          <ul class="space-y-3">
            <li v-for="(p, i) in data.payments" :key="p.mode_of_payment" class="flex items-center gap-3 text-sm">
              <span class="size-2.5 rounded-full" :style="{ background: CHART.palette[i % CHART.palette.length] }" />
              <span class="flex-1 text-ink-200">{{ paymentLabel(p.mode_of_payment) }}</span>
              <span class="num text-ink-100">{{ toman(p.amount) }}</span>
              <span class="num w-12 text-left text-xs text-ink-400">{{ percent((p.amount / paymentsTotal) * 100) }}</span>
            </li>
          </ul>
        </div>
        <EmptyState v-else :icon="ReceiptText" title="پرداختی ثبت نشده" />
      </Panel>

      <Panel title="آخرین سفارش‌ها">
        <template #actions>
          <RouterLink to="/orders" class="inline-flex items-center gap-1 text-xs text-ink-400 hover:text-one-400">همه <ArrowLeft class="size-3.5" /></RouterLink>
        </template>
        <ul v-if="data?.recent_orders.length" class="divide-y divide-white/[0.04]">
          <li v-for="o in data.recent_orders" :key="o.name" class="flex items-center gap-3 py-3 text-sm">
            <div class="min-w-0 flex-1">
              <p class="text-ink-100">{{ orderType(o.remarks) }}</p>
              <p class="text-xs text-ink-400">{{ jShortDate(o.posting_date) }} · {{ shortTime(o.posting_time) }}</p>
            </div>
            <span class="num" :class="o.is_return ? 'text-rose-400' : 'text-bone'">{{ toman(o.base_grand_total) }}</span>
          </li>
        </ul>
        <EmptyState v-else :icon="ReceiptText" title="سفارشی نیست" />
      </Panel>
    </div>
  </div>
</template>
