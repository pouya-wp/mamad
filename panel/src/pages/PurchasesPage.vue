<script setup lang="ts">
import { LoaderCircle, Plus, ShoppingCart, Trash2, Truck, UserPlus } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import Panel from '@/components/Panel.vue'
import { get, post } from '@/lib/api'
import { faNumber, jDate, paymentLabel, toman, toRial, uom } from '@/lib/format'
import { toast, toastError } from '@/lib/toast'
import type { Ingredient, Purchase, Supplier } from '@/lib/types'

const purchases = ref<Purchase[]>([])
const suppliers = ref<Supplier[]>([])
const ingredients = ref<Ingredient[]>([])
const loading = ref(true)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    ;[purchases.value, suppliers.value, ingredients.value] = await Promise.all([
      get<Purchase[]>('cafe_app.api.inventory.list_purchases'),
      get<Supplier[]>('cafe_app.api.inventory.list_suppliers'),
      get<Ingredient[]>('cafe_app.api.menu.list_ingredients'),
    ])
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const byCode = computed(() => new Map(ingredients.value.map((i) => [i.item_code, i])))
const supplierMax = computed(() => Math.max(1, ...suppliers.value.map((s) => s.total_purchases)))

// ---- New purchase ----
type Line = { item_code: string; qty: number | null; priceToman: number | null }
const purchaseOpen = ref(false)
const supplier = ref('')
const billNo = ref('')
const payment = ref<'Cash' | 'Credit Card' | ''>('Credit Card')
const lines = ref<Line[]>([])

function openPurchase() {
  supplier.value = suppliers.value[0]?.name ?? ''
  billNo.value = ''
  payment.value = 'Credit Card'
  lines.value = [{ item_code: '', qty: null, priceToman: null }]
  purchaseOpen.value = true
}

function pickItem(line: Line) {
  const item = byCode.value.get(line.item_code)
  if (item && !line.priceToman) line.priceToman = item.valuation_rate / 10
}

const lineTotal = (l: Line) => toRial((l.qty ?? 0) * (l.priceToman ?? 0))
const purchaseTotal = computed(() => lines.value.reduce((sum, l) => sum + lineTotal(l), 0))

async function savePurchase() {
  saving.value = true
  try {
    await post('cafe_app.api.inventory.record_purchase', {
      supplier: supplier.value,
      items: lines.value
        .filter((l) => l.item_code && l.qty)
        .map((l) => ({ item_code: l.item_code, qty: l.qty, rate: toRial(l.priceToman ?? 0) })),
      mode_of_payment: payment.value || null,
      bill_no: billNo.value || null,
    })
    toast('خرید ثبت شد و موجودی انبار به‌روز شد')
    purchaseOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}

// ---- Supplier ----
const supplierOpen = ref(false)
const supplierName = ref('')
const supplierMobile = ref('')

async function saveSupplier() {
  saving.value = true
  try {
    await post('cafe_app.api.inventory.save_supplier', { supplier_name: supplierName.value.trim(), mobile_no: supplierMobile.value || null })
    toast('تأمین‌کننده اضافه شد')
    supplierOpen.value = false
    supplierName.value = ''
    supplierMobile.value = ''
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
    <div class="flex flex-wrap items-center gap-3">
      <p class="text-sm text-ink-400">هر خرید، هم موجودی انبار را زیاد می‌کند و هم پرداخت به تأمین‌کننده را در حسابداری ثبت می‌کند.</p>
      <div class="flex-1" />
      <button class="btn-ghost" @click="supplierOpen = true"><UserPlus class="size-4" /> تأمین‌کننده</button>
      <button class="btn-primary" :disabled="!suppliers.length" @click="openPurchase"><Plus class="size-4" /> خرید جدید</button>
    </div>

    <div class="grid gap-6 xl:grid-cols-3">
      <div class="card overflow-hidden xl:col-span-2">
        <div class="overflow-x-auto">
          <table class="w-full min-w-[600px] text-sm">
            <thead>
              <tr class="border-b border-white/[0.06] text-right text-xs text-ink-400">
                <th class="px-6 py-4 font-medium">تأمین‌کننده</th>
                <th class="px-4 py-4 font-medium">تاریخ</th>
                <th class="px-4 py-4 font-medium">شماره فاکتور</th>
                <th class="px-4 py-4 font-medium">وضعیت</th>
                <th class="px-6 py-4 text-left font-medium">مبلغ (تومان)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04]">
              <tr v-for="p in purchases" :key="p.name">
                <td class="px-6 py-3.5 font-medium text-ink-100">{{ p.supplier }}</td>
                <td class="px-4 py-3.5 text-ink-300">{{ jDate(p.posting_date) }}</td>
                <td class="px-4 py-3.5 text-ink-400" dir="ltr">{{ p.bill_no || '—' }}</td>
                <td class="px-4 py-3.5">
                  <span v-if="p.is_paid || !p.outstanding_amount" class="rounded-full bg-mint-400/10 px-2.5 py-1 text-xs text-mint-400">پرداخت شده</span>
                  <span v-else class="rounded-full bg-amber-300/10 px-2.5 py-1 text-xs text-amber-300">نسیه · {{ toman(p.outstanding_amount) }}</span>
                </td>
                <td class="num px-6 py-3.5 text-left font-bold text-bone">{{ toman(p.base_grand_total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-if="!loading && !purchases.length" :icon="ShoppingCart" title="هنوز خریدی ثبت نشده" />
        <div v-if="loading" class="flex justify-center py-6"><LoaderCircle class="size-5 animate-spin text-ink-400" /></div>
      </div>

      <Panel title="تأمین‌کنندگان" subtitle="بر اساس مجموع خرید">
        <ul v-if="suppliers.length" class="space-y-4">
          <li v-for="s in suppliers" :key="s.name">
            <div class="flex items-center gap-3 text-sm">
              <div class="grid size-9 place-items-center rounded-xl bg-white/[0.04] text-ink-300"><Truck class="size-4" /></div>
              <div class="min-w-0 flex-1">
                <p class="truncate text-ink-100">{{ s.supplier_name }}</p>
                <p class="text-xs text-ink-500" dir="ltr">{{ s.mobile_no }}</p>
              </div>
              <span class="num text-ink-200">{{ toman(s.total_purchases) }}</span>
            </div>
            <div class="mt-2 mr-12 h-1 overflow-hidden rounded-full bg-white/[0.05]">
              <div class="h-full rounded-full bg-one-500/70" :style="{ width: `${(s.total_purchases / supplierMax) * 100}%` }" />
            </div>
          </li>
        </ul>
        <EmptyState v-else :icon="Truck" title="تأمین‌کننده‌ای نیست" text="اول یک تأمین‌کننده اضافه کن." />
      </Panel>
    </div>

    <!-- Purchase modal -->
    <Modal v-model="purchaseOpen" title="خرید جدید" width="max-w-3xl">
      <div class="space-y-5">
        <div class="grid gap-4 sm:grid-cols-3">
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">تأمین‌کننده</span>
            <select v-model="supplier" class="field">
              <option v-for="s in suppliers" :key="s.name" :value="s.name">{{ s.supplier_name }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">پرداخت</span>
            <select v-model="payment" class="field">
              <option value="Credit Card">{{ paymentLabel('Credit Card') }}</option>
              <option value="Cash">{{ paymentLabel('Cash') }}</option>
              <option value="">نسیه</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">شماره فاکتور</span>
            <input v-model="billNo" class="field" dir="ltr" />
          </label>
        </div>

        <div class="space-y-2">
          <div class="grid grid-cols-[1fr_110px_140px_120px_auto] gap-2 px-1 text-xs text-ink-400">
            <span>کالا</span><span>مقدار</span><span>قیمت واحد (تومان)</span><span>جمع</span><span class="w-10" />
          </div>
          <div v-for="(line, index) in lines" :key="index" class="grid grid-cols-[1fr_110px_140px_120px_auto] items-center gap-2">
            <select v-model="line.item_code" class="field h-10" @change="pickItem(line)">
              <option value="" disabled>انتخاب</option>
              <option v-for="i in ingredients" :key="i.item_code" :value="i.item_code">{{ i.item_name }}</option>
            </select>
            <div class="relative">
              <input v-model.number="line.qty" type="number" min="0" step="any" class="field h-10 pl-12" />
              <span class="absolute inset-y-0 left-2.5 grid place-items-center text-[11px] text-ink-400">{{ uom(byCode.get(line.item_code)?.stock_uom) }}</span>
            </div>
            <input v-model.number="line.priceToman" type="number" min="0" step="any" class="field h-10" />
            <span class="num text-sm text-ink-200">{{ toman(lineTotal(line)) }}</span>
            <button class="grid size-10 place-items-center rounded-xl text-ink-400 hover:text-rose-400" @click="lines.splice(index, 1)"><Trash2 class="size-4" /></button>
          </div>
          <button class="btn-ghost h-9 text-xs" @click="lines.push({ item_code: '', qty: null, priceToman: null })"><Plus class="size-3.5" /> قلم دیگر</button>
        </div>

        <div class="flex items-baseline justify-between rounded-2xl bg-white/[0.03] px-5 py-4">
          <span class="text-ink-300">جمع خرید · {{ faNumber(lines.filter((l) => l.item_code).length) }} قلم</span>
          <span class="num text-2xl font-black text-bone">{{ toman(purchaseTotal) }} <span class="text-sm font-normal text-ink-400">تومان</span></span>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="purchaseOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || !supplier || !purchaseTotal" @click="savePurchase">
          <LoaderCircle v-if="saving" class="size-4 animate-spin" /> ثبت خرید
        </button>
      </template>
    </Modal>

    <!-- Supplier modal -->
    <Modal v-model="supplierOpen" title="تأمین‌کننده جدید">
      <div class="space-y-4">
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">نام</span>
          <input v-model="supplierName" class="field" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">موبایل</span>
          <input v-model="supplierMobile" class="field" dir="ltr" inputmode="tel" />
        </label>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="supplierOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || !supplierName.trim()" @click="saveSupplier">ذخیره</button>
      </template>
    </Modal>
  </div>
</template>
