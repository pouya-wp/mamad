<script setup lang="ts">
import { Activity, ChevronDown, LoaderCircle } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import { get } from '@/lib/api'
import { jDate, toman } from '@/lib/format'
import { toastError } from '@/lib/toast'

type ActivityRow = {
  name: string; creation: string; actor: string; actor_name: string
  action: string; reference_doctype: string; reference_name: string
  scope: 'Restaurant' | 'Cafe' | null; summary: string
  before: Record<string, unknown> | null; after: Record<string, unknown> | null
}
type Actor = { actor: string; actor_name: string }

const actionLabels: Record<string, string> = {
  'purchase.create': 'ثبت خرید', 'purchase.update': 'ویرایش خرید', 'purchase.delete': 'حذف خرید',
  'recipe.update': 'ویرایش رسپی', 'expense.create': 'ثبت هزینه', 'advance.create': 'ثبت مساعده',
}
const fieldLabels: Record<string, string> = {
  scope: 'بخش', purchase_date: 'تاریخ خرید', posting_date: 'تاریخ ثبت', supplier: 'فروشنده',
  payment: 'روش پرداخت', mode_of_payment: 'پرداخت از', total: 'جمع', amount: 'مبلغ',
  note: 'توضیح', source: 'روش ثبت', kind: 'نوع', expense_account: 'حساب هزینه',
  employee: 'شناسه کارمند', employee_name: 'کارمند', journal_entry: 'سند حسابداری',
  notes: 'توضیح رسپی',
}
const actors = ref<Actor[]>([])
const rows = ref<ActivityRow[]>([])
const loading = ref(false)
const hasMore = ref(false)
const filters = ref({ actor: '', action: '', scope: '', from: '', to: '' })

async function load(more = false) {
  loading.value = true
  try {
    const batch = await get<ActivityRow[]>('cafe_app.api.buyer_activity.list_activity', {
      actor: filters.value.actor || undefined,
      action: filters.value.action || undefined,
      scope: filters.value.scope || undefined,
      from_date: filters.value.from || undefined,
      to_date: filters.value.to || undefined,
      start: more ? rows.value.length : 0,
      limit: 100,
    })
    rows.value = more ? [...rows.value, ...batch] : batch
    hasMore.value = batch.length === 100
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  actors.value = await get<Actor[]>('cafe_app.api.buyer_activity.actors').catch(() => [])
  await load(false)
})

function valueText(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (key === 'scope') return value === 'Restaurant' ? 'رستوران' : 'کافه'
  if (key === 'kind') return value === 'Advance' ? 'مساعده' : 'هزینه'
  if (['total', 'amount', 'fixed_cost', 'unit_price'].includes(key)) return `${toman(Number(value))} تومان`
  if (key.endsWith('date')) return jDate(String(value))
  return String(value)
}

function snapshotLines(snapshot: Record<string, unknown> | null): string[] {
  if (!snapshot) return []
  const lines: string[] = []
  for (const [key, value] of Object.entries(snapshot)) {
    if ((key === 'items' || key === 'rows') && Array.isArray(value)) {
      lines.push(`${key === 'items' ? 'اقلام خرید' : 'مواد رسپی'}: ${value.length} ردیف`)
      for (const [index, raw] of value.entries()) {
        const item = raw as Record<string, unknown>
        const name = item.item_name ?? item.ingredient_name ?? item.ingredient ?? 'قلم'
        const qty = item.qty ? ` · ${item.qty} ${item.unit ?? ''}` : ''
        const amount = item.amount ? ` · ${valueText('amount', item.amount)}` : item.fixed_cost ? ` · هزینه ثابت ${valueText('fixed_cost', item.fixed_cost)}` : ''
        lines.push(`  ${index + 1}. ${name}${qty}${amount}`)
      }
    } else {
      lines.push(`${fieldLabels[key] ?? key}: ${valueText(key, value)}`)
    }
  }
  return lines
}
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="flex items-center gap-2 text-xl font-black text-bone"><Activity class="size-5 text-one-400" /> فعالیت مسئولان خرید</h1>
      <p class="mt-1 text-sm text-ink-400">ثبت، ویرایش و حذف خریدها، ویرایش رسپی‌ها، هزینه‌ها و مساعده‌ها با نام کاربر و جزئیات قبل و بعد؛ از زمان فعال‌سازی این بخش.</p>
    </div>

    <form class="card grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-6" @submit.prevent="load(false)">
      <label class="block">
        <span class="mb-1 block text-xs text-ink-400">کاربر</span>
        <select v-model="filters.actor" class="field">
          <option value="">همه</option>
          <option v-for="actor in actors" :key="actor.actor" :value="actor.actor">{{ actor.actor_name || actor.actor }}</option>
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-xs text-ink-400">عملیات</span>
        <select v-model="filters.action" class="field">
          <option value="">همه</option>
          <option v-for="(label, action) in actionLabels" :key="action" :value="action">{{ label }}</option>
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-xs text-ink-400">بخش</span>
        <select v-model="filters.scope" class="field">
          <option value="">همه</option>
          <option value="Restaurant">رستوران</option>
          <option value="Cafe">کافه</option>
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-xs text-ink-400">از تاریخ</span>
        <input v-model="filters.from" type="date" class="field" dir="ltr" />
      </label>
      <label class="block">
        <span class="mb-1 block text-xs text-ink-400">تا تاریخ</span>
        <input v-model="filters.to" type="date" class="field" dir="ltr" />
      </label>
      <button type="submit" class="btn-primary self-end justify-center" :disabled="loading">
        <LoaderCircle v-if="loading" class="size-4 animate-spin" /> نمایش
      </button>
    </form>

    <div v-if="rows.length" class="space-y-3">
      <article v-for="row in rows" :key="row.name" class="card p-4 sm:p-5">
        <div class="flex flex-wrap items-start gap-3">
          <div class="min-w-48 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-full bg-one-500/10 px-2.5 py-1 text-xs font-bold text-one-400">{{ actionLabels[row.action] ?? row.action }}</span>
              <span v-if="row.scope" class="rounded-full bg-white/[0.05] px-2.5 py-1 text-xs text-ink-300">{{ row.scope === 'Restaurant' ? 'رستوران' : 'کافه' }}</span>
            </div>
            <p class="mt-2 font-medium text-bone">{{ row.summary }}</p>
            <p class="mt-1 text-xs text-ink-400">{{ row.actor_name || row.actor }} · {{ jDate(row.creation.slice(0, 10)) }} ساعت {{ row.creation.slice(11, 16) }}</p>
            <p class="mt-1 text-[11px] text-ink-600">{{ row.reference_name }}</p>
          </div>
        </div>
        <details class="group mt-3 border-t border-white/[0.05] pt-3">
          <summary class="flex cursor-pointer list-none items-center gap-1 text-xs text-ink-300 hover:text-bone">
            <ChevronDown class="size-4 transition group-open:rotate-180" /> جزئیات دقیق
          </summary>
          <div class="mt-3 grid gap-3" :class="row.before && row.after ? 'lg:grid-cols-2' : ''">
            <div v-if="row.before" class="rounded-xl bg-white/[0.03] p-4">
              <p class="mb-2 text-xs font-bold text-ink-300">قبل</p>
              <p v-for="(line, i) in snapshotLines(row.before)" :key="i" class="whitespace-pre-wrap break-words py-0.5 text-xs leading-6 text-ink-400">{{ line }}</p>
            </div>
            <div v-if="row.after" class="rounded-xl bg-white/[0.03] p-4">
              <p class="mb-2 text-xs font-bold text-ink-300">بعد</p>
              <p v-for="(line, i) in snapshotLines(row.after)" :key="i" class="whitespace-pre-wrap break-words py-0.5 text-xs leading-6 text-ink-200">{{ line }}</p>
            </div>
          </div>
        </details>
      </article>
    </div>
    <EmptyState v-else-if="!loading" :icon="Activity" title="فعالیتی در این بازه ثبت نشده" />
    <button v-if="hasMore" class="btn-ghost mx-auto" :disabled="loading" @click="load(true)">
      <LoaderCircle v-if="loading" class="size-4 animate-spin" /> نمایش موارد قدیمی‌تر
    </button>
  </div>
</template>
