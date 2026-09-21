<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { percent, tomanCompact } from '@/lib/format'
import { sound } from '@/lib/sound'

/** Category share drawn as the crema ring of a coffee cup seen from above. */
const props = defineProps<{ groups: { item_group: string; revenue: number }[]; palette: string[] }>()

const ready = ref(false)
const hovered = ref<number | null>(null)
onMounted(() => requestAnimationFrame(() => (ready.value = true)))

const total = computed(() => props.groups.reduce((sum, g) => sum + g.revenue, 0))
const arcs = computed(() => {
  let offset = 0
  return props.groups.map((g, i) => {
    const share = total.value ? (g.revenue / total.value) * 100 : 0
    const arc = { share, offset, color: props.palette[i % props.palette.length] }
    offset += share
    return arc
  })
})

const focus = computed(() => (hovered.value === null ? null : { group: props.groups[hovered.value], arc: arcs.value[hovered.value] }))

function enter(i: number) {
  if (hovered.value === i) return
  hovered.value = i
  sound.bubble()
}
</script>

<template>
  <!-- one pointerleave on the svg: moving between arcs must not flash the centre back to the total -->
  <svg viewBox="0 0 220 220" class="mx-auto w-full max-w-[220px]" role="img" aria-label="سهم دسته‌ها از فروش" @pointerleave="hovered = null">
    <defs>
      <radialGradient id="cup-coffee" cx="45%" cy="40%" r="70%">
        <stop offset="0%" stop-color="#3a1d0e" />
        <stop offset="60%" stop-color="#1c0d05" />
        <stop offset="100%" stop-color="#0b0502" />
      </radialGradient>
      <radialGradient id="cup-shine" cx="34%" cy="26%" r="46%">
        <stop offset="0%" stop-color="rgba(255,255,255,0.10)" />
        <stop offset="100%" stop-color="rgba(255,255,255,0)" />
      </radialGradient>
    </defs>

    <!-- saucer and cup -->
    <circle cx="110" cy="110" r="106" fill="#0d0d0f" stroke="rgba(255,255,255,0.06)" />
    <circle cx="110" cy="110" r="88" fill="#140a05" stroke="rgba(245,242,236,0.22)" stroke-width="3" />
    <circle cx="110" cy="110" r="80" fill="url(#cup-coffee)" />
    <circle cx="110" cy="110" r="80" fill="url(#cup-shine)" />

    <!-- crema ring = category shares -->
    <circle
      v-for="(arc, i) in arcs"
      :key="i"
      cx="110"
      cy="110"
      r="60"
      fill="none"
      pathLength="100"
      :stroke="arc.color"
      :stroke-width="hovered === i ? 22 : 16"
      :stroke-dasharray="`${ready ? Math.max(arc.share - 1.2, 0) : 0} 100`"
      :stroke-dashoffset="-arc.offset"
      transform="rotate(-90 110 110)"
      class="cup-arc cursor-pointer"
      :style="{ opacity: hovered !== null && hovered !== i ? 0.35 : 0.92, transitionDelay: ready ? '0ms' : `${i * 90}ms` }"
      @pointerenter="enter(i)"
    />

    <!-- a faint latte-art swirl -->
    <path d="M96 118c-6-10 2-24 14-24s20 14 14 24c-4 7-14 12-14 12s-10-5-14-12z" fill="rgba(245,242,236,0.06)" />

    <text x="110" y="104" text-anchor="middle" class="fill-bone text-[18px] font-bold">
      {{ tomanCompact(focus ? focus.group.revenue : total) }}
    </text>
    <text x="110" y="121" text-anchor="middle" class="fill-ink-400 text-[10px]">
      {{ focus ? focus.group.item_group : 'تومان' }}
    </text>
    <text v-if="focus" x="110" y="137" text-anchor="middle" class="fill-one-400 text-[11px] font-medium">
      {{ percent(focus.arc.share) }}
    </text>
  </svg>
</template>
