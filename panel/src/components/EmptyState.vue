<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ icon?: Component; title: string; text?: string }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
    <div v-if="icon" class="grid size-12 animate-float place-items-center rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.06] to-white/[0.01] text-ink-300 shadow-[0_12px_30px_-12px_rgba(255,79,26,0.35)]">
      <component :is="icon" class="size-5" />
    </div>
    <p class="font-medium text-ink-100">{{ title }}</p>
    <p v-if="text" class="max-w-xs text-sm leading-6 text-ink-400">{{ text }}</p>
    <slot />
  </div>
</template>
