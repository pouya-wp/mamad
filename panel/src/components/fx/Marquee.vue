<script setup lang="ts">
defineProps<{ items: string[] }>()

// letter-spacing breaks the joins of Persian letters, so only Latin items get it
const isLatin = (text: string) => /^[\x20-\x7E]+$/.test(text)
</script>

<template>
  <div class="marquee relative overflow-hidden border-y border-white/[0.06] py-3" dir="ltr">
    <div class="marquee-track flex w-max">
      <div v-for="copy in 2" :key="copy" class="flex shrink-0 items-center gap-10 pr-10" :aria-hidden="copy === 2">
        <template v-for="(item, i) in items" :key="i">
          <span class="text-xs whitespace-nowrap text-ink-300" :class="isLatin(item) ? 'tracking-[0.35em]' : ''">{{ item }}</span>
          <span class="size-1 shrink-0 rounded-full bg-one-500 shadow-[0_0_8px_rgba(255,79,26,0.9)]" />
        </template>
      </div>
    </div>
  </div>
</template>
