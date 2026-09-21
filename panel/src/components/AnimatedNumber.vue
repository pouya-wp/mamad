<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ value: number; format?: (value: number) => string; duration?: number }>(), {
  duration: 900,
})

const shown = ref(0)
let frame = 0

/** Count from the previous value to the new one with an ease-out-expo curve. */
function animate(from: number, to: number) {
  cancelAnimationFrame(frame)
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    shown.value = to
    return
  }
  const start = performance.now()
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / props.duration)
    shown.value = t === 1 ? to : from + (to - from) * (1 - Math.pow(2, -10 * t))
    if (t < 1) frame = requestAnimationFrame(step)
  }
  frame = requestAnimationFrame(step)
}

watch(
  () => props.value,
  (to, from) => animate(from ?? 0, to ?? 0),
  { immediate: true },
)
onBeforeUnmount(() => cancelAnimationFrame(frame))
</script>

<template>
  <span class="num">{{ format ? format(shown) : Math.round(shown).toLocaleString('fa-IR') }}</span>
</template>
