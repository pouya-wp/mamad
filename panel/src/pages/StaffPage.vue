<script setup lang="ts">
import { CalendarClock, LoaderCircle, Pencil, Phone, Plus, Trash2, UserPlus, UsersRound } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import { get, post } from '@/lib/api'
import { faDigits, faNumber, fromJalaliInput, jDate, toJalaliInput, toman, toRial, toToman } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { Contract, ContractState, Employee } from '@/lib/types'

const staff = ref<Employee[]>([])
const loading = ref(true)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    staff.value = await get<Employee[]>('cafe_app.api.staff.list_staff')
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const STATE: Record<ContractState, { label: string; tone: string }> = {
  active: { label: 'فعال', tone: 'bg-mint-400/10 text-mint-400' },
  expiring: { label: 'رو به پایان', tone: 'bg-amber-300/10 text-amber-300' },
  expired: { label: 'تمام شده', tone: 'bg-rose-400/10 text-rose-400' },
  upcoming: { label: 'شروع نشده', tone: 'bg-white/[0.06] text-ink-300' },
  open: { label: 'بدون تاریخ پایان', tone: 'bg-white/[0.06] text-ink-300' },
}

const active = computed(() => staff.value.filter((e) => e.status === 'Active'))
const payroll = computed(() => active.value.reduce((sum, e) => sum + (e.monthly_salary ?? 0), 0))
const expiring = computed(() =>
  staff.value.flatMap((e) => e.contracts.filter((c) => c.state === 'expiring' || c.state === 'expired').map((c) => ({ e, c }))),
)
const incomplete = computed(() =>
  staff.value.filter((e) => e.contracts.some((c) => !c.start_date || !c.end_date || !c.monthly_salary || !c.shift_start)),
)

const shift = (c: Contract) => (c.shift_start || c.shift_end ? faDigits(`${c.shift_start ?? '؟'} تا ${c.shift_end ?? '؟'}`) : 'نامشخص')
const dateOr = (d: string | null) => (d ? jDate(d) : 'نامشخص')

// ---- Editor ----
type ContractForm = Omit<Contract, 'monthly_salary' | 'start_date' | 'end_date' | 'sign_date'> & {
  salaryToman: number | null
  start: string
  end: string
  signed: string
}
type EmployeeForm = Omit<Employee, 'contracts' | 'birth_date'> & { birth: string; contracts: ContractForm[] }

const editorOpen = ref(false)
const form = ref<EmployeeForm>(blank())

function blankContract(): ContractForm {
  return { position: '', start: '', end: '', signed: '', shift_start: '', shift_end: '', working_days: '', salaryToman: null, payment_day: null, note: '' }
}

function blank(): EmployeeForm {
  return { full_name: '', national_id: '', phone: '', address: '', birth: '', status: 'Active', notes: '', contracts: [blankContract()] }
}

function edit(e?: Employee) {
  form.value = e
    ? {
        ...e,
        birth: toJalaliInput(e.birth_date),
        contracts: e.contracts.map((c) => ({
          ...c,
          salaryToman: c.monthly_salary ? toToman(c.monthly_salary) : null,
          start: toJalaliInput(c.start_date),
          end: toJalaliInput(c.end_date),
          signed: toJalaliInput(c.sign_date),
        })),
      }
    : blank()
  editorOpen.value = true
}

/** A Shamsi field that is filled in but not a valid date. */
const badDate = (text: string) => !!text.trim() && !fromJalaliInput(text)
const formInvalid = computed(
  () => !form.value.full_name.trim() || badDate(form.value.birth) || form.value.contracts.some((c) => badDate(c.start) || badDate(c.end) || badDate(c.signed)),
)

async function save() {
  saving.value = true
  try {
    const f = form.value
    await post('cafe_app.api.staff.save_employee', {
      data: {
        name: f.name,
        full_name: f.full_name,
        national_id: f.national_id,
        phone: f.phone,
        address: f.address,
        birth_date: fromJalaliInput(f.birth),
        status: f.status,
        notes: f.notes,
        contracts: f.contracts.map((c) => ({
          position: c.position,
          start_date: fromJalaliInput(c.start),
          end_date: fromJalaliInput(c.end),
          sign_date: fromJalaliInput(c.signed),
          shift_start: c.shift_start,
          shift_end: c.shift_end,
          working_days: c.working_days,
          monthly_salary: toRial(c.salaryToman ?? 0),
          payment_day: c.payment_day,
          note: c.note,
        })),
      },
    })
    toast('اطلاعات کارمند ذخیره شد')
    editorOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!form.value.name || !window.confirm(`${form.value.full_name} و قراردادهایش حذف شود؟`)) return
  try {
    await post('cafe_app.api.staff.delete_employee', { name: form.value.name })
    toast('کارمند حذف شد')
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
      <p class="text-sm text-ink-400">قراردادهای پرسنل ONE CAFE؛ تاریخ‌ها شمسی و مبالغ به تومان است.</p>
      <div class="flex-1" />
      <button class="btn-primary" @click="edit()"><UserPlus class="size-4" /> کارمند جدید</button>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <div class="card p-5">
        <p class="text-xs text-ink-400">پرسنل فعال</p>
        <p class="num mt-2 text-2xl font-black text-bone">{{ faNumber(active.length) }}</p>
      </div>
      <div class="card p-5">
        <p class="text-xs text-ink-400">جمع حقوق ماهانه قراردادهای جاری</p>
        <p class="num mt-2 text-2xl font-black text-bone">{{ toman(payroll) }} <span class="text-xs font-normal text-ink-400">تومان</span></p>
      </div>
      <div class="card p-5">
        <p class="text-xs text-ink-400">قرارداد تمام‌شده یا رو به پایان</p>
        <p class="num mt-2 text-2xl font-black" :class="expiring.length ? 'text-amber-300' : 'text-bone'">{{ faNumber(expiring.length) }}</p>
      </div>
      <div class="card p-5">
        <p class="text-xs text-ink-400">قرارداد با اطلاعات ناقص</p>
        <p class="num mt-2 text-2xl font-black" :class="incomplete.length ? 'text-amber-300' : 'text-bone'">{{ faNumber(incomplete.length) }}</p>
      </div>
    </div>

    <div v-if="loading && !staff.length" class="grid gap-4 lg:grid-cols-2">
      <div v-for="i in 4" :key="i" class="card h-48 animate-pulse" />
    </div>
    <div v-else-if="staff.length" class="grid gap-4 lg:grid-cols-2">
      <article v-for="e in staff" :key="e.name" class="card p-5" :class="e.status === 'Inactive' ? 'opacity-50' : ''">
        <div class="flex items-start gap-3">
          <div class="grid size-11 shrink-0 place-items-center rounded-full bg-one-500/15 font-bold text-one-400">{{ e.full_name.charAt(0) }}</div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-lg font-bold text-bone">{{ e.full_name }}</p>
            <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-400">
              <a v-if="e.phone" :href="`tel:${e.phone}`" class="flex items-center gap-1 hover:text-one-400"><Phone class="size-3" /> {{ faDigits(e.phone) }}</a>
              <span v-if="e.national_id">کد ملی {{ faDigits(e.national_id) }}</span>
              <span v-if="e.birth_date">تولد {{ jDate(e.birth_date) }}</span>
            </div>
          </div>
          <button class="rounded-lg p-2 text-ink-400 hover:bg-white/5 hover:text-one-400" title="ویرایش" @click="edit(e)"><Pencil class="size-4" /></button>
        </div>

        <div v-for="(c, index) in e.contracts" :key="c.name ?? index" class="mt-4 rounded-2xl bg-white/[0.03] p-4 text-sm">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-medium text-ink-100">{{ c.position || 'سمت نامشخص' }}</span>
            <span v-if="c.state" class="rounded-full px-2 py-0.5 text-xs" :class="STATE[c.state].tone">
              {{ STATE[c.state].label }}<template v-if="c.state === 'expiring' && c.days_left != null"> · {{ faNumber(c.days_left) }} روز</template>
            </span>
            <span class="flex-1" />
            <span class="num font-bold text-bone">{{ c.monthly_salary ? `${toman(c.monthly_salary)} تومان` : 'حقوق نامشخص' }}</span>
          </div>
          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
            <div><dt class="text-ink-500">شروع</dt><dd class="text-ink-200">{{ dateOr(c.start_date) }}</dd></div>
            <div><dt class="text-ink-500">پایان</dt><dd class="text-ink-200">{{ dateOr(c.end_date) }}</dd></div>
            <div><dt class="text-ink-500">ساعت کاری</dt><dd class="text-ink-200">{{ shift(c) }}</dd></div>
            <div><dt class="text-ink-500">روزهای کاری</dt><dd class="text-ink-200">{{ c.working_days || 'نامشخص' }}</dd></div>
            <div><dt class="text-ink-500">روز پرداخت</dt><dd class="text-ink-200">{{ c.payment_day ? `${faNumber(c.payment_day)} هر ماه` : 'نامشخص' }}</dd></div>
            <div><dt class="text-ink-500">امضا</dt><dd class="text-ink-200">{{ dateOr(c.sign_date) }}</dd></div>
          </dl>
          <p v-if="c.note" class="mt-3 text-[11px] leading-5" :class="c.note.startsWith('فرضی') ? 'text-amber-200/80' : 'text-ink-400'">{{ c.note }}</p>
        </div>
        <p v-if="!e.contracts.length" class="mt-4 text-sm text-ink-400">قراردادی ثبت نشده</p>
      </article>
    </div>
    <EmptyState v-else :icon="UsersRound" title="هنوز کارمندی ثبت نشده" />

    <Modal v-model="editorOpen" :title="form.name ? 'ویرایش کارمند' : 'کارمند جدید'" width="max-w-3xl">
      <div class="space-y-6">
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">نام و نام خانوادگی</span>
            <input v-model="form.full_name" class="field" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">موبایل</span>
            <input v-model="form.phone" class="field" dir="ltr" inputmode="tel" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">کد ملی</span>
            <input v-model="form.national_id" class="field" dir="ltr" inputmode="numeric" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">تاریخ تولد (شمسی)</span>
            <input v-model="form.birth" class="field" dir="ltr" placeholder="1384/06/22" :class="badDate(form.birth) ? 'border-rose-400/60' : ''" />
          </label>
          <label class="block sm:col-span-2">
            <span class="mb-2 block text-sm text-ink-300">آدرس</span>
            <input v-model="form.address" class="field" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">وضعیت</span>
            <select v-model="form.status" class="field">
              <option value="Active">مشغول به کار</option>
              <option value="Inactive">قطع همکاری</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">یادداشت</span>
            <input v-model="form.notes" class="field" />
          </label>
        </div>

        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="flex items-center gap-2 font-bold text-bone"><CalendarClock class="size-4 text-one-500" /> قراردادها</p>
            <button class="btn-ghost h-8 px-3 text-xs" @click="form.contracts.push(blankContract())"><Plus class="size-3.5" /> قرارداد</button>
          </div>
          <div v-for="(c, index) in form.contracts" :key="index" class="grid gap-3 rounded-2xl border border-white/[0.06] p-4 sm:grid-cols-3">
            <label class="block sm:col-span-2">
              <span class="mb-1.5 block text-xs text-ink-400">سمت</span>
              <input v-model="c.position" class="field h-10" />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs text-ink-400">حقوق ماهانه (تومان)</span>
              <input v-model.number="c.salaryToman" type="number" min="0" class="field h-10" />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs text-ink-400">شروع (شمسی)</span>
              <input v-model="c.start" class="field h-10" dir="ltr" placeholder="1405/06/23" :class="badDate(c.start) ? 'border-rose-400/60' : ''" />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs text-ink-400">پایان (شمسی)</span>
              <input v-model="c.end" class="field h-10" dir="ltr" placeholder="1405/12/23" :class="badDate(c.end) ? 'border-rose-400/60' : ''" />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs text-ink-400">تاریخ امضا (شمسی)</span>
              <input v-model="c.signed" class="field h-10" dir="ltr" :class="badDate(c.signed) ? 'border-rose-400/60' : ''" />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs text-ink-400">شروع شیفت</span>
              <input v-model="c.shift_start" class="field h-10" dir="ltr" placeholder="16:00" />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs text-ink-400">پایان شیفت</span>
              <input v-model="c.shift_end" class="field h-10" dir="ltr" placeholder="23:45" />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs text-ink-400">روز پرداخت حقوق</span>
              <input v-model.number="c.payment_day" type="number" min="1" max="31" class="field h-10" />
            </label>
            <label class="block sm:col-span-2">
              <span class="mb-1.5 block text-xs text-ink-400">روزهای کاری</span>
              <input v-model="c.working_days" class="field h-10" />
            </label>
            <label class="block sm:col-span-2">
              <span class="mb-1.5 block text-xs text-ink-400">یادداشت</span>
              <input v-model="c.note" class="field h-10" />
            </label>
            <div class="flex items-end justify-end">
              <button class="btn-ghost h-10 text-xs text-rose-300" @click="form.contracts.splice(index, 1)"><Trash2 class="size-3.5" /> حذف قرارداد</button>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <button v-if="form.name" class="btn-ghost text-rose-300" @click="remove"><Trash2 class="size-4" /> حذف کارمند</button>
        <span class="flex-1" />
        <button class="btn-ghost" @click="editorOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || formInvalid" @click="save">
          <LoaderCircle v-if="saving" class="size-4 animate-spin" /> ذخیره
        </button>
      </template>
    </Modal>
  </div>
</template>
