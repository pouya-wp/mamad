<script setup lang="ts">
import {
  ArrowRight,
  Banknote,
  Check,
  CreditCard,
  LoaderCircle,
  Minus,
  Plus,
  Search,
  ShoppingBag,
  Split,
  Trash2,
  X,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import AnimatedNumber from '@/components/AnimatedNumber.vue'
import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import OneLogo from '@/components/OneLogo.vue'
import Segmented from '@/components/Segmented.vue'
import { get, post } from '@/lib/api'
import { faNumber, jDateTime, toman, toRial, toToman } from '@/lib/format'
import { sound, vibrate } from '@/lib/sound'
import { toast, toastError } from '@/lib/toast'
import type { PosItem, PosMenu, Shift } from '@/lib/types'

type OrderType = 'سالن' | 'بیرون‌بر' | 'پیک'
type Line = { item_code: string; item_name: string; rate: number; qty: number }

const menu = ref<PosMenu | null>(null)
const shift = ref<Shift | null>(null)
const loading = ref(true)
const search = ref('')
const group = ref('همه')

const cart = ref<Line[]>([])
const orderType = ref<OrderType>('سالن')
const tableNo = ref('')
const discountToman = ref<number | null>(null)
const note = ref('')
const busy = ref(false)
const lastOrder = ref<{ name: string; total: number } | null>(null)
const celebrate = ref(false)
const sparkles = Array.from({ length: 14 }, (_, i) => {
  const angle = (Math.PI * 2 * i) / 14
  return { dx: `${Math.cos(angle) * 120}px`, dy: `${Math.sin(angle) * 120}px`, accent: i % 2 === 0 }
})

const splitOpen = ref(false)
const splitCashToman = ref<number | null>(null)
const shiftOpen = ref(false)
const shiftCashToman = ref<number | null>(null)
const shiftNote = ref('')

const orderTypes: { value: OrderType; label: string }[] = [
  { value: 'سالن', label: 'سالن' },
  { value: 'بیرون‌بر', label: 'بیرون‌بر' },
  { value: 'پیک', label: 'پیک' },
]

const items = computed(() => {
  const q = search.value.trim()
  return (menu.value?.items ?? []).filter(
    (i) => (group.value === 'همه' || i.item_group === group.value) && (!q || i.item_name.includes(q)),
  )
})

const qtyOf = (code: string) => cart.value.find((l) => l.item_code === code)?.qty ?? 0
const subtotal = computed(() => cart.value.reduce((sum, l) => sum + l.rate * l.qty, 0))
const discount = computed(() => Math.min(toRial(discountToman.value ?? 0), subtotal.value))
const total = computed(() => subtotal.value - discount.value)
const count = computed(() => cart.value.reduce((sum, l) => sum + l.qty, 0))
const splitCard = computed(() => Math.max(0, total.value - toRial(splitCashToman.value ?? 0)))

const tileTone = ['from-one-500/25', 'from-bone/15', 'from-one-300/20', 'from-ink-400/25']
const toneOf = (item: PosItem) => tileTone[(menu.value?.groups.indexOf(item.item_group) ?? 0) % tileTone.length]

function add(item: PosItem) {
  sound.add(qtyOf(item.item_code) + 1)
  vibrate()
  const line = cart.value.find((l) => l.item_code === item.item_code)
  if (line) line.qty++
  else cart.value.push({ item_code: item.item_code, item_name: item.item_name, rate: item.rate, qty: 1 })
}

function change(line: Line, by: number) {
  if (by > 0) sound.add(line.qty + 1)
  else sound.remove()
  line.qty += by
  if (line.qty <= 0) cart.value = cart.value.filter((l) => l !== line)
}

function reset() {
  cart.value = []
  tableNo.value = ''
  discountToman.value = null
  note.value = ''
  splitCashToman.value = null
}

async function load() {
  loading.value = true
  try {
    ;[menu.value, shift.value] = await Promise.all([
      get<PosMenu>('cafe_app.api.pos.get_menu'),
      get<Shift | null>('cafe_app.api.pos.current_shift'),
    ])
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}

async function checkout(payments: { mode_of_payment: string; amount?: number }[]) {
  if (!shift.value) {
    shiftOpen.value = true
    toast('اول شیفت را باز کن', 'info')
    return
  }
  busy.value = true
  try {
    const result = await post<{ name: string; grand_total: number }>('cafe_app.api.pos.create_order', {
      items: cart.value.map(({ item_code, qty }) => ({ item_code, qty })),
      payments,
      order_type: orderType.value,
      table_no: tableNo.value || null,
      discount_amount: discount.value,
      note: note.value || null,
    })
    lastOrder.value = { name: result.name, total: result.grand_total }
    celebrate.value = true
    sound.register()
    setTimeout(() => (celebrate.value = false), 1500)
    toast(`سفارش ${result.name} ثبت شد`, 'success', 3800, false)
    splitOpen.value = false
    reset()
    shift.value = await get<Shift | null>('cafe_app.api.pos.current_shift')
  } catch (error) {
    toastError(error)
  } finally {
    busy.value = false
  }
}

async function submitShift() {
  busy.value = true
  try {
    if (shift.value) {
      await post('cafe_app.api.pos.close_shift', { closing_cash: toRial(shiftCashToman.value ?? 0), note: shiftNote.value || null })
      shift.value = null
      toast('شیفت بسته شد', 'success', 3800, false)
      sound.shiftClose()
    } else {
      shift.value = await post<Shift>('cafe_app.api.pos.open_shift', { opening_cash: toRial(shiftCashToman.value ?? 0) })
      toast('شیفت باز شد، فروش خوبی داشته باشی!', 'success', 3800, false)
      sound.shiftOpen()
    }
    shiftOpen.value = false
    shiftCashToman.value = null
    shiftNote.value = ''
  } catch (error) {
    toastError(error)
  } finally {
    busy.value = false
  }
}

async function openShiftModal() {
  if (shift.value) shift.value = await get<Shift | null>('cafe_app.api.pos.current_shift').catch(() => shift.value)
  shiftOpen.value = true
}

onMounted(load)
</script>

<template>
  <div class="flex h-dvh flex-col bg-ink-950">
    <!-- Top bar -->
    <header class="flex h-16 shrink-0 items-center gap-4 border-b border-white/[0.06] px-4 sm:px-6">
      <RouterLink to="/" class="flex items-center gap-2 rounded-xl px-2 py-1.5 text-ink-300 hover:bg-white/5 hover:text-ink-100">
        <ArrowRight class="size-4" />
        <span class="hidden text-sm sm:inline">پنل</span>
      </RouterLink>
      <div class="text-bone"><OneLogo :size="26" /></div>
      <p class="label-caps hidden md:block">صندوق</p>
      <div class="flex-1" />
      <button
        class="flex items-center gap-2.5 rounded-xl border px-3.5 py-2 text-sm transition"
        :class="shift ? 'border-mint-400/25 bg-mint-400/[0.06] text-mint-400' : 'border-one-500/40 bg-one-500/10 text-one-400'"
        @click="openShiftModal"
      >
        <span class="relative flex size-2">
          <span v-if="shift" class="absolute inline-flex size-full animate-ping rounded-full bg-mint-400 opacity-60" />
          <span class="relative inline-flex size-2 rounded-full" :class="shift ? 'bg-mint-400' : 'bg-one-500'" />
        </span>
        <template v-if="shift">شیفت باز · {{ faNumber(shift.orders_count) }} سفارش</template>
        <template v-else>باز کردن شیفت</template>
      </button>
    </header>

    <div class="grid min-h-0 flex-1 lg:grid-cols-[1fr_400px]">
      <!-- Menu -->
      <section class="flex min-h-0 flex-col">
        <div class="space-y-4 px-4 pt-5 sm:px-6">
          <div class="relative">
            <Search class="pointer-events-none absolute top-1/2 right-4 size-4 -translate-y-1/2 text-ink-400" />
            <input v-model="search" class="field h-12 pr-11" placeholder="جستجوی آیتم منو…" />
          </div>
          <div class="-mx-1 flex gap-2 overflow-x-auto pb-1">
            <button
              v-for="g in ['همه', ...(menu?.groups ?? [])]"
              :key="g"
              data-ripple
              class="shrink-0 rounded-full border px-4 py-2 text-sm transition"
              :class="group === g ? 'border-bone bg-bone font-medium text-ink-950' : 'border-white/10 text-ink-300 hover:border-white/25 hover:text-ink-100'"
              @click="group = g"
            >
              {{ g }}
            </button>
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
          <div v-if="loading" class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
            <div v-for="i in 12" :key="i" class="card h-32 animate-pulse" />
          </div>
          <div v-else-if="items.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
            <button
              v-for="item in items"
              :key="item.item_code"
              data-ripple
              data-tilt="7"
              data-sfx="none"
              class="group card relative flex h-32 flex-col justify-between overflow-hidden bg-gradient-to-bl via-ink-850 to-ink-850 p-4 text-right transition hover:-translate-y-0.5 hover:border-white/15 active:scale-[0.98]"
              :class="[toneOf(item), qtyOf(item.item_code) ? 'border-one-500/50' : '']"
              @click="add(item)"
            >
              <span
                v-if="qtyOf(item.item_code)"
                class="num absolute top-3 left-3 grid size-7 place-items-center rounded-full bg-one-500 text-xs font-bold text-white shadow-lg shadow-one-500/40"
              >
                {{ faNumber(qtyOf(item.item_code)) }}
              </span>
              <span class="text-[11px] text-ink-400">{{ item.item_group }}</span>
              <div>
                <p data-depth class="font-bold leading-6 text-bone">{{ item.item_name }}</p>
                <p class="num mt-1 text-sm text-ink-300">{{ toman(item.rate) }} <span class="text-[11px] text-ink-500">تومان</span></p>
              </div>
            </button>
          </div>
          <EmptyState v-else :icon="Search" title="آیتمی پیدا نشد" text="منو را از بخش «منو و رسپی» کامل کن." />
        </div>
      </section>

      <!-- Cart -->
      <aside class="flex min-h-0 flex-col border-t border-white/[0.06] bg-ink-900 lg:border-t-0 lg:border-r">
        <div class="space-y-3 border-b border-white/[0.06] p-5">
          <div class="flex items-center justify-between">
            <h2 class="font-bold text-bone">سفارش جدید</h2>
            <button v-if="cart.length" data-sfx="clear" class="flex items-center gap-1 text-xs text-ink-400 hover:text-rose-400" @click="reset">
              <Trash2 class="size-3.5" /> پاک کردن
            </button>
          </div>
          <div class="flex items-center gap-2">
            <Segmented v-model="orderType" :options="orderTypes" />
            <input v-if="orderType === 'سالن'" v-model="tableNo" class="field h-10 w-24 text-center" placeholder="میز" inputmode="numeric" />
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-5">
          <TransitionGroup
            v-if="cart.length"
            tag="ul"
            class="divide-y divide-white/[0.05]"
            enter-from-class="opacity-0 translate-x-6"
            leave-to-class="opacity-0 -translate-x-6"
            enter-active-class="transition duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
            leave-active-class="transition duration-200"
          >
            <li v-for="line in cart" :key="line.item_code" class="flex items-center gap-3 py-3.5">
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-ink-100">{{ line.item_name }}</p>
                <p class="num mt-0.5 text-xs text-ink-400">{{ toman(line.rate * line.qty) }} تومان</p>
              </div>
              <div class="flex items-center gap-1 rounded-xl border border-white/10 bg-ink-850 p-1">
                <button data-sfx="none" class="grid size-7 place-items-center rounded-lg text-ink-300 hover:bg-white/5 hover:text-ink-100" @click="change(line, 1)">
                  <Plus class="size-3.5" />
                </button>
                <span class="num w-6 text-center text-sm font-bold text-bone">{{ faNumber(line.qty) }}</span>
                <button data-sfx="none" class="grid size-7 place-items-center rounded-lg text-ink-300 hover:bg-white/5 hover:text-rose-400" @click="change(line, -1)">
                  <Minus class="size-3.5" />
                </button>
              </div>
            </li>
          </TransitionGroup>
          <EmptyState v-else :icon="ShoppingBag" title="سبد خالیه" text="آیتم‌های منو را لمس کن تا به سفارش اضافه شوند.">
            <p v-if="lastOrder" class="mt-2 rounded-full bg-white/[0.04] px-3 py-1 text-xs text-ink-300">
              آخرین سفارش: {{ lastOrder.name }} · {{ toman(lastOrder.total) }} تومان
            </p>
          </EmptyState>
        </div>

        <div class="space-y-4 border-t border-white/[0.06] p-5">
          <div class="grid grid-cols-2 gap-2">
            <input v-model.number="discountToman" type="number" min="0" class="field h-10" placeholder="تخفیف (تومان)" />
            <input v-model="note" class="field h-10" placeholder="یادداشت" />
          </div>
          <div class="space-y-1.5 text-sm">
            <div class="flex justify-between text-ink-400">
              <span>{{ faNumber(count) }} قلم</span>
              <span class="num">{{ toman(subtotal) }}</span>
            </div>
            <div v-if="discount" class="flex justify-between text-one-400">
              <span>تخفیف</span>
              <span class="num">− {{ toman(discount) }}</span>
            </div>
            <div class="flex items-baseline justify-between pt-1">
              <span class="text-ink-200">مبلغ قابل پرداخت</span>
              <span class="text-3xl font-black text-bone"><AnimatedNumber :value="total" :format="toman" :duration="450" /> <span class="text-sm font-normal text-ink-400">تومان</span></span>
            </div>
          </div>
          <div class="grid grid-cols-[1fr_1fr_auto] gap-2">
            <button class="btn-primary h-13 text-base" :disabled="!cart.length || busy" @click="checkout([{ mode_of_payment: 'Credit Card' }])">
              <LoaderCircle v-if="busy" class="size-5 animate-spin" />
              <template v-else><CreditCard class="size-5" /> کارتخوان</template>
            </button>
            <button class="btn-ghost h-13 text-base" :disabled="!cart.length || busy" @click="checkout([{ mode_of_payment: 'Cash' }])">
              <Banknote class="size-5" /> نقدی
            </button>
            <button class="btn-ghost h-13 w-13 px-0" title="پرداخت ترکیبی" :disabled="!cart.length || busy" @click="splitOpen = true">
              <Split class="size-5" />
            </button>
          </div>
        </div>
      </aside>
    </div>

    <!-- Order registered -->
    <Transition leave-active-class="transition duration-300" leave-to-class="opacity-0">
      <div v-if="celebrate" class="pointer-events-none fixed inset-0 z-[90] grid place-items-center bg-black/40 backdrop-blur-[2px]">
        <div class="relative grid place-items-center">
          <span class="celebrate-ring absolute size-28 rounded-full border-2 border-one-500" />
          <span class="celebrate-ring absolute size-28 rounded-full border border-bone/60 [animation-delay:120ms]" />
          <span
            v-for="(s, i) in sparkles"
            :key="i"
            class="ripple-sparkle"
            :class="{ 'is-accent': s.accent }"
            :style="{ width: '6px', height: '6px', '--dx': s.dx, '--dy': s.dy, animationDuration: '0.9s', animationDelay: `${i * 12}ms` }"
          />
          <div class="celebrate-check grid size-24 place-items-center rounded-full bg-one-500 text-white shadow-[0_0_60px_-4px_rgba(255,79,26,0.9)]">
            <Check class="size-12" :stroke-width="3" />
          </div>
          <p class="celebrate-check absolute top-32 whitespace-nowrap text-lg font-bold text-bone [animation-delay:120ms]">سفارش ثبت شد</p>
        </div>
      </div>
    </Transition>

    <!-- Split payment -->
    <Modal v-model="splitOpen" title="پرداخت ترکیبی">
      <div class="space-y-5">
        <div class="flex items-baseline justify-between rounded-2xl bg-white/[0.03] px-4 py-3">
          <span class="text-sm text-ink-300">جمع سفارش</span>
          <span class="num text-xl font-bold text-bone">{{ toman(total) }} تومان</span>
        </div>
        <label class="block">
          <span class="mb-2 flex items-center gap-2 text-sm text-ink-300"><Banknote class="size-4" /> مبلغ نقدی (تومان)</span>
          <input v-model.number="splitCashToman" type="number" min="0" :max="toToman(total)" class="field h-12 text-lg" />
        </label>
        <div class="flex items-center justify-between rounded-2xl border border-white/10 px-4 py-3">
          <span class="flex items-center gap-2 text-sm text-ink-300"><CreditCard class="size-4" /> باقی با کارتخوان</span>
          <span class="num font-bold text-one-400">{{ toman(splitCard) }} تومان</span>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="splitOpen = false">انصراف</button>
        <button
          class="btn-primary"
          :disabled="busy || !splitCashToman"
          @click="checkout([{ mode_of_payment: 'Cash', amount: toRial(splitCashToman ?? 0) }, { mode_of_payment: 'Credit Card' }])"
        >
          ثبت سفارش
        </button>
      </template>
    </Modal>

    <!-- Shift -->
    <Modal v-model="shiftOpen" :title="shift ? 'بستن شیفت' : 'باز کردن شیفت'">
      <div class="space-y-5">
        <template v-if="shift">
          <p class="text-sm text-ink-400">شروع شیفت: {{ jDateTime(shift.opening_time) }}</p>
          <div class="grid grid-cols-2 gap-3">
            <div class="rounded-2xl bg-white/[0.03] p-4">
              <p class="text-xs text-ink-400">فروش کل</p>
              <p class="num mt-1 font-bold text-bone">{{ toman(shift.total_sales) }}</p>
            </div>
            <div class="rounded-2xl bg-white/[0.03] p-4">
              <p class="text-xs text-ink-400">تعداد سفارش</p>
              <p class="num mt-1 font-bold text-bone">{{ faNumber(shift.orders_count) }}</p>
            </div>
            <div class="rounded-2xl bg-white/[0.03] p-4">
              <p class="text-xs text-ink-400">فروش کارتخوان</p>
              <p class="num mt-1 font-bold text-bone">{{ toman(shift.card_sales) }}</p>
            </div>
            <div class="rounded-2xl border border-one-500/30 bg-one-500/[0.07] p-4">
              <p class="text-xs text-one-300">نقد مورد انتظار در صندوق</p>
              <p class="num mt-1 font-bold text-bone">{{ toman(shift.expected_cash) }}</p>
            </div>
          </div>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">نقد شمارش‌شده در صندوق (تومان)</span>
            <input v-model.number="shiftCashToman" type="number" min="0" class="field h-12 text-lg" />
          </label>
          <p v-if="shiftCashToman !== null" class="text-sm" :class="toRial(shiftCashToman) - shift.expected_cash === 0 ? 'text-mint-400' : 'text-amber-300'">
            مغایرت: {{ toman(toRial(shiftCashToman) - shift.expected_cash) }} تومان
          </p>
          <input v-model="shiftNote" class="field" placeholder="توضیحات (اختیاری)" />
        </template>
        <label v-else class="block">
          <span class="mb-2 block text-sm text-ink-300">موجودی نقد اول شیفت (تومان)</span>
          <input v-model.number="shiftCashToman" type="number" min="0" class="field h-12 text-lg" placeholder="۰" />
        </label>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="shiftOpen = false"><X class="size-4" /> انصراف</button>
        <button class="btn-primary" :disabled="busy || (!!shift && shiftCashToman === null)" @click="submitShift">
          {{ shift ? 'بستن شیفت' : 'شروع شیفت' }}
        </button>
      </template>
    </Modal>
  </div>
</template>
