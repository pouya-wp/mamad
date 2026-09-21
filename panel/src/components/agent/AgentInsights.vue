<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'

import { get } from '@/lib/api'
import { jDateTime } from '@/lib/format'
import { useAgent } from '@/stores/agent'

/**
 * The assistant's note for today, printed on the same tape as the rest of its
 * answers — black paper here, so the dashboard keeps its dark room.
 */
type Insight = { tone: 'up' | 'down' | 'warn' | 'info'; text: string; ask: string }

const agent = useAgent()
const insights = ref<Insight[] | null>(null)
const printedAt = ref(new Date())

const load = async () => {
  insights.value = await get<Insight[]>('cafe_app.api.agent.insights').catch(() => [])
  printedAt.value = new Date()
}
onMounted(load)
watch(() => agent.dataVersion, load)

// the marks a thermal printer can actually set
const marks = { up: '▲', down: '▼', warn: '!', info: '▸' }
const tones = { up: 'text-mint-400', down: 'text-rose-400', warn: 'text-amber-300', info: 'text-one-500' }
const serial = computed(() => String(100 + new Date().getDate()))
</script>

<template>
  <section class="slip px-6 py-6 sm:px-8">
    <div class="flex items-baseline gap-3">
      <p class="text-base font-light text-bone" dir="ltr">ON<span class="text-one-500">1</span>E</p>
      <p class="flex-1 text-xs text-ink-400">یادداشت دستیار · {{ jDateTime(printedAt) }}</p>
      <p class="num hidden text-[10px] text-ink-500 sm:block" dir="ltr">NO. {{ serial }}</p>
    </div>

    <div class="my-4 border-t border-b border-white/15" style="height: 3px" />

    <div v-if="insights === null" class="grid gap-2 md:grid-cols-2">
      <div v-for="i in 4" :key="i" class="h-10 animate-pulse rounded bg-white/[0.03]" />
    </div>

    <div v-else-if="insights.length" class="grid gap-x-8 md:grid-cols-2">
      <button v-for="(item, i) in insights" :key="i" class="slip-row text-sm text-ink-100" @click="agent.ask(item.ask)">
        <span class="mark shrink-0 text-xs" :class="tones[item.tone]">{{ marks[item.tone] }}</span>
        <span class="flex-1 leading-7">{{ item.text }}</span>
        <ArrowLeft class="go size-4 shrink-0 self-center text-one-400" />
      </button>
    </div>
    <p v-else class="text-sm text-ink-400">هنوز داده کافی برای تحلیل نیست.</p>

    <p class="mt-5 text-center text-[10px] text-ink-500">
      برای پرسیدن، روی هر خط بزن · یا
      <button class="text-one-400 underline underline-offset-4 hover:text-one-300" @click="agent.open = true">دفتر دستیار</button>
      را باز کن
    </p>
  </section>
</template>
