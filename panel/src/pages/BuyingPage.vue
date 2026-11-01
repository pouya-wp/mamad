<script setup lang="ts">
import { Bot, LoaderCircle, Pencil, Plus, ShoppingBasket, Sparkles, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import Segmented from '@/components/Segmented.vue'
import { get, post } from '@/lib/api'
import { faNumber, isoDate, jDate, toman, toRial, toToman } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { BuyList, BuyPayment, BuyPurchase, BuyScope } from '@/lib/types'
import { useAgent } from '@/stores/agent'
import { useSession } from '@/stores/session'

const session = useSession()
const agent = useAgent()

const SCOPES: Record<BuyScope, string> = { Restaurant: 'رستوران', Cafe: 'کافه' }
const PAYMENTS: Record<BuyPayment, string> = { Card: 'کارت', Cash: 'نقدی', Transfer: 'کارت به کارت', Credit: 'نسیه' }
const UNITS = ['کیلو', 'گرم', 'لیتر', 'میلی‌لیتر', 'عدد', 'بسته', 'شانه', 'کارتن']

const own = computed(() => session.isBuyer && session.buyerScopes.length === 1 ? session.buyerScopes[0] as BuyScope : null)

const scopeTab = ref<BuyScope>('Restaurant')
const scopeTabs: { value: BuyScope; label: string }[] = [
  { value: 'Restaurant', label: 'رستوران' },
  { value: 'Cafe', label: 'کافه' },
]

type Period = 'today' | 'week' | 'month' | 'all'
const period = ref<Period>('week')
const periods: { value: Period; label: string }[] = [
  { value: 'today', label: 'امروز' },
  { value: 'week', label: '۷ روز' },
  { value: 'month', label: '۳۰ روز' },
  { value: 'all', label: 'همه' },
]

const data = ref<BuyList>({ rows: [], totals: {} })
const ingredients = ref<{ item_code: string; item_name: string; stock_uom: string }[]>([])
const loading = ref(true)
const saving = ref(false)

function range(): { from_date?: string; to_date?: string } {
  if (period.value === 'all') return {}
  const days = { today: 0, week: 6, month: 29 }[period.value]
  const from = new Date()
  from.setDate(from.getDate() - days)
  return { from_date: isoDate(from), to_date: isoDate() }
}

async function load() {
  loading.value = true
  try {
    data.value = await get<BuyList>('cafe_app.api.purchasing.list_purchases', {
      ...range(),
      scope: own.value ?? scopeTab.value,
    })
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  load()
  ingredients.value = await get<typeof ingredients.value>('cafe_app.api.purchasing.ingredients').catch(() => [])
})
watch([scopeTab, period], load)
// the assistant confirmed a purchase from the chat
watch(() => agent.dataVersion, load)

const visibleScopes = computed<BuyScope[]>(() =>
  [own.value ?? scopeTab.value],
)

// ---- Purchase form ----
type Line = { item_name: string; qty: number | null; unit: string; amountToman: number | null }
type Form = { name?: string; scope: BuyScope; purchase_date: string; supplier: string; payment: BuyPayment; note: string; lines: Line[] }

const formOpen = ref(false)
const form = ref<Form>(blankForm())

function blankForm(): Form {
  return {
    scope: own.value ?? scopeTab.value,
    purchase_date: isoDate(),
    supplier: '',
    payment: 'Card',
    note: '',
    lines: [{ item_name: '', qty: null, unit: 'کیلو', amountToman: null }],
  }
}

function openNew() {
  form.value = blankForm()
  formOpen.value = true
}

function openEdit(p: BuyPurchase) {
  form.value = {
    name: p.name,
    scope: p.scope,
    purchase_date: p.purchase_date,
    supplier: p.supplier ?? '',
    payment: p.payment,
    note: p.note ?? '',
    lines: p.items.map((i) => ({ item_name: i.item_name, qty: i.qty, unit: i.unit ?? '', amountToman: toToman(i.amount) })),
  }
  formOpen.value = true
}

const formTotal = computed(() => form.value.lines.reduce((sum, l) => sum + toRial(l.amountToman ?? 0), 0))
const unitPrice = (l: Line) => (l.qty && l.amountToman ? toRial(l.amountToman / l.qty) : 0)
const ingredientNames = computed(() => new Map(ingredients.value.map((i) => [i.item_name, i.item_code])))

function setDay(offset: number) {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  form.value.purchase_date = isoDate(d)
}

async function save() {
  saving.value = true
  try {
    const f = form.value
    await post('cafe_app.api.purchasing.save_purchase', {
      data: {
        name: f.name,
        scope: f.scope,
        purchase_date: f.purchase_date,
        supplier: f.supplier,
        payment: f.payment,
        note: f.note,
        items: f.lines
          .filter((l) => l.item_name.trim() && l.amountToman)
          .map((l) => ({
            item_name: l.item_name.trim(),
            ingredient: ingredientNames.value.get(l.item_name.trim()) ?? null,
            qty: l.qty,
            unit: l.unit,
            amount: toRial(l.amountToman ?? 0),
          })),
      },
    })
    toast(f.name ? 'خرید ویرایش شد' : 'خرید ثبت شد')
    formOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}

async function remove(p: BuyPurchase) {
  if (!window.confirm(`خرید ${toman(p.total)} تومانی ${jDate(p.purchase_date)} حذف شود؟`)) return
  try {
    await post('cafe_app.api.purchasing.delete_purchase', { name: p.name })
    toast('خرید حذف شد')
    load()
  } catch (error) {
    toastError(error)
  }
}

function askAssistant() {
  agent.open = true
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <Segmented v-if="!own" v-model="scopeTab" :options="scopeTabs" />
      <span v-else class="rounded-full border border-one-500/30 bg-one-500/10 px-4 py-1.5 text-sm text-one-400">دفتر خرید {{ SCOPES[own] }}</span>
      <Segmented v-model="period" :options="periods" />
      <div class="flex-1" />
      <button class="btn-ghost" @click="askAssistant"><Sparkles class="size-4 text-one-500" /> با دستیار ثبت کن</button>
      <button class="btn-primary" @click="openNew"><Plus class="size-4" /> خرید جدید</button>
    </div>

    <!-- totals per desk -->
    <div class="grid gap-4" :class="visibleScopes.length > 1 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'">
      <div v-for="scope in visibleScopes" :key="scope" class="card p-5">
        <p class="text-xs text-ink-400">خرید {{ SCOPES[scope] }}</p>
        <p class="num mt-2 text-2xl font-black text-bone">{{ toman(data.totals[scope]?.total ?? 0) }} <span class="text-xs font-normal text-ink-400">تومان</span></p>
        <p class="mt-1 text-xs text-ink-500">{{ faNumber(data.totals[scope]?.count ?? 0) }} خرید</p>
      </div>
      <button class="card flex items-center gap-4 p-5 text-right transition hover:border-one-500/30" @click="askAssistant">
        <div class="grid size-11 shrink-0 place-items-center rounded-2xl bg-one-500/15 text-one-400"><Bot class="size-5" /></div>
        <div class="min-w-0 text-sm">
          <p class="font-bold text-bone">خریدت را بگو، دستیار ثبتش می‌کند</p>
          <p class="mt-1 truncate text-ink-400">مثلاً «۲۰ کیلو گوشت از قصابی گرفتم کیلویی ۸۵۰ هزار»</p>
        </div>
      </button>
    </div>

    <div v-if="loading && !data.rows.length" class="space-y-3">
      <div v-for="i in 4" :key="i" class="card h-24 animate-pulse" />
    </div>
    <div v-else-if="data.rows.length" class="space-y-3">
      <article v-for="p in data.rows" :key="p.name" class="card p-5">
        <div class="flex flex-wrap items-start gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2 text-xs">
              <span class="text-ink-300">{{ jDate(p.purchase_date) }}</span>
              <span v-if="!own" class="rounded-full px-2 py-0.5" :class="p.scope === 'Restaurant' ? 'bg-amber-300/10 text-amber-300' : 'bg-mint-400/10 text-mint-400'">{{ SCOPES[p.scope] }}</span>
              <span class="rounded-full bg-white/[0.05] px-2 py-0.5 text-ink-300">{{ PAYMENTS[p.payment] }}</span>
              <span v-if="p.source === 'Assistant'" class="flex items-center gap-1 rounded-full bg-one-500/10 px-2 py-0.5 text-one-400"><Sparkles class="size-3" /> دستیار</span>
              <span class="text-ink-500">{{ p.owner_name }}</span>
            </div>
            <p class="mt-2 font-bold text-bone">{{ p.supplier || 'بدون نام فروشنده' }}</p>
          </div>
          <p class="num text-xl font-black text-bone">{{ toman(p.total) }} <span class="text-xs font-normal text-ink-400">تومان</span></p>
          <div class="flex gap-1">
            <button class="rounded-lg p-2 text-ink-400 hover:bg-white/5 hover:text-one-400" title="ویرایش" @click="openEdit(p)"><Pencil class="size-4" /></button>
            <button class="rounded-lg p-2 text-ink-400 hover:bg-white/5 hover:text-rose-400" title="حذف" @click="remove(p)"><Trash2 class="size-4" /></button>
          </div>
        </div>
        <ul class="mt-3 flex flex-wrap gap-2 text-xs">
          <li v-for="(i, index) in p.items" :key="index" class="rounded-xl bg-white/[0.03] px-3 py-1.5 text-ink-200">
            {{ i.item_name }}
            <span v-if="i.qty" class="text-ink-400">· {{ faNumber(i.qty, 2) }} {{ i.unit }}</span>
            <span class="num text-ink-400">· {{ toman(i.amount) }}</span>
          </li>
        </ul>
        <p v-if="p.note" class="mt-2 text-xs text-ink-400">{{ p.note }}</p>
      </article>
    </div>
    <EmptyState v-else :icon="ShoppingBasket" title="خریدی در این بازه ثبت نشده" text="از «خرید جدید» یا با گفتن به دستیار ثبتش کن." />

    <Modal v-model="formOpen" :title="form.name ? 'ویرایش خرید' : 'خرید جدید'" width="max-w-3xl">
      <div class="space-y-5">
        <div class="grid gap-4 sm:grid-cols-2">
          <p class="text-sm text-ink-300">دفتر خرید {{ SCOPES[form.scope] }}</p>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">فروشنده</span>
            <input v-model="form.supplier" class="field" placeholder="مثلاً: قصابی رضا" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">پرداخت</span>
            <select v-model="form.payment" class="field">
              <option v-for="(label, value) in PAYMENTS" :key="value" :value="value">{{ label }}</option>
            </select>
          </label>
          <div class="block">
            <span class="mb-2 block text-sm text-ink-300">تاریخ · {{ jDate(form.purchase_date) }}</span>
            <div class="flex gap-2">
              <input v-model="form.purchase_date" type="date" class="field" dir="ltr" />
              <button class="btn-ghost h-11 shrink-0 px-3 text-xs" @click="setDay(0)">امروز</button>
              <button class="btn-ghost h-11 shrink-0 px-3 text-xs" @click="setDay(-1)">دیروز</button>
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <div class="hidden grid-cols-[1fr_90px_110px_140px_auto] gap-2 px-1 text-xs text-ink-400 sm:grid">
            <span>کالا</span><span>مقدار</span><span>واحد</span><span>مبلغ کل (تومان)</span><span class="w-10" />
          </div>
          <div v-for="(line, index) in form.lines" :key="index" class="grid grid-cols-2 items-center gap-2 sm:grid-cols-[1fr_90px_110px_140px_auto]">
            <input v-model="line.item_name" class="field col-span-2 h-10 sm:col-span-1" list="buy-ingredients" placeholder="نام کالا" />
            <input v-model.number="line.qty" type="number" min="0" step="any" class="field h-10" placeholder="مقدار" />
            <input v-model="line.unit" class="field h-10" list="buy-units" placeholder="واحد" />
            <div class="relative">
              <input v-model.number="line.amountToman" type="number" min="0" step="any" class="field h-10" placeholder="مبلغ" />
              <span v-if="unitPrice(line)" class="absolute -bottom-4 right-1 text-[10px] text-ink-500">هر {{ line.unit || 'واحد' }} {{ toman(unitPrice(line)) }}</span>
            </div>
            <button class="grid size-10 place-items-center rounded-xl text-ink-400 hover:text-rose-400" @click="form.lines.splice(index, 1)"><Trash2 class="size-4" /></button>
          </div>
          <datalist id="buy-ingredients">
            <option v-for="i in ingredients" :key="i.item_code" :value="i.item_name" />
          </datalist>
          <datalist id="buy-units">
            <option v-for="u in UNITS" :key="u" :value="u" />
          </datalist>
          <button class="btn-ghost mt-3 h-9 text-xs" @click="form.lines.push({ item_name: '', qty: null, unit: 'کیلو', amountToman: null })"><Plus class="size-3.5" /> قلم دیگر</button>
        </div>

        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">یادداشت</span>
          <input v-model="form.note" class="field" />
        </label>

        <p class="text-xs text-ink-500">اگر نام کالا با مواد اولیه منو یکی باشد، قیمت این خرید در بهای تمام‌شده محصولات حساب می‌شود.</p>

        <div class="flex items-baseline justify-between rounded-2xl bg-white/[0.03] px-5 py-4">
          <span class="text-ink-300">جمع خرید · {{ faNumber(form.lines.filter((l) => l.item_name && l.amountToman).length) }} قلم</span>
          <span class="num text-2xl font-black text-bone">{{ toman(formTotal) }} <span class="text-sm font-normal text-ink-400">تومان</span></span>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="formOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || !formTotal" @click="save">
          <LoaderCircle v-if="saving" class="size-4 animate-spin" /> {{ form.name ? 'ذخیره' : 'ثبت خرید' }}
        </button>
      </template>
    </Modal>
  </div>
</template>
