<script setup lang="ts">
import { Printer } from 'lucide-vue-next'
import { computed } from 'vue'

import Modal from '@/components/Modal.vue'
import ReceiptPaper from '@/components/ReceiptPaper.vue'
import { faNumber, jDate, paymentLabel, percent, toman } from '@/lib/format'
import { sound } from '@/lib/sound'
import type { DashboardSummary } from '@/lib/types'

/**
 * The close-of-day slip every till prints: the same paper the assistant uses,
 * but for the owner — and this one can go to a real printer.
 */
const open = defineModel<boolean>({ required: true })
const props = defineProps<{ data: DashboardSummary; label: string }>()

const kpis = computed(() => props.data.kpis)
const margin = computed(() => (kpis.value.revenue ? (kpis.value.gross_profit / kpis.value.revenue) * 100 : 0))
const paymentsTotal = computed(() => props.data.payments.reduce((sum, p) => sum + p.amount, 0))
const code = computed(() => `ONE-${props.data.range.to.replaceAll('-', '')}`)

function print() {
  sound.register()
  window.print()
}
</script>

<template>
  <Modal v-model="open" title="رسید کافه" width="max-w-md">
    <div class="print-area mx-auto max-w-[340px]">
      <ReceiptPaper :title="label" :code="code">
        <p class="ink-soft text-center text-[11px]">{{ jDate(data.range.from) }} تا {{ jDate(data.range.to) }}</p>
        <div class="receipt-rule my-2.5" />

        <div class="receipt-row"><span>فروش</span><span class="dots" /><span class="num font-bold">{{ toman(kpis.revenue) }} ت</span></div>
        <div class="receipt-row"><span>سفارش‌ها</span><span class="dots" /><span class="num font-bold">{{ faNumber(kpis.orders) }}</span></div>
        <div class="receipt-row"><span>اقلام فروخته‌شده</span><span class="dots" /><span class="num font-bold">{{ faNumber(kpis.items_sold) }}</span></div>
        <div class="receipt-row"><span>میانگین هر فاکتور</span><span class="dots" /><span class="num font-bold">{{ toman(kpis.avg_ticket) }} ت</span></div>

        <div class="receipt-rule my-2.5" />
        <div class="receipt-row"><span>بهای تمام‌شده</span><span class="dots" /><span class="num">{{ toman(kpis.cogs) }} ت</span></div>
        <div class="receipt-row text-[15px]">
          <span class="font-bold">سود ناخالص</span><span class="dots" />
          <span class="num font-black">{{ toman(kpis.gross_profit) }} ت</span>
        </div>
        <p class="ink-soft text-[10px]">حاشیه سود {{ percent(margin) }}</p>

        <template v-if="data.payments.length">
          <div class="receipt-rule my-2.5" />
          <p class="ink-soft text-[10px]">روش پرداخت</p>
          <div v-for="p in data.payments" :key="p.mode_of_payment" class="receipt-row">
            <span>{{ paymentLabel(p.mode_of_payment) }}</span>
            <span class="dots" />
            <span class="num">{{ percent(paymentsTotal ? (p.amount / paymentsTotal) * 100 : 0) }}</span>
            <span class="num font-bold">{{ toman(p.amount) }} ت</span>
          </div>
        </template>

        <template v-if="data.top_items.length">
          <div class="receipt-rule my-2.5" />
          <p class="ink-soft text-[10px]">پرفروش‌ترین‌ها</p>
          <div v-for="item in data.top_items.slice(0, 5)" :key="item.item_code" class="receipt-row">
            <span>{{ item.item_name }}</span>
            <span class="dots" />
            <span class="num font-bold">{{ faNumber(item.qty) }}</span>
          </div>
        </template>

        <template v-if="data.low_stock.length">
          <div class="receipt-rule my-2.5" />
          <p class="ink-accent text-[10px]">{{ faNumber(data.low_stock.length) }} قلم زیر حد مجاز — یادت نره سفارش بدی</p>
        </template>

        <div class="receipt-rule my-2.5" />
        <p class="text-center text-[11px]">ممنون که هستی · ONE CAFE</p>
      </ReceiptPaper>
    </div>

    <template #footer>
      <button class="btn-ghost" @click="open = false">بستن</button>
      <button class="btn-primary" @click="print"><Printer class="size-4" /> چاپ</button>
    </template>
  </Modal>
</template>
