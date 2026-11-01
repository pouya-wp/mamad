<script setup lang="ts">
import { HandCoins, LoaderCircle, ReceiptText, Wallet } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Segmented from '@/components/Segmented.vue'
import { get, post } from '@/lib/api'
import { isoDate, jDate, toman, toRial } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'

type Scope = 'Restaurant' | 'Cafe'
type Kind = 'Expense' | 'Advance'
type Option = { value: string; label: string }
type Options = {
  scopes: { value: Scope; label: string }[]
  accounts: { name: string; account_name: string }[]
  employees: { name: string; full_name: string }[]
  modes: Option[]
}
type Entry = {
  name: string; owner_name: string; scope: Scope; kind: Kind; posting_date: string
  amount: number; mode_of_payment: string; expense_account: string | null
  employee_name: string | null; note: string | null; journal_entry: string
}

const kinds: { value: Kind; label: string }[] = [
  { value: 'Expense', label: 'هزینه‌ها' },
  { value: 'Advance', label: 'مساعده کارکنان' },
]
const kind = ref<Kind>('Expense')
const scope = ref<Scope>('Restaurant')
const options = ref<Options | null>(null)
const entries = ref<Entry[]>([])
const loading = ref(true)
const saving = ref(false)
const ready = ref(false)
const form = ref({ amountToman: null as number | null, account: '', employee: '', mode: 'Cash', date: isoDate(), note: '' })

async function load() {
  loading.value = true
  try {
    entries.value = await get<Entry[]>('cafe_app.api.buyer_expenses.list_entries', {
      scope: scope.value, kind: kind.value, limit: 100,
    })
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    options.value = await get<Options>('cafe_app.api.buyer_expenses.options')
    scope.value = options.value.scopes[0]?.value ?? 'Restaurant'
    form.value.account = options.value.accounts[0]?.name ?? ''
    form.value.employee = options.value.employees[0]?.name ?? ''
    await load()
    ready.value = true
  } catch (error) {
    loading.value = false
    toastError(error)
  }
})
watch([kind, scope], () => { if (ready.value) load() })

async function save() {
  if (!form.value.amountToman || form.value.amountToman <= 0) return
  saving.value = true
  try {
    await post('cafe_app.api.buyer_expenses.record_entry', {
      scope: scope.value,
      kind: kind.value,
      amount: toRial(form.value.amountToman),
      mode_of_payment: form.value.mode,
      posting_date: form.value.date,
      account: kind.value === 'Expense' ? form.value.account : null,
      employee: kind.value === 'Advance' ? form.value.employee : null,
      note: form.value.note || null,
    })
    toast(kind.value === 'Advance' ? 'مساعده و سند حسابداری ثبت شد' : 'هزینه و سند حسابداری ثبت شد')
    form.value.amountToman = null
    form.value.note = ''
    await load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <div>
        <h1 class="text-xl font-black text-bone">هزینه‌ها</h1>
        <p class="mt-1 text-sm text-ink-400">پرداخت‌های هر بخش و مساعده کارکنان را با سند حسابداری ثبت کن.</p>
      </div>
      <div class="flex-1" />
      <select v-model="scope" class="field w-auto min-w-36" aria-label="بخش خرید">
        <option v-for="item in options?.scopes ?? []" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
    </div>

    <Segmented v-model="kind" :options="kinds" />

    <div class="grid gap-6 xl:grid-cols-[380px_1fr]">
      <section class="card p-5">
        <div class="mb-5 flex items-center gap-3">
          <div class="grid size-10 place-items-center rounded-xl bg-one-500/10 text-one-400">
            <HandCoins v-if="kind === 'Advance'" class="size-5" />
            <Wallet v-else class="size-5" />
          </div>
          <div>
            <h2 class="font-bold text-bone">ثبت {{ kind === 'Advance' ? 'مساعده' : 'هزینه' }} {{ scope === 'Restaurant' ? 'رستوران' : 'کافه' }}</h2>
            <p class="text-xs text-ink-400">پس از ثبت، سند حسابداری ارسال می‌شود.</p>
          </div>
        </div>

        <form class="space-y-4" @submit.prevent="save">
          <label v-if="kind === 'Expense'" class="block">
            <span class="mb-2 block text-sm text-ink-300">نوع هزینه</span>
            <select v-model="form.account" class="field" required>
              <option v-for="account in options?.accounts ?? []" :key="account.name" :value="account.name">{{ account.account_name }}</option>
            </select>
          </label>
          <label v-else class="block">
            <span class="mb-2 block text-sm text-ink-300">کارمند</span>
            <select v-model="form.employee" class="field" required>
              <option v-for="employee in options?.employees ?? []" :key="employee.name" :value="employee.name">{{ employee.full_name }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">مبلغ (تومان)</span>
            <input v-model.number="form.amountToman" class="field" type="number" min="1" step="1" required />
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="mb-2 block text-sm text-ink-300">پرداخت از</span>
              <select v-model="form.mode" class="field">
                <option v-for="mode in options?.modes ?? []" :key="mode.value" :value="mode.value">{{ mode.label }}</option>
              </select>
            </label>
            <label class="block">
              <span class="mb-2 block text-sm text-ink-300">تاریخ</span>
              <input v-model="form.date" class="field" type="date" dir="ltr" :max="isoDate()" required />
            </label>
          </div>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">توضیح</span>
            <textarea v-model="form.note" class="field min-h-20" maxlength="500" placeholder="اختیاری" />
          </label>
          <p v-if="kind === 'Advance'" class="rounded-xl border border-sky-400/20 bg-sky-400/5 p-3 text-xs leading-6 text-sky-200">
            مساعده در حساب دارایی ثبت می‌شود و هزینهٔ حقوق یا سود و زیان این روز محسوب نمی‌شود.
          </p>
          <button class="btn-primary w-full justify-center" type="submit" :disabled="saving || !options || !form.amountToman || (kind === 'Expense' ? !form.account : !form.employee)">
            <LoaderCircle v-if="saving" class="size-4 animate-spin" />
            ثبت {{ kind === 'Advance' ? 'مساعده' : 'هزینه' }}
          </button>
        </form>
      </section>

      <section class="card p-5">
        <div class="mb-4 flex items-center gap-2">
          <ReceiptText class="size-5 text-one-400" />
          <h2 class="font-bold text-bone">{{ kind === 'Advance' ? 'مساعده‌های ثبت‌شده' : 'هزینه‌های ثبت‌شده' }}</h2>
          <LoaderCircle v-if="loading" class="size-4 animate-spin text-ink-400" />
        </div>
        <div v-if="entries.length" class="divide-y divide-white/[0.05]">
          <div v-for="entry in entries" :key="entry.name" class="flex flex-wrap items-center gap-3 py-4 text-sm">
            <div class="min-w-44 flex-1">
              <p class="font-medium text-ink-100">{{ entry.kind === 'Advance' ? entry.employee_name : options?.accounts.find((a) => a.name === entry.expense_account)?.account_name ?? entry.expense_account }}</p>
              <p class="mt-1 text-xs text-ink-400">{{ jDate(entry.posting_date) }} · {{ entry.owner_name }} · {{ entry.mode_of_payment === 'Cash' ? 'نقدی' : 'کارتخوان' }}</p>
              <p v-if="entry.note" class="mt-1 text-xs text-ink-500">{{ entry.note }}</p>
              <p class="mt-1 text-[11px] text-ink-600">سند {{ entry.journal_entry }} · {{ entry.name }}</p>
            </div>
            <span class="num font-bold text-bone">{{ toman(entry.amount) }}</span>
          </div>
        </div>
        <EmptyState v-else-if="!loading" :icon="kind === 'Advance' ? HandCoins : Wallet" title="موردی ثبت نشده" />
      </section>
    </div>
  </div>
</template>
