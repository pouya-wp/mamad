<script setup lang="ts">
import { computed } from 'vue'

/**
 * The assistant's avatar: the "O" of the logo as a thin neon ring with the orange "1" inside.
 * Idle it breathes, thinking it spins with orbiting sparks, speaking it sends out pulses.
 * Pure CSS transforms/opacity, so it stays smooth everywhere.
 */
const props = withDefaults(defineProps<{ state?: 'idle' | 'thinking' | 'speaking'; size?: number }>(), {
  state: 'idle',
  size: 36,
})

const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  '--stroke': `${Math.min(6, Math.max(1.5, props.size * 0.045))}px`,
}))
</script>

<template>
  <span class="agent-o" :class="`is-${state}`" :style="style" aria-hidden="true">
    <span class="agent-o__glow" />
    <span class="agent-o__face" />
    <span class="agent-o__arc" />
    <span class="agent-o__pulse" />
    <span class="agent-o__pulse is-late" />
    <span class="agent-o__orbit">
      <span v-for="i in 3" :key="i" class="agent-o__spark" :style="{ '--i': i }" />
    </span>
    <svg class="agent-o__one" viewBox="0 0 24 24" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="M13.5 19V5l-3.5 3" stroke="#ff4f1a" stroke-width="2.4" />
    </svg>
  </span>
</template>
