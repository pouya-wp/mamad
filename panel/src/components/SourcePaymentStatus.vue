<script setup lang="ts">
import type { SourcePaymentSnapshot } from '@/lib/types'
import { computed } from 'vue'

const props = defineProps<{ payment: Pick<SourcePaymentSnapshot, 'status' | 'basis'> & Partial<Pick<SourcePaymentSnapshot, 'checked_at'>> }>()
const states = {
  Unknown: { label: 'نامشخص', tone: 'bg-white/5 text-ink-400' },
  Unpaid: { label: 'پرداخت‌نشده', tone: 'bg-amber-400/10 text-amber-300' },
  Credit: { label: 'نسیه', tone: 'bg-amber-400/10 text-amber-300' },
  Partial: { label: 'پرداخت ناقص', tone: 'bg-amber-400/10 text-amber-300' },
  Paid: { label: 'پرداخت‌شده', tone: 'bg-mint-400/10 text-mint-400' },
  Cancelled: { label: 'لغوشده در سپهریار', tone: 'bg-rose-400/10 text-rose-400' },
}
const state = computed(() => props.payment.status === 'Unknown' && props.payment.checked_at === null
  ? { label: 'در انتظار همگام‌سازی', tone: 'bg-sky-400/10 text-sky-300' }
  : props.payment.basis === 'Unallocated' && !['Unknown', 'Cancelled'].includes(props.payment.status)
  ? { label: 'نیازمند تطبیق تسویه', tone: 'bg-sky-400/10 text-sky-300' }
  : states[props.payment.status])
</script>

<template>
  <span class="inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-xs" :class="state.tone">
    {{ state.label }}
  </span>
</template>
