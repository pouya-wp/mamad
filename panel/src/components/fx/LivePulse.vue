<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { faNumber, toman, tomanCompact } from '@/lib/format'
import { sound } from '@/lib/sound'
import { usePulse } from '@/stores/pulse'

/**
 * The café's heartbeat in the header: an ECG line that sweeps while the shop is
 * quiet and spikes the moment a sale lands at the till, with the amount flashing by.
 */
const pulse = usePulse()
const beating = ref(false)
const flash = ref(false)
let timers: number[] = []

watch(
  () => pulse.beat,
  () => {
    beating.value = true
    flash.value = true
    sound.success()
    timers.push(window.setTimeout(() => (beating.value = false), 1600))
    timers.push(window.setTimeout(() => (flash.value = false), 3400))
  },
)

onMounted(() => pulse.start())
onBeforeUnmount(() => {
  timers.forEach(clearTimeout)
  timers = []
})
</script>

<template>
  <RouterLink
    to="/orders"
    class="pulse-monitor hidden items-center gap-3 rounded-xl border border-white/10 bg-white/[0.02] px-3 py-1.5 transition hover:border-one-500/40 md:flex"
    :class="{ 'is-beating': beating }"
    :title="`${faNumber(pulse.orders)} سفارش امروز`"
  >
    <svg viewBox="0 0 120 28" class="h-7 w-[86px] shrink-0" aria-hidden="true">
      <path class="pulse-base" d="M0 14 H26 l3 -9 l3 18 l3 -9 H62 l4 -5 l3 9 l3 -4 H120" />
      <path class="pulse-sweep" d="M0 14 H26 l3 -9 l3 18 l3 -9 H62 l4 -5 l3 9 l3 -4 H120" />
    </svg>

    <div class="leading-4">
      <p class="num text-[13px] font-medium text-bone">{{ tomanCompact(pulse.revenue) }}</p>
      <p class="text-[10px] text-ink-500">فروش امروز</p>
    </div>

    <Transition enter-active-class="animate-pop" leave-active-class="transition duration-300" leave-to-class="-translate-y-2 opacity-0">
      <span v-if="flash" class="num rounded-full bg-one-500/15 px-2 py-0.5 text-[11px] text-one-300">+{{ toman(pulse.lastAmount) }}</span>
    </Transition>
  </RouterLink>
</template>
