<script setup lang="ts">
import { BellRing, ChevronLeft, CircleAlert, Info, PartyPopper, TriangleAlert } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { faNumber } from '@/lib/format'

import type { Alert } from '@/lib/types'

const props = defineProps<{ alerts: Alert[] | null }>()

const ICONS = { danger: CircleAlert, warn: TriangleAlert, info: Info, ok: PartyPopper }
const TONES = {
  danger: 'border-rose-400/30 bg-rose-400/[0.07] text-rose-300',
  warn: 'border-amber-300/30 bg-amber-300/[0.07] text-amber-200',
  info: 'border-sky-400/20 bg-sky-400/[0.05] text-sky-200',
  ok: 'border-mint-400/25 bg-mint-400/[0.06] text-mint-300',
}

// Urgent items always show; the calmer ones fold behind "more".
const expanded = ref(false)
const urgent = computed(() => (props.alerts ?? []).filter((a) => a.tone === 'danger' || a.tone === 'warn'))
const visible = computed(() => (expanded.value ? props.alerts ?? [] : (props.alerts ?? []).slice(0, Math.max(4, urgent.value.length))))
const hidden = computed(() => (props.alerts?.length ?? 0) - visible.value.length)
</script>

<template>
  <section class="space-y-2">
    <div class="flex items-center gap-2 text-sm text-ink-300">
      <BellRing class="size-4 text-one-500" />
      <span class="font-bold text-bone">هشدارها و اطلاعیه‌ها</span>
      <span v-if="alerts" class="text-xs text-ink-500">{{ alerts.length ? `${faNumber(alerts.length)} مورد` : 'همه‌چیز مرتب است' }}</span>
    </div>
    <div v-if="alerts === null" class="grid gap-2 md:grid-cols-2">
      <div v-for="i in 2" :key="i" class="h-16 animate-pulse rounded-2xl bg-white/[0.03]" />
    </div>
    <div v-else-if="alerts.length" class="grid gap-2 md:grid-cols-2">
      <component
        :is="a.link ? RouterLink : 'div'"
        v-for="(a, index) in visible"
        :key="index"
        :to="a.link ?? undefined"
        class="group flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm transition"
        :class="[TONES[a.tone], a.link ? 'hover:brightness-125' : '']"
      >
        <component :is="ICONS[a.tone]" class="mt-0.5 size-4 shrink-0" />
        <div class="min-w-0 flex-1">
          <p class="font-medium">{{ a.title }}</p>
          <p v-if="a.text" class="mt-0.5 text-xs opacity-75">{{ a.text }}</p>
        </div>
        <ChevronLeft v-if="a.link" class="mt-0.5 size-4 shrink-0 opacity-40 transition group-hover:opacity-90" />
      </component>
    </div>
    <button v-if="hidden > 0" class="text-xs text-ink-400 hover:text-bone" @click="expanded = true">{{ faNumber(hidden) }} اطلاعیه دیگر</button>
  </section>
</template>
