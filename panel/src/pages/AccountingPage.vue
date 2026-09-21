<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { ArrowUp, Banknote, Landmark, LoaderCircle, Plus, Sparkles, Wallet } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import VChart from 'vue-echarts'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import Panel from '@/components/Panel.vue'
import Segmented from '@/components/Segmented.vue'
import StatCard from '@/components/StatCard.vue'
import { get, post } from '@/lib/api'
import { CHART, tooltipBase } from '@/lib/charts'
import { isoDate, jDate, jMonth, paymentLabel, percent, toman, tomanCompact, toRial } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { AccountingOverview, ExpenseRow } from '@/lib/types'
import { useLoader } from '@/lib/useLoader'
import { useAgent } from '@/stores/agent'

const agent = useAgent()
const sentence = ref('')
const examples = ['۴۵۰ میلیون اجاره این ماه رو دادم', '۸ میلیون قبض برق و گاز', '۳ میلیون تبلیغات اینستاگرام کارتی دادم']

function askAgent(text = sentence.value) {
  if (!text.trim()) return
  agent.ask(text)
  sentence.value = ''
}

type Period = 'week' | 'month' | 'year'
const period = ref<Period>('month')
const periods: { value: Period; label: string }[] = [
  { value: 'week', label: '۷ روز' },
  { value: 'month', label: '۳۰ روز' },
  { value: 'year', label: 'یک سال' },
]

const { data, loading, load } = useLoader(() => get<AccountingOverview>('cafe_app.api.accounting.overview', { period: period.value }))
watch(period, load, { immediate: true })

const expenses = ref<ExpenseRow[]>([])
const accounts = ref<{ name: string; account_name: string }[]>([])
const loadExpenses = async () => {
  try {
    ;[expenses.value, accounts.value] = await Promise.all([
      get<ExpenseRow[]>('cafe_app.api.accounting.list_expenses', { limit: 20 }),
      get<{ name: string; account_name: string }[]>('cafe_app.api.accounting.expense_accounts'),
    ])
  } catch (error) {
    toastError(error)
  }
}
onMounted(loadExpenses)
watch(
  () => agent.dataVersion,
  () => {
    load()
    loadExpenses()
  },
)

const netMargin = computed(() => (data.value?.income ? (data.value.net_profit / data.value.income) * 100 : 0))
const expenseMax = computed(() => Math.max(1, ...(data.value?.expenses_by_account ?? []).map((e) => e.amount)))

const axisLabel = { color: CHART.axis, fontFamily: CHART.font, fontSize: 11 }
const monthlyOption = computed<EChartsOption>(() => {
  const months = data.value?.monthly ?? []
  return {
    grid: { top: 30, right: 4, bottom: 4, left: 4, containLabel: true },
    legend: { top: 0, left: 0, textStyle: { color: CHART.axis, fontFamily: CHART.font }, itemWidth: 10, itemHeight: 10, icon: 'roundRect' },
    tooltip: {
      ...tooltipBase,
      trigger: 'axis',
      valueFormatter: (v) => `${toman(Number(v))} تومان`,
    },
    xAxis: { type: 'category', inverse: true, data: months.map((m) => jMonth(m.month)), axisLine: { show: false }, axisTick: { show: false }, axisLabel },
    yAxis: { type: 'value', position: 'right', splitLine: { lineStyle: { color: CHART.grid } }, axisLabel: { ...axisLabel, formatter: (v: number) => tomanCompact(v) } },
    series: [
      { name: 'درآمد', type: 'bar', barGap: '20%', barWidth: '26%', itemStyle: { color: CHART.bone, borderRadius: [5, 5, 1, 1] }, data: months.map((m) => m.income) },
      { name: 'هزینه', type: 'bar', barWidth: '26%', itemStyle: { color: 'rgba(157,157,166,0.35)', borderRadius: [5, 5, 1, 1] }, data: months.map((m) => m.expense) },
      { name: 'سود', type: 'line', smooth: true, symbolSize: 7, lineStyle: { color: CHART.one, width: 2.5 }, itemStyle: { color: CHART.one }, data: months.map((m) => m.profit) },
    ],
  }
})

// ---- Expense ----
const expenseOpen = ref(false)
const saving = ref(false)
const form = ref({ account: '', amountToman: null as number | null, mode: 'Cash', date: isoDate(), note: '' })

function openExpense() {
  form.value = { account: accounts.value[0]?.name ?? '', amountToman: null, mode: 'Cash', date: isoDate(), note: '' }
  expenseOpen.value = true
}

async function saveExpense() {
  saving.value = true
  try {
    await post('cafe_app.api.accounting.record_expense', {
      account: form.value.account,
      amount: toRial(form.value.amountToman ?? 0),
      mode_of_payment: form.value.mode,
      posting_date: form.value.date,
      note: form.value.note || null,
    })
    toast('هزینه ثبت شد')
    expenseOpen.value = false
    load()
    loadExpenses()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="stagger space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <Segmented v-model="period" :options="periods" />
      <div class="flex-1" />
      <button class="btn-ghost" @click="openExpense"><Plus class="size-4" /> ثبت دستی</button>
    </div>

    <!-- One-sentence bookkeeping -->
    <section class="card relative overflow-hidden border-one-500/25 bg-gradient-to-l from-one-500/[0.08] via-ink-850 to-ink-850 p-6 sm:p-7">
      <div class="flex items-center gap-3">
        <div class="grid size-9 place-items-center rounded-xl bg-one-500 text-white shadow-lg shadow-one-500/40"><Sparkles class="size-4" /></div>
        <div>
          <p class="font-bold text-bone">حسابداری با یک جمله</p>
          <p class="text-xs text-ink-400">فقط بنویس چه پولی دادی؛ دستیار سند رو آماده می‌کنه و با تأیید تو ثبت می‌کنه.</p>
        </div>
      </div>
      <form class="mt-5 flex items-center gap-2 rounded-2xl border border-white/10 bg-ink-900 p-2 focus-within:border-one-500/60" @submit.prevent="askAgent()">
        <input v-model="sentence" class="h-11 flex-1 bg-transparent px-3 text-[15px] text-ink-100 outline-none placeholder:text-ink-500" placeholder="مثلاً: ۱۲ میلیون حقوق باریستا دادم" />
        <button class="grid size-11 place-items-center rounded-xl bg-one-500 text-white hover:bg-one-400 disabled:opacity-30" :disabled="!sentence.trim()">
          <ArrowUp class="size-5" />
        </button>
      </form>
      <div class="mt-3 flex flex-wrap gap-2">
        <button v-for="e in examples" :key="e" class="rounded-full border border-white/10 px-3 py-1.5 text-xs text-ink-300 hover:border-one-500/40 hover:text-bone" @click="askAgent(e)">
          {{ e }}
        </button>
      </div>
    </section>

    <div class="grid gap-4 transition-opacity sm:grid-cols-2 xl:grid-cols-4" :class="loading && data ? 'opacity-60' : ''">
      <template v-if="data">
        <StatCard label="درآمد" :value="data.income" format="toman" unit="تومان" />
        <StatCard label="بهای تمام‌شده فروش" :value="data.cogs" format="toman" unit="تومان" :hint="`سود ناخالص ${toman(data.gross_profit)}`" />
        <StatCard label="هزینه‌های جاری" :value="data.operating_expenses" format="toman" unit="تومان" hint="اجاره، حقوق، قبوض…" />
        <StatCard accent label="سود خالص" :value="data.net_profit" format="toman" unit="تومان" :hint="`حاشیه سود خالص ${percent(netMargin)}`" />
      </template>
      <div v-for="i in 4" v-else :key="i" class="card h-[150px] animate-pulse" />
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <Panel title="صورت سود و زیان" subtitle="خلاصه بازه انتخاب‌شده">
        <div v-if="data" class="space-y-1 text-sm">
          <div class="flex justify-between rounded-xl px-3 py-2.5"><span class="text-ink-200">درآمد فروش</span><span class="num text-bone">{{ toman(data.income) }}</span></div>
          <div class="flex justify-between rounded-xl px-3 py-2.5"><span class="text-ink-400">− بهای تمام‌شده</span><span class="num text-ink-300">{{ toman(data.cogs) }}</span></div>
          <div class="flex justify-between rounded-xl bg-white/[0.03] px-3 py-2.5 font-medium"><span class="text-ink-100">سود ناخالص</span><span class="num text-bone">{{ toman(data.gross_profit) }}</span></div>
          <div class="flex justify-between rounded-xl px-3 py-2.5"><span class="text-ink-400">− هزینه‌های جاری</span><span class="num text-ink-300">{{ toman(data.operating_expenses) }}</span></div>
          <div
            class="mt-2 flex justify-between rounded-xl border px-3 py-3.5 text-base font-bold"
            :class="data.net_profit >= 0 ? 'border-one-500/30 bg-one-500/[0.08]' : 'border-rose-400/30 bg-rose-400/[0.06]'"
          >
            <span class="text-bone">سود خالص</span>
            <span class="num" :class="data.net_profit >= 0 ? 'text-one-400' : 'text-rose-400'">{{ toman(data.net_profit) }}</span>
          </div>
        </div>
      </Panel>

      <Panel title="درآمد و هزینه" subtitle="۶ ماه اخیر" class="xl:col-span-2">
        <!-- the height lives on the wrapper: vue-echarts forces height:100% on its own element -->
        <div class="h-64 sm:h-72 xl:h-80">
          <VChart v-if="data" :option="monthlyOption" autoresize />
          <div v-else class="h-full animate-pulse rounded-xl bg-white/[0.02]" />
        </div>
      </Panel>
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <Panel title="هزینه‌ها به تفکیک">
        <ul v-if="data?.expenses_by_account.length" class="space-y-4">
          <li v-for="e in data.expenses_by_account" :key="e.account">
            <div class="flex justify-between text-sm">
              <span class="text-ink-200">{{ e.account_name }}</span>
              <span class="num text-ink-100">{{ toman(e.amount) }}</span>
            </div>
            <div class="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.05]">
              <div class="h-full rounded-full bg-bone/50" :style="{ width: `${(e.amount / expenseMax) * 100}%` }" />
            </div>
          </li>
        </ul>
        <EmptyState v-else :icon="Wallet" title="هزینه‌ای در این بازه نیست" />
      </Panel>

      <Panel title="موجودی صندوق و بانک">
        <ul v-if="data?.balances.length" class="space-y-3">
          <li v-for="b in data.balances" :key="b.account" class="flex items-center gap-3 rounded-2xl bg-white/[0.03] p-4">
            <div class="grid size-10 place-items-center rounded-xl bg-white/[0.05] text-ink-200">
              <component :is="b.account_type === 'Cash' ? Banknote : Landmark" class="size-5" />
            </div>
            <span class="flex-1 text-sm text-ink-200">{{ b.account_name }}</span>
            <span class="num font-bold" :class="b.balance < 0 ? 'text-rose-400' : 'text-bone'">{{ toman(b.balance) }}</span>
          </li>
        </ul>
        <EmptyState v-else :icon="Landmark" title="حسابی نیست" />
      </Panel>

      <Panel title="آخرین هزینه‌ها">
        <ul v-if="expenses.length" class="max-h-96 divide-y divide-white/[0.04] overflow-y-auto pl-2">
          <li v-for="e in expenses" :key="e.name + e.account" class="flex items-center gap-3 py-3 text-sm">
            <div class="min-w-0 flex-1">
              <p class="truncate text-ink-100">{{ e.account_name }}</p>
              <p class="truncate text-xs text-ink-500">{{ jDate(e.posting_date) }}<template v-if="e.user_remark"> · {{ e.user_remark }}</template></p>
            </div>
            <span class="num text-ink-200">{{ toman(e.amount) }}</span>
          </li>
        </ul>
        <EmptyState v-else :icon="Wallet" title="هزینه‌ای ثبت نشده" />
      </Panel>
    </div>

    <Modal v-model="expenseOpen" title="ثبت هزینه">
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="block sm:col-span-2">
          <span class="mb-2 block text-sm text-ink-300">نوع هزینه</span>
          <select v-model="form.account" class="field">
            <option v-for="a in accounts" :key="a.name" :value="a.name">{{ a.account_name }}</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">مبلغ (تومان)</span>
          <input v-model.number="form.amountToman" type="number" min="0" class="field" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">پرداخت از</span>
          <select v-model="form.mode" class="field">
            <option value="Cash">{{ paymentLabel('Cash') }}</option>
            <option value="Credit Card">{{ paymentLabel('Credit Card') }}</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">تاریخ</span>
          <input v-model="form.date" type="date" class="field" dir="ltr" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">توضیح</span>
          <input v-model="form.note" class="field" />
        </label>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="expenseOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || !form.account || !form.amountToman" @click="saveExpense">
          <LoaderCircle v-if="saving" class="size-4 animate-spin" /> ثبت
        </button>
      </template>
    </Modal>
  </div>
</template>
