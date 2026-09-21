<script setup lang="ts">
import { CircleAlert, CircleCheck, Info, X } from 'lucide-vue-next'

import { dismiss, toasts } from '@/lib/toast'

const icons = { success: CircleCheck, error: CircleAlert, info: Info }
const tones = {
  success: { border: 'border-mint-400/25', icon: 'text-mint-400', bar: 'bg-mint-400' },
  error: { border: 'border-rose-400/30', icon: 'text-rose-400', bar: 'bg-rose-400' },
  info: { border: 'border-white/10', icon: 'text-ink-300', bar: 'bg-one-500' },
}
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-6 z-[100] flex flex-col items-center gap-2 px-4">
    <TransitionGroup
      enter-from-class="opacity-0 translate-y-4 scale-95"
      leave-to-class="opacity-0 scale-90"
      enter-active-class="transition duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
      leave-active-class="transition duration-200"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto relative flex max-w-md items-start gap-3 overflow-hidden rounded-2xl border bg-ink-800/95 px-4 py-3 text-sm shadow-2xl shadow-black backdrop-blur-xl"
        :class="tones[t.kind].border"
      >
        <component :is="icons[t.kind]" class="mt-0.5 size-4 shrink-0" :class="tones[t.kind].icon" />
        <p class="leading-6">{{ t.message }}</p>
        <button class="text-ink-400 hover:text-ink-100" @click="dismiss(t.id)"><X class="size-4" /></button>
        <span
          class="absolute right-0 bottom-0 h-0.5 w-full origin-right opacity-70"
          :class="tones[t.kind].bar"
          :style="{ animation: `toast-progress ${t.timeout}ms linear forwards` }"
        />
      </div>
    </TransitionGroup>
  </div>
</template>
