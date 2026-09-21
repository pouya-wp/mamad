<script setup lang="ts">
import { Check, LoaderCircle, X } from 'lucide-vue-next'

import ReceiptPaper from '@/components/ReceiptPaper.vue'
import { faNumber, jDate, percent, toman, uom } from '@/lib/format'
import { type AgentBlock, type ValueFormat, useAgent } from '@/stores/agent'

/**
 * Whatever the assistant has to hand over — a report or a slip to approve —
 * comes out of the printer as a real receipt: label, dotted leader, value.
 * Plain talk stays on the dark deck; only documents get printed.
 */
defineProps<{ blocks: AgentBlock[] }>()
const agent = useAgent()

function show(value: number | string, format?: ValueFormat, unit?: string) {
  if (typeof value === 'string' && format !== 'date') return value
  switch (format) {
    case 'toman':
      return `${toman(Number(value))} ت`
    case 'percent':
      return percent(Number(value))
    case 'date':
      return jDate(String(value))
    case 'number':
      return `${faNumber(Number(value), 1)}${unit ? ` ${uom(unit)}` : ''}`
    default:
      return String(value)
  }
}

const statusLine = {
  pending: 'فیش پیشنهادی — منتظر تأیید',
  working: 'در حال ثبت…',
  done: 'ثبت شد',
  cancelled: 'پاره شد',
  error: 'ثبت نشد',
}

// sparks thrown off when the stamp lands on the paper
const stampSparks = Array.from({ length: 10 }, (_, i) => {
  const angle = (Math.PI * 2 * i) / 10
  return { '--dx': `${Math.cos(angle) * 46}px`, '--dy': `${Math.sin(angle) * 46}px`, accent: i % 2 === 0 }
})
</script>

<template>
  <div class="space-y-5">
    <ReceiptPaper
      v-for="(block, index) in blocks"
      :key="index"
      :title="block.type === 'proposal' ? statusLine[block.status] : block.title || 'گزارش'"
      :code="block.type === 'proposal' ? (block.result?.split(' · ').pop() ?? `PROPOSAL ${block.id.slice(0, 8)}`) : undefined"
      :tilt="index % 2 ? -0.35 : 0.3"
      :class="{
        'is-stamped': block.type === 'proposal' && block.status === 'done',
        'opacity-50': block.type === 'proposal' && block.status === 'cancelled',
      }"
      :style="{ animationDelay: `${index * 140}ms` }"
    >
      <!-- Metrics and lists are the same thing on paper: rows with a dotted leader -->
      <template v-if="block.type === 'metrics'">
        <div v-for="item in block.items" :key="item.label" class="receipt-row">
          <span>{{ item.label }}</span>
          <span class="dots" />
          <span class="num font-bold">{{ show(item.value, item.format) }}</span>
          <span
            v-if="item.change !== undefined && item.change !== null"
            class="num text-[11px]"
            :class="item.change >= 0 ? 'ink-accent' : 'ink-soft'"
            dir="ltr"
          >
            {{ item.change >= 0 ? '▲' : '▼' }}{{ percent(Math.abs(item.change)) }}
          </span>
        </div>
      </template>

      <template v-else-if="block.type === 'list'">
        <div v-for="(item, i) in block.items" :key="i">
          <div class="receipt-row">
            <span>{{ item.label }}</span>
            <span class="dots" />
            <span class="num font-bold" :class="item.tone === 'danger' || item.tone === 'warn' ? 'ink-accent' : ''">
              {{ show(item.value, item.format, item.uom) }}
            </span>
          </div>
          <p v-if="item.hint" class="ink-soft -mt-1 text-[10px]">{{ item.hint }}</p>
        </div>
      </template>

      <!-- A proposal is a slip: nothing is posted until it carries the stamp -->
      <template v-else-if="block.type === 'proposal'">
        <p class="mb-2 text-center font-bold">{{ block.title }}</p>
        <div v-for="line in block.lines" :key="line.label" class="receipt-row">
          <span>{{ line.label }}</span>
          <span class="dots" />
          <span class="num font-bold">{{ show(line.value, line.format, line.uom) }}</span>
        </div>
        <p v-if="block.result" class="mt-2 text-[11px]" :class="block.status === 'error' ? 'ink-accent' : 'ink-soft'">{{ block.result }}</p>

        <!-- the stamp lands in ink, slightly off-angle, like a real one -->
        <div v-if="block.status === 'done'" class="pointer-events-none absolute top-2 left-2">
          <span
            v-for="(s, i) in stampSparks"
            :key="i"
            class="ripple-sparkle"
            :class="{ 'is-accent': s.accent }"
            :style="{ left: '30px', top: '30px', width: '4px', height: '4px', '--dx': s['--dx'], '--dy': s['--dy'], animationDelay: '160ms' }"
          />
          <div class="agent-stamp grid size-[62px] place-items-center rounded-full border-2 text-center" style="border-color: rgba(195, 51, 10, 0.75); color: #c3330a">
            <div class="leading-none">
              <p class="text-[13px] font-light tracking-tight" dir="ltr">ONe</p>
              <p class="mt-1 text-[9px] font-black">ثبت شد</p>
            </div>
          </div>
        </div>
      </template>

      <template #actions>
        <div
          v-if="block.type === 'proposal' && (block.status === 'pending' || block.status === 'working')"
          class="relative mt-3 grid grid-cols-[1fr_auto] gap-2"
        >
          <button class="paper-btn paper-btn-ink" :disabled="block.status === 'working'" @click="agent.confirm(block)">
            <LoaderCircle v-if="block.status === 'working'" class="size-4 animate-spin" />
            <template v-else><Check class="size-4" /> مهر و ثبت</template>
          </button>
          <button class="paper-btn" :disabled="block.status === 'working'" title="پاره کن" @click="agent.cancel(block)"><X class="size-4" /></button>
        </div>
      </template>
    </ReceiptPaper>
  </div>
</template>
