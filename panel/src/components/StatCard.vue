<script setup lang="ts">
import { TrendingDown, TrendingUp } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import RollingNumber from '@/components/fx/RollingNumber.vue'
import { faNumber, percent, toman } from '@/lib/format'

const props = defineProps<{
  label: string
  /** A number rolls in slot-machine style with `format`; a string is shown as-is. */
  value: number | string
  format?: 'toman' | 'number'
  unit?: string
  change?: number | null
  hint?: string
  accent?: boolean
}>()

const up = computed(() => (props.change ?? 0) >= 0)
const formatter = computed(() => (props.format === 'toman' ? toman : (n: number) => faNumber(n)))

// the neon frame surges for a moment whenever the number goes up (e.g. a new sale)
const surging = ref(false)
watch(
  () => props.value,
  (now, before) => {
    if (typeof now !== 'number' || typeof before !== 'number' || now <= before) return
    surging.value = true
    setTimeout(() => (surging.value = false), 1600)
  },
)
</script>

<template>
  <div
    class="card spotlight group @container overflow-hidden p-6 transition duration-500 hover:-translate-y-0.5 hover:border-white/10 sm:p-7"
    :class="[
      accent ? 'neon-frame border-one-500/20 bg-gradient-to-bl from-one-500/[0.14] via-ink-850 to-ink-850' : '',
      { 'is-surging': surging },
    ]"
  >
    <div v-if="accent" class="pointer-events-none absolute -top-16 -left-16 -z-10 size-44 animate-drift rounded-full bg-one-500/25 blur-3xl" />
    <p class="text-sm text-ink-300">{{ label }}</p>
    <div class="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <!-- scales with the card width so long rial amounts never overflow -->
      <span class="text-[clamp(1.35rem,12.5cqi,2.125rem)] leading-tight font-bold tracking-tight whitespace-nowrap text-bone">
        <RollingNumber v-if="typeof value === 'number'" :value="value" :format="formatter" />
        <span v-else class="num">{{ value }}</span>
      </span>
      <span v-if="unit" class="text-sm text-ink-400">{{ unit }}</span>
    </div>
    <div class="mt-3 flex h-6 items-center gap-2 text-xs">
      <span
        v-if="change !== undefined && change !== null"
        class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium"
        :class="up ? 'bg-mint-400/10 text-mint-400' : 'bg-rose-400/10 text-rose-400'"
      >
        <component :is="up ? TrendingUp : TrendingDown" class="size-3.5" />
        {{ percent(Math.abs(change)) }}
      </span>
      <span class="text-ink-400">{{ hint }}</span>
    </div>
  </div>
</template>
