<script setup lang="ts">
import type { OrderTotals } from '@/lib/types'
import { faNumber, jDateTime, jShortDate, toman } from '@/lib/format'
import SourcePaymentStatus from './SourcePaymentStatus.vue'
import { computed, ref } from 'vue'

const props = defineProps<{ report: NonNullable<OrderTotals['credit_report']> }>()
const expanded = ref(false)
const visibleCustomers = computed(() => expanded.value ? props.report.customers : props.report.customers.slice(0, 5))
defineEmits<{ open: [name: string] }>()
</script>

<template>
  <section class="overflow-hidden rounded-2xl border border-white/[0.06]">
    <div class="space-y-2 border-b border-white/[0.06] p-5">
      <h2 class="text-base font-bold text-bone">نسیهٔ مشتریان · {{ faNumber(report.customers.length) }} نفر</h2>
      <p class="text-sm text-ink-300">ماندهٔ بدهکارِ حساب‌های تأییدشده: <b class="num text-amber-300">{{ toman(report.account_debt) }}</b> تومان</p>
      <p class="text-xs leading-6 text-ink-400">نسیهٔ فاکتورها مربوط به همین انتخاب است. ماندهٔ حساب، کل حساب مشتری در سپهریار است و می‌تواند شامل بدهی‌های قبل از این بازه باشد؛ هر حساب فقط یک‌بار جمع می‌شود. برای دیدن فاکتورها نام مشتری را باز کنید.</p>
      <p v-if="report.unverified_customers" class="text-xs text-amber-300">حساب {{ faNumber(report.unverified_customers) }} مشتری هنوز تأیید نشده و در جمع ماندهٔ حساب‌ها نیامده است.</p>
    </div>
    <div v-for="(customer, index) in visibleCustomers" :key="customer.customer_id || index" class="border-b border-white/[0.05] last:border-0">
      <details>
        <summary class="grid cursor-pointer gap-3 p-5 text-sm sm:grid-cols-3">
          <div><b class="text-bone">{{ customer.customer_name || 'نام مشتری در منبع مشخص نیست' }}</b><span class="mr-2 text-xs text-ink-500">کد {{ faNumber(customer.customer_id || 0) }}</span><p class="mt-1 text-xs text-ink-400">{{ faNumber(customer.invoices.length) }} فاکتور نسیه در این انتخاب</p></div>
          <div class="text-ink-400">نسیهٔ ثبت‌شدهٔ فاکتورها<p class="num mt-1 font-bold text-ink-200">{{ toman(customer.credit) }} تومان</p></div>
          <div class="text-ink-400">ماندهٔ کل حساب مشتری<p v-if="customer.account_balance !== null" class="num mt-1 font-bold" :class="customer.account_balance > 0 ? 'text-amber-300' : 'text-mint-400'">{{ toman(Math.abs(customer.account_balance)) }} تومان · {{ customer.account_balance > 0 ? 'بدهکار' : customer.account_balance < 0 ? 'بستانکار' : 'تسویه' }}</p><p v-else class="mt-1 text-amber-300">حساب قابل تأیید نیست</p></div>
        </summary>
        <div class="space-y-3 px-5 pb-5">
          <p v-if="customer.checked_at" class="text-xs text-ink-500">آخرین بررسی حساب: {{ jDateTime(customer.checked_at) }}</p>
          <div v-for="invoice in customer.invoices" :key="invoice.name" class="flex flex-wrap items-center gap-3 rounded-xl bg-white/[0.03] p-3 text-xs">
            <button class="font-bold text-bone underline underline-offset-4" @click="$emit('open', invoice.name)">{{ invoice.name }}</button>
            <span class="text-ink-400">{{ jShortDate(invoice.posting_date) }}</span>
            <SourcePaymentStatus :payment="invoice" />
            <span class="num text-ink-300">نسیه {{ toman(invoice.credit) }} تومان</span>
            <span class="num text-ink-300">{{ invoice.outstanding !== null ? `ماندهٔ فاکتور ${toman(invoice.outstanding)} تومان` : 'ماندهٔ فاکتور: نیازمند تطبیق حساب' }}</span>
          </div>
        </div>
      </details>
    </div>
    <div v-if="report.customers.length > 5" class="border-t border-white/[0.06] p-3 text-center"><button class="btn-ghost" @click="expanded = !expanded">{{ expanded ? 'نمایش کمتر' : `نمایش همهٔ ${faNumber(report.customers.length)} مشتری` }}</button></div>
  </section>
</template>
