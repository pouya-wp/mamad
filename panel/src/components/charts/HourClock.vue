<script setup lang="ts">
import { computed, ref } from 'vue'

import { faNumber, toman } from '@/lib/format'
import { sound } from '@/lib/sound'

/** A 24-hour dial shaped like the "O" of the logo; busier hours glow brighter. */
type Hour = { hour: number; orders: number; revenue: number }
const props = defineProps<{ hours: Hour[] }>()

const CENTER = 150
const INNER = 92
const OUTER = 132
const nowHour = new Date().getHours()
const hovered = ref<number | null>(null)

// The café is open 8:30–23:30; the faint outer arc marks those hours.
const OPEN_FROM = 8.5
const OPEN_TO = 23.5
const openArc = { length: ((OPEN_TO - OPEN_FROM) / 24) * 100, offset: -(OPEN_FROM / 24) * 100 }

/** Each hour plays its own note, so sweeping around the dial plays a scale. */
function hover(hour: number) {
  if (hovered.value === hour) return
  hovered.value = hour
  sound.note(hour)
}

const peak = computed(() => props.hours.reduce((best, h) => (h.orders > best.orders ? h : best), { hour: nowHour, orders: 0, revenue: 0 }))
const max = computed(() => Math.max(1, peak.value.orders))
const focus = computed(() => props.hours.find((h) => h.hour === hovered.value) ?? peak.value)

const point = (radius: number, angle: number) => `${CENTER + radius * Math.cos(angle)} ${CENTER + radius * Math.sin(angle)}`
const angleOf = (hour: number) => (hour / 24) * Math.PI * 2 - Math.PI / 2

function segment(hour: number) {
  const gap = 0.022
  const a0 = angleOf(hour) + gap
  const a1 = angleOf(hour + 1) - gap
  return `M ${point(OUTER, a0)} A ${OUTER} ${OUTER} 0 0 1 ${point(OUTER, a1)} L ${point(INNER, a1)} A ${INNER} ${INNER} 0 0 0 ${point(INNER, a0)} Z`
}

function fill(h: Hour) {
  if (!h.orders) return 'rgba(255,255,255,0.035)'
  return `rgba(255, 79, 26, ${0.14 + 0.86 * (h.orders / max.value)})`
}

const labels = [0, 3, 6, 9, 12, 15, 18, 21].map((hour) => {
  const angle = angleOf(hour)
  return { hour, x: CENTER + 74 * Math.cos(angle), y: CENTER + 74 * Math.sin(angle) }
})
const nowDot = computed(() => {
  const angle = angleOf(nowHour + 0.5)
  return { x: CENTER + 142 * Math.cos(angle), y: CENTER + 142 * Math.sin(angle) }
})
</script>

<template>
  <!-- one pointerleave on the svg: sweeping across segments must not flicker the centre -->
  <svg viewBox="0 0 300 300" class="w-full max-w-[300px] select-none" role="img" aria-label="ضربان کافه در ۲۴ ساعت" @pointerleave="hovered = null">
    <defs>
      <filter id="clock-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="blur" />
        <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
    </defs>

    <circle :cx="CENTER" :cy="CENTER" :r="OUTER + 10" fill="none" stroke="rgba(255,255,255,0.05)" />
    <circle
      class="clock-ring"
      :cx="CENTER"
      :cy="CENTER"
      :r="OUTER + 10"
      fill="none"
      stroke="rgba(245,242,236,0.22)"
      stroke-width="1.5"
      stroke-linecap="round"
      pathLength="100"
      :stroke-dasharray="`${openArc.length} 100`"
      :stroke-dashoffset="openArc.offset"
      :transform="`rotate(-90 ${CENTER} ${CENTER})`"
    />
    <path
      v-for="h in hours"
      :key="h.hour"
      class="clock-seg cursor-pointer"
      :d="segment(h.hour)"
      :fill="fill(h)"
      :filter="h.orders / max > 0.6 ? 'url(#clock-glow)' : undefined"
      :stroke="h.hour === nowHour ? 'rgba(245,242,236,0.55)' : 'transparent'"
      stroke-width="1"
      :style="{ animationDelay: `${h.hour * 28}ms`, opacity: hovered !== null && hovered !== h.hour ? 0.45 : 1 }"
      @pointerenter="hover(h.hour)"
    />

    <text v-for="l in labels" :key="l.hour" :x="l.x" :y="l.y" text-anchor="middle" dominant-baseline="central" class="fill-ink-500 text-[10px]">
      {{ faNumber(l.hour) }}
    </text>

    <circle class="clock-now" :cx="nowDot.x" :cy="nowDot.y" r="3.5" fill="#ff4f1a" />

    <text :x="CENTER" :y="CENTER - 22" text-anchor="middle" class="fill-ink-400 text-[10px]">
      {{ hovered === null ? 'شلوغ‌ترین ساعت' : 'ساعت انتخابی' }}
    </text>
    <text :x="CENTER" :y="CENTER + 8" text-anchor="middle" class="fill-bone text-[34px] font-extralight">
      {{ faNumber(focus.hour) }}:۰۰
    </text>
    <text :x="CENTER" :y="CENTER + 32" text-anchor="middle" class="fill-one-400 text-[11px]">
      {{ faNumber(focus.orders) }} سفارش · {{ toman(focus.revenue) }}
    </text>
  </svg>
</template>
