<script setup lang="ts">
import { computed } from 'vue'

import { jDateTime } from '@/lib/format'

/**
 * One slip of till paper: torn at both ends, printed line by line, with the café's
 * head, a ghosted logo behind the numbers and a barcode at the foot.
 * Used by the assistant for every report it hands over, and by the day's receipt.
 */
const props = withDefaults(
  defineProps<{
    title?: string
    /** printed under the bars; also the seed the bars are generated from */
    code?: string
    at?: Date | string
    /** slight hand-placed tilt, so a stack of slips never looks like a table */
    tilt?: number
    wide?: boolean
  }>(),
  { tilt: 0 },
)

const stamp = computed(() => jDateTime(props.at ?? new Date()))

/** Deterministic bars — the same code always prints the same barcode. */
const bars = computed(() => {
  const seed = props.code ?? props.title ?? 'ONE'
  let hash = 7
  for (const char of seed) hash = (hash * 31 + char.charCodeAt(0)) % 100000
  return Array.from({ length: 44 }, (_, i) => {
    hash = (hash * 1103515245 + 12345) % 2147483648
    return { w: 1 + ((hash >> (i % 5)) % 3), h: 62 + ((hash >> 3) % 39) }
  })
})
</script>

<template>
  <div class="paper-slip px-4 py-4 text-[13px] leading-7" :style="{ transform: `rotate(${tilt}deg)`, maxWidth: wide ? undefined : '100%' }">
    <p class="paper-watermark" dir="ltr">ONe</p>

    <div class="relative flex items-baseline gap-2 text-[10px]">
      <span class="text-[13px] font-light" dir="ltr">ON<span class="ink-accent">1</span>E</span>
      <span class="ink-soft flex-1">{{ title }}</span>
      <span class="ink-soft">{{ stamp }}</span>
    </div>
    <div class="receipt-rule my-2.5" />

    <div class="relative">
      <slot />
    </div>

    <slot name="actions" />

    <div class="relative mt-4">
      <div class="receipt-rule mb-3" />
      <div class="barcode" aria-hidden="true">
        <i v-for="(bar, i) in bars" :key="i" :style="{ width: `${bar.w}px`, height: `${bar.h}%` }" />
      </div>
      <p class="ink-soft mt-1.5 text-center text-[10px]" dir="ltr">{{ code ?? 'ONE CAFE · YAZD' }}</p>
    </div>
  </div>
</template>
