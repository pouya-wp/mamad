<script setup lang="ts">
withDefaults(defineProps<{ size?: number; withWordmark?: boolean; animated?: boolean }>(), {
  size: 40,
  withWordmark: false,
  animated: false,
})

const letters = [...'ONE1CAFE']
</script>

<template>
  <div class="inline-flex flex-col items-center gap-2" dir="ltr" :class="{ 'logo-animated': animated }">
    <!-- "ONe" wordmark: thin geometric strokes; the right stem of the N is the orange "1" -->
    <svg :height="size" viewBox="0 0 132 48" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-label="ONE CAFE">
      <circle class="logo-stroke stroke-1" pathLength="1" cx="22" cy="24" r="17" stroke="currentColor" stroke-width="2.6" />
      <path class="logo-stroke stroke-2" pathLength="1" d="M50 41V7l26 34" stroke="currentColor" stroke-width="2.6" />
      <path class="one-stem logo-stroke stroke-3" pathLength="1" d="M78 41V7l-6 5" stroke="#ff4f1a" stroke-width="2.8" />
      <path
        class="logo-stroke stroke-4"
        pathLength="1"
        d="M92 26h30c0-9-6.7-15-15-15s-15 6.7-15 15 6.7 15 15 15c5 0 9-2 12-5.5"
        stroke="currentColor"
        stroke-width="2.6"
      />
    </svg>
    <span v-if="withWordmark" class="flex gap-[0.62em] text-[10px] text-ink-300">
      <span
        v-for="(letter, i) in letters"
        :key="i"
        class="logo-letter"
        :class="{ 'text-one-500': letter === '1' }"
        :style="animated ? { animationDelay: `${900 + i * 70}ms` } : undefined"
      >
        {{ letter }}
      </span>
    </span>
  </div>
</template>
