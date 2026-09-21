<script setup lang="ts">
import { ClipboardCheck, History, LoaderCircle, Package, Plus, Search, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import Panel from '@/components/Panel.vue'
import StatCard from '@/components/StatCard.vue'
import { get, post } from '@/lib/api'
import { faNumber, jShortDate, shortTime, toman, uom } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { Ingredient, Movement } from '@/lib/types'

const items = ref<Ingredient[]>([])
const moves = ref<Movement[]>([])
const loading = ref(true)
const search = ref('')
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    ;[items.value, moves.value] = await Promise.all([
      get<Ingredient[]>('cafe_app.api.menu.list_ingredients'),
      get<Movement[]>('cafe_app.api.inventory.movements', { limit: 40 }),
    ])
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const visible = computed(() => items.value.filter((i) => !i.disabled && (!search.value || i.item_name.includes(search.value))))
const stockValue = computed(() => items.value.reduce((sum, i) => sum + i.stock_value, 0))
const low = computed(() => items.value.filter((i) => i.actual_qty > 0 && i.actual_qty <= i.safety_stock).length)
const out = computed(() => items.value.filter((i) => i.actual_qty <= 0).length)

const status = (i: Ingredient) =>
  i.actual_qty <= 0 ? { label: 'تمام شده', tone: 'bg-rose-400/10 text-rose-400', bar: 'bg-rose-400' }
  : i.actual_qty <= i.safety_stock ? { label: 'رو به اتمام', tone: 'bg-amber-300/10 text-amber-300', bar: 'bg-amber-300' }
  : { label: 'کافی', tone: 'bg-mint-400/10 text-mint-400', bar: 'bg-bone/50' }

const fill = (i: Ingredient) => `${Math.min(100, (i.actual_qty / Math.max(i.safety_stock * 3, 1)) * 100)}%`

const VOUCHERS: Record<string, string> = {
  'Sales Invoice': 'فروش',
  'Purchase Invoice': 'خرید',
  'Purchase Receipt': 'رسید خرید',
  'Stock Entry': 'ضایعات / انتقال',
  'Stock Reconciliation': 'انبارگردانی',
}

// ---- Waste ----
type Row = { item_code: string; qty: number | null }
const wasteOpen = ref(false)
const wasteRows = ref<Row[]>([{ item_code: '', qty: null }])
const wasteReason = ref('')
const byCode = computed(() => new Map(items.value.map((i) => [i.item_code, i])))

async function saveWaste() {
  saving.value = true
  try {
    await post('cafe_app.api.inventory.record_waste', {
      items: wasteRows.value.filter((r) => r.item_code && r.qty),
      reason: wasteReason.value || 'ضایعات',
    })
    toast('ضایعات ثبت شد')
    wasteOpen.value = false
    wasteRows.value = [{ item_code: '', qty: null }]
    wasteReason.value = ''
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}

// ---- Stock count ----
const countOpen = ref(false)
const counted = ref<Record<string, number | null>>({})

function openCount() {
  counted.value = {}
  countOpen.value = true
}

async function saveCount() {
  const rows = Object.entries(counted.value)
    .filter(([, qty]) => qty !== null && qty !== undefined && (qty as unknown) !== '')
    .map(([item_code, qty]) => ({
      item_code,
      qty,
      valuation_rate: byCode.value.get(item_code)?.valuation_rate || undefined,
    }))
  if (!rows.length) return toast('حداقل یک قلم را شمارش کن', 'info')

  saving.value = true
  try {
    await post('cafe_app.api.inventory.stock_count', { items: rows, note: 'انبارگردانی از پنل' })
    toast(`انبارگردانی ${faNumber(rows.length)} قلم ثبت شد`)
    countOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="grid gap-4 sm:grid-cols-3">
      <StatCard accent label="ارزش موجودی انبار" :value="stockValue" format="toman" unit="تومان" />
      <StatCard label="رو به اتمام" :value="low" format="number" unit="قلم" hint="زیر حد مجاز" />
      <StatCard label="تمام شده" :value="out" format="number" unit="قلم" />
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <div class="relative min-w-56 flex-1 sm:max-w-xs">
        <Search class="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-ink-400" />
        <input v-model="search" class="field pr-10" placeholder="جستجوی ماده اولیه…" />
      </div>
      <div class="flex-1" />
      <button class="btn-ghost" @click="wasteOpen = true"><Trash2 class="size-4" /> ثبت ضایعات</button>
      <button class="btn-primary" @click="openCount"><ClipboardCheck class="size-4" /> انبارگردانی</button>
    </div>

    <div class="grid gap-6 2xl:grid-cols-3">
      <div class="card overflow-hidden 2xl:col-span-2">
        <div class="overflow-x-auto">
          <table class="w-full min-w-[640px] text-sm">
            <thead>
              <tr class="border-b border-white/[0.06] text-right text-xs text-ink-400">
                <th class="px-6 py-4 font-medium">ماده اولیه</th>
                <th class="w-[34%] px-4 py-4 font-medium">موجودی</th>
                <th class="px-4 py-4 font-medium">ارزش (تومان)</th>
                <th class="px-6 py-4 font-medium">وضعیت</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04]">
              <tr v-for="i in visible" :key="i.item_code">
                <td class="px-6 py-3.5">
                  <p class="font-medium text-ink-100">{{ i.item_name }}</p>
                  <p class="text-xs text-ink-500">{{ i.item_group }}</p>
                </td>
                <td class="px-4 py-3.5">
                  <div class="flex items-baseline justify-between gap-2">
                    <span class="num text-ink-100">{{ faNumber(i.actual_qty) }} <span class="text-xs text-ink-500">{{ uom(i.stock_uom) }}</span></span>
                    <span class="num text-[11px] text-ink-500">حد {{ faNumber(i.safety_stock) }}</span>
                  </div>
                  <div class="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.05]">
                    <div class="h-full rounded-full transition-all duration-700" :class="status(i).bar" :style="{ width: fill(i) }" />
                  </div>
                </td>
                <td class="num px-4 py-3.5 text-ink-300">{{ toman(i.stock_value) }}</td>
                <td class="px-6 py-3.5">
                  <span class="rounded-full px-2.5 py-1 text-xs" :class="status(i).tone">{{ status(i).label }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-if="!loading && !visible.length" :icon="Package" title="ماده اولیه‌ای نیست" />
        <div v-if="loading" class="flex justify-center py-6"><LoaderCircle class="size-5 animate-spin text-ink-400" /></div>
      </div>

      <Panel title="گردش انبار" subtitle="آخرین ورود و خروج‌ها">
        <ul v-if="moves.length" class="max-h-[640px] divide-y divide-white/[0.04] overflow-y-auto pl-2">
          <li v-for="(m, index) in moves" :key="index" class="flex items-center gap-3 py-3">
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm text-ink-100">{{ m.item_name }}</p>
              <p class="text-xs text-ink-500">{{ VOUCHERS[m.voucher_type] ?? m.voucher_type }} · {{ jShortDate(m.posting_date) }} {{ shortTime(m.posting_time) }}</p>
            </div>
            <!-- a stock count sets the quantity instead of moving it -->
            <span v-if="m.voucher_type === 'Stock Reconciliation'" class="num text-sm font-medium text-ink-200" dir="ltr">
              = {{ faNumber(m.qty_after_transaction) }}
              <span class="text-[11px] font-normal text-ink-500">{{ uom(m.stock_uom) }}</span>
            </span>
            <span v-else class="num text-sm font-medium" :class="m.actual_qty < 0 ? 'text-rose-400' : 'text-mint-400'" dir="ltr">
              {{ m.actual_qty > 0 ? '+' : '' }}{{ faNumber(m.actual_qty) }}
              <span class="text-[11px] font-normal text-ink-500">{{ uom(m.stock_uom) }}</span>
            </span>
          </li>
        </ul>
        <EmptyState v-else :icon="History" title="گردشی ثبت نشده" />
      </Panel>
    </div>

    <!-- Waste -->
    <Modal v-model="wasteOpen" title="ثبت ضایعات">
      <div class="space-y-3">
        <div v-for="(row, index) in wasteRows" :key="index" class="grid grid-cols-[1fr_130px_auto] gap-2">
          <select v-model="row.item_code" class="field h-10">
            <option value="" disabled>انتخاب ماده</option>
            <option v-for="i in items" :key="i.item_code" :value="i.item_code">{{ i.item_name }}</option>
          </select>
          <div class="relative">
            <input v-model.number="row.qty" type="number" min="0" step="any" class="field h-10 pl-14" />
            <span class="absolute inset-y-0 left-3 grid place-items-center text-xs text-ink-400">{{ uom(byCode.get(row.item_code)?.stock_uom) }}</span>
          </div>
          <button class="grid size-10 place-items-center rounded-xl text-ink-400 hover:text-rose-400" @click="wasteRows.splice(index, 1)"><Trash2 class="size-4" /></button>
        </div>
        <button class="btn-ghost h-9 text-xs" @click="wasteRows.push({ item_code: '', qty: null })"><Plus class="size-3.5" /> قلم دیگر</button>
        <input v-model="wasteReason" class="field" placeholder="علت (مثلاً: شیر ترش شد)" />
      </div>
      <template #footer>
        <button class="btn-ghost" @click="wasteOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving" @click="saveWaste">ثبت</button>
      </template>
    </Modal>

    <!-- Stock count -->
    <Modal v-model="countOpen" title="انبارگردانی" width="max-w-2xl">
      <p class="mb-4 text-sm text-ink-400">مقدار واقعی شمارش‌شده را فقط برای اقلامی که شمردی وارد کن.</p>
      <div class="divide-y divide-white/[0.05]">
        <div v-for="i in items" :key="i.item_code" class="grid grid-cols-[1fr_110px_140px] items-center gap-3 py-2.5 text-sm">
          <span class="text-ink-100">{{ i.item_name }}</span>
          <span class="num text-ink-500">سیستم: {{ faNumber(i.actual_qty) }}</span>
          <div class="relative">
            <input v-model.number="counted[i.item_code]" type="number" min="0" step="any" class="field h-9 pl-14" />
            <span class="absolute inset-y-0 left-3 grid place-items-center text-xs text-ink-400">{{ uom(i.stock_uom) }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="countOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving" @click="saveCount">ثبت انبارگردانی</button>
      </template>
    </Modal>
  </div>
</template>
