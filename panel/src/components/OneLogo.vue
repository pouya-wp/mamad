<script setup lang="ts">
import { brand } from '@/lib/brand'

withDefaults(defineProps<{ size?: number; withWordmark?: boolean; animated?: boolean }>(), {
  size: 40,
  withWordmark: false,
  animated: false,
})

const isOne = brand.latin === 'ONE'
const letters = [...(isOne ? 'ONE1CAFE' : brand.wordmark)]
const accentAt = (letter: string, index: number) => (isOne ? letter === '1' : letter === brand.accent && index === brand.latin.indexOf(brand.accent))
</script>

<template>
  <div class="inline-flex flex-col items-center gap-2" dir="ltr" :class="{ 'logo-animated': animated }">
    <!-- ONE CAFE: "ONe" in thin geometric strokes, the right stem of the N being the orange "1" -->
    <svg v-if="isOne" :height="size" viewBox="0 0 132 48" fill="none" stroke-linecap="round" stroke-linejoin="round" :aria-label="brand.wordmark">
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

    <!-- TORANJ: the toranj medallion the café is named after — the carpet motif and the citrus,
         drawn in the same thin strokes, with the stem and leaf in the brand's orange. -->
    <svg v-else :height="size" viewBox="0 0 44 48" fill="none" stroke-linecap="round" stroke-linejoin="round" :aria-label="brand.wordmark">
      <path
        class="logo-stroke stroke-1"
        pathLength="1"
        d="M22 9c10.5 8.5 14.5 16 14.5 21.5 0 8-6.5 13-14.5 14.5-8-1.5-14.5-6.5-14.5-14.5C7.5 25 11.5 17.5 22 9Z"
        stroke="currentColor"
        stroke-width="2.4"
      />
      <path
        class="logo-stroke stroke-2"
        pathLength="1"
        d="M22 20c5.5 4.5 7.5 8.5 7.5 11.5 0 4-3 6.5-7.5 7.5-4.5-1-7.5-3.5-7.5-7.5 0-3 2-7 7.5-11.5Z"
        stroke="currentColor"
        stroke-width="1.5"
      />
      <path class="one-stem logo-stroke stroke-3" pathLength="1" d="M22 9V3" stroke="#ff4f1a" stroke-width="2.6" />
      <path class="one-stem logo-stroke stroke-4" pathLength="1" d="M22.5 5.5c2.5-3.5 6-4 8.5-3-.5 3.5-4 5.5-8.5 3.5Z" stroke="#ff4f1a" stroke-width="1.8" />
    </svg>

    <span v-if="withWordmark" class="flex gap-[0.62em] text-[10px] text-ink-300">
      <span
        v-for="(letter, i) in letters"
        :key="i"
        class="logo-letter"
        :class="{ 'text-one-500': accentAt(letter, i) }"
        :style="animated ? { animationDelay: `${900 + i * 70}ms` } : undefined"
      >
        {{ letter }}
      </span>
    </span>
  </div>
</template>
