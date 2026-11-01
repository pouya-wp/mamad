<script setup lang="ts">
import { LoaderCircle, Pencil, Plus, Receipt, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import { get, post } from '@/lib/api'
import { DIRECTION_LABELS, DIRECTION_TONES, KIND_LABELS, STATUS_LABELS, STATUS_TONES } from '@/lib/cheques'
import { faDigits, faNumber, fromJalaliInput, isoDate, jDate, toJalaliInput, toman, toRial, toToman } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { Cheque, ChequeKind, ChequeList, ChequeStatus } from '@/lib/types'

const statusFilter = ref<ChequeStatus | ''>('')

const data = ref<ChequeList | null>(null)
const loading = ref(true)
const saving = ref(false)
const today = isoDate()

async function load() {
  loading.value = true
  try {
    data.value = await get<ChequeList>('cafe_app.api.cheques.list_cheques', {
      direction: 'Issued',
      status: statusFilter.value || undefined,
    })
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(statusFilter, load)

function dueLabel(c: Cheque) {
  if (!c.due_date) return 'بدون سررسید'
  if (c.status !== 'Pending') return jDate(c.due_date)
  const days = Math.round((new Date(c.due_date).getTime() - new Date(today).getTime()) / 86_400_000)
  if (days < 0) return `${jDate(c.due_date)} · ${faNumber(-days)} روز گذشته`
  if (days === 0) return 'امروز'
  return `${jDate(c.due_date)} · ${faNumber(days)} روز دیگر`
}
const overdue = (c: Cheque) => c.status === 'Pending' && !!c.due_date && c.due_date < today

// ---- editor ----
type Form = Omit<Cheque, 'amount' | 'due_date' | 'issue_date'> & { amountToman: number | null; due: string; issued: string }
const editorOpen = ref(false)
const form = ref<Form>(blank())

function blank(): Form {
  return {
    direction: 'Issued',
    kind: 'Regular',
    party: '',
    amountToman: null,
    due: '',
    issued: '',
    status: 'Pending',
    bank: '',
    cheque_no: '',
    sayad_id: '',
    note: '',
  }
}

function openNew() {
  form.value = blank()
  editorOpen.value = true
}

function edit(c: Cheque) {
  form.value = { ...c, amountToman: toToman(c.amount), due: toJalaliInput(c.due_date), issued: toJalaliInput(c.issue_date) }
  editorOpen.value = true
}

type AccountOption = { name: string; account_name: string }
const settlementAccounts = ref<{ bank: AccountOption[]; counterpart: AccountOption[] }>({ bank: [], counterpart: [] })
const settlementOpen = ref(false)
const settling = ref(false)
const settlementCheque = ref<Cheque | null>(null)
const bankAccount = ref('')
const counterpartAccount = ref('')

async function openSettlement(c: Cheque) {
  settlementCheque.value = c
  bankAccount.value = ''
  counterpartAccount.value = ''
  try {
    settlementAccounts.value = await get<{ bank: AccountOption[]; counterpart: AccountOption[] }>('cafe_app.api.cheques.settlement_accounts')
    settlementOpen.value = true
  } catch (error) {
    toastError(error)
  }
}

async function settle() {
  if (!settlementCheque.value?.name || !bankAccount.value || !counterpartAccount.value || settling.value) return
  settling.value = true
  try {
    const result = await post<{ journal_entry: string }>('cafe_app.api.cheques.settle_cheque', {
      name: settlementCheque.value.name, bank_account: bankAccount.value, counterpart_account: counterpartAccount.value,
    })
    toast(`تسویه و سند ${result.journal_entry} ثبت شد`)
    settlementOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    settling.value = false
  }
}

const badDate = (text: string) => !!text.trim() && !fromJalaliInput(text)
const formInvalid = computed(() => {
  const f = form.value
  return !f.party.trim() || !f.amountToman || badDate(f.due) || badDate(f.issued) || (f.kind === 'Regular' && !fromJalaliInput(f.due))
})

async function save() {
  saving.value = true
  try {
    const f = form.value
    await post('cafe_app.api.cheques.save_cheque', {
      data: {
        name: f.name,
        direction: 'Issued',
        kind: f.kind,
        party: f.party,
        amount: toRial(f.amountToman ?? 0),
        due_date: fromJalaliInput(f.due),
        issue_date: fromJalaliInput(f.issued),
        status: f.status,
        bank: f.bank,
        cheque_no: f.cheque_no,
        sayad_id: f.sayad_id,
        note: f.note,
      },
    })
    toast(f.name ? 'چک ویرایش شد' : 'چک ثبت شد')
    editorOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}

async function setStatus(c: Cheque, status: ChequeStatus) {
  try {
    await post('cafe_app.api.cheques.set_status', { name: c.name, status })
    toast(`وضعیت: ${STATUS_LABELS[status]}`)
    load()
  } catch (error) {
    toastError(error)
  }
}

async function remove() {
  if (!form.value.name || !window.confirm('این چک حذف شود؟')) return
  try {
    await post('cafe_app.api.cheques.delete_cheque', { name: form.value.name })
    toast('چک حذف شد')
    editorOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <select v-model="statusFilter" class="field h-10 w-auto">
        <option value="">همه‌ی وضعیت‌ها</option>
        <option v-for="(label, value) in STATUS_LABELS" :key="value" :value="value">{{ label }}</option>
      </select>
      <div class="flex-1" />
      <button class="btn-primary" @click="openNew"><Plus class="size-4" /> چک جدید</button>
    </div>

    <div v-if="data" class="grid gap-4 sm:grid-cols-3">
      <div class="card p-5">
        <p class="text-xs text-ink-400">پرداختی در جریان</p>
        <p class="num mt-2 text-2xl font-black text-rose-400">{{ toman(data.summary.Issued.pending) }} <span class="text-xs font-normal text-ink-400">تومان</span></p>
        <p class="mt-1 text-xs text-ink-500">{{ faNumber(data.summary.Issued.pending_count) }} چک · این هفته {{ toman(data.summary.Issued.due_week) }}</p>
      </div>
      <div class="card p-5">
        <p class="text-xs text-ink-400">سررسید گذشته و نامشخص</p>
        <p class="num mt-2 text-2xl font-black" :class="data.summary.Issued.overdue ? 'text-amber-300' : 'text-bone'">
          {{ faNumber(data.summary.Issued.overdue) }}
        </p>
      </div>
      <div class="card p-5">
        <p class="text-xs text-ink-400">برگشتی</p>
        <p class="num mt-2 text-2xl font-black" :class="data.summary.Issued.bounced ? 'text-rose-400' : 'text-bone'">
          {{ faNumber(data.summary.Issued.bounced) }}
        </p>
      </div>
    </div>

    <div v-if="loading && !data" class="space-y-3">
      <div v-for="i in 3" :key="i" class="card h-20 animate-pulse" />
    </div>
    <div v-else-if="data?.rows.length" class="space-y-3">
      <article v-for="c in data.rows" :key="c.name" class="card flex flex-wrap items-center gap-4 p-4 sm:p-5" :class="overdue(c) ? 'border-amber-300/30' : ''">
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2 text-xs">
            <span class="font-medium" :class="DIRECTION_TONES[c.direction]">{{ KIND_LABELS[c.kind] }} {{ DIRECTION_LABELS[c.direction] }}</span>
            <span :class="overdue(c) ? 'text-amber-300' : 'text-ink-400'">{{ dueLabel(c) }}</span>
            <span v-if="c.bank" class="text-ink-500">{{ c.bank }}</span>
            <span v-if="c.cheque_no" class="text-ink-500">ش {{ faDigits(c.cheque_no) }}</span>
          </div>
          <p class="mt-1.5 truncate font-bold text-bone">{{ c.party }}</p>
          <p v-if="c.note" class="mt-1 truncate text-xs text-ink-400">{{ c.note }}</p>
        </div>
        <p class="num text-xl font-black" :class="DIRECTION_TONES[c.direction]">{{ toman(c.amount) }} <span class="text-xs font-normal text-ink-400">تومان</span></p>
        <button v-if="!c.settled && c.status !== 'Cancelled' && c.kind === 'Regular'" class="btn-primary text-xs" @click="openSettlement(c)">ثبت تسویه و سند</button>
        <span v-if="c.settled" class="text-xs text-mint-400">سند {{ c.journal_entry }}</span>
        <span v-else-if="c.journal_entry" class="text-xs text-amber-300">سند قبلی لغو شده</span>
        <select v-if="!c.journal_entry"
          :value="c.status"
          class="h-9 rounded-full border-0 px-3 text-xs"
          :class="STATUS_TONES[c.status]"
          @change="setStatus(c, ($event.target as HTMLSelectElement).value as ChequeStatus)"
        >
          <option v-for="(label, value) in STATUS_LABELS" :key="value" :value="value" :disabled="value === 'Cleared' && c.status !== 'Cleared'" class="bg-ink-900 text-ink-100">{{ label }}</option>
        </select>
        <button v-if="!c.journal_entry && c.status !== 'Cleared'" class="rounded-lg p-2 text-ink-400 hover:bg-white/5 hover:text-one-400" title="ویرایش" @click="edit(c)"><Pencil class="size-4" /></button>
      </article>
    </div>
    <EmptyState v-else :icon="Receipt" title="چک پرداختی با این فیلتر نیست" text="چک پرداختی را از «چک جدید» ثبت کن." />

    <Modal v-model="editorOpen" :title="form.name ? 'ویرایش چک' : 'چک جدید'" width="max-w-2xl">
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">سند</span>
          <select v-model="form.kind" class="field">
            <option v-for="(label, value) in KIND_LABELS" :key="value" :value="value as ChequeKind">{{ label }}</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">در وجه</span>
          <input v-model="form.party" class="field" placeholder="نام شخص یا شرکت" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">مبلغ (تومان)</span>
          <input v-model.number="form.amountToman" type="number" min="0" class="field" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">تاریخ سررسید (شمسی){{ form.kind === 'Regular' ? '' : ' · اختیاری' }}</span>
          <input v-model="form.due" class="field" dir="ltr" placeholder="1405/08/15" :class="badDate(form.due) ? 'border-rose-400/60' : ''" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">تاریخ صدور (شمسی)</span>
          <input v-model="form.issued" class="field" dir="ltr" :class="badDate(form.issued) ? 'border-rose-400/60' : ''" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">بانک</span>
          <input v-model="form.bank" class="field" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">شماره چک</span>
          <input v-model="form.cheque_no" class="field" dir="ltr" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">شناسه صیادی</span>
          <input v-model="form.sayad_id" class="field" dir="ltr" inputmode="numeric" maxlength="16" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">وضعیت</span>
          <select v-model="form.status" class="field">
            <option v-for="(label, value) in STATUS_LABELS" :key="value" :value="value as ChequeStatus" :disabled="value === 'Cleared'">{{ label }}</option>
          </select>
        </label>
        <label class="block sm:col-span-2">
          <span class="mb-2 block text-sm text-ink-300">یادداشت</span>
          <input v-model="form.note" class="field" placeholder="بابت چه؟" />
        </label>
      </div>
      <template #footer>
        <button v-if="form.name" class="btn-ghost text-rose-300" @click="remove"><Trash2 class="size-4" /> حذف</button>
        <span class="flex-1" />
        <button class="btn-ghost" @click="editorOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || formInvalid" @click="save">
          <LoaderCircle v-if="saving" class="size-4 animate-spin" /> ذخیره
        </button>
      </template>
    </Modal>
    <Modal v-model="settlementOpen" title="ثبت تسویه چک و سند حسابداری" width="max-w-xl">
      <div class="space-y-4 text-sm">
        <p class="text-ink-300">{{ settlementCheque?.party }} · {{ toman(settlementCheque?.amount ?? 0) }} تومان</p>
        <label class="block"><span class="mb-2 block text-ink-300">حساب بانکی / صندوق پرداختی</span>
          <select v-model="bankAccount" class="field"><option value="">انتخاب حساب</option><option v-for="a in settlementAccounts.bank" :key="a.name" :value="a.name">{{ a.account_name }} · {{ a.name }}</option></select>
        </label>
        <label class="block"><span class="mb-2 block text-ink-300">حساب مقابل بدهکار</span>
          <select v-model="counterpartAccount" class="field"><option value="">انتخاب حساب</option><option v-for="a in settlementAccounts.counterpart" :key="a.name" :value="a.name">{{ a.account_name }} · {{ a.name }}</option></select>
        </label>
        <p class="text-xs leading-6 text-ink-400">با تأیید، مبلغ چک از حساب بانکی خارج و به حساب مقابل بدهکار می‌شود. حساب مقابل را طبق سند مبنای چک انتخاب کن.</p>
      </div>
      <template #footer><button class="btn-ghost" @click="settlementOpen = false">انصراف</button><button class="btn-primary" :disabled="settling || !bankAccount || !counterpartAccount" @click="settle">ثبت سند و تسویه</button></template>
    </Modal>
  </div>
</template>
