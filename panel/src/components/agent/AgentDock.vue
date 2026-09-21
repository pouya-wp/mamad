<script setup lang="ts">
import { CornerDownLeft, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AgentBlocks from '@/components/agent/AgentBlocks.vue'
import AgentOrb from '@/components/agent/AgentOrb.vue'
import TypeText from '@/components/agent/TypeText.vue'
import { sound } from '@/lib/sound'
import { type ChatMessage, useAgent } from '@/stores/agent'
import { useSession } from '@/stores/session'

/**
 * The assistant talks on the dark deck, and prints: every report it hands over and
 * every entry it wants to post comes out of the head as a real receipt (AgentBlocks).
 */
const agent = useAgent()
const session = useSession()
const draft = ref('')
const scroller = ref<HTMLElement>()
const input = ref<HTMLTextAreaElement>()

const orbState = computed(() => (agent.busy ? 'thinking' : agent.messages.some((m) => m.fresh) ? 'speaking' : 'idle'))
const firstName = computed(() => session.user?.full_name?.split(' ')[0] ?? '')

async function submit() {
  const text = draft.value
  if (!text.trim() || agent.busy) return
  sound.send()
  draft.value = ''
  await agent.send(text)
}

function onKey(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    agent.open = !agent.open
  } else if (event.key === 'Escape' && agent.open) {
    agent.open = false
  }
}

function typed(message: ChatMessage) {
  message.fresh = false
  scrollDown()
}

async function scrollDown() {
  await nextTick()
  scroller.value?.scrollTo({ top: scroller.value.scrollHeight, behavior: 'smooth' })
}

watch(() => [agent.messages.length, agent.busy], scrollDown)
watch(
  () => agent.open,
  async (open) => {
    if (!open) return sound.whooshOut()
    sound.whoosh()
    await nextTick()
    input.value?.focus()
  },
)

onMounted(() => {
  window.addEventListener('keydown', onKey)
  agent.loadStatus()
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <!-- Launcher: a slip still hanging out of the printer -->
  <button
    v-if="!agent.open"
    data-ripple
    data-magnetic="0.35"
    class="agent-tab fixed bottom-6 left-6 z-40 flex items-center gap-3 rounded-full py-2 pr-2.5 pl-5 text-sm text-bone backdrop-blur-xl"
    @click="agent.open = true"
  >
    <AgentOrb :size="34" :state="orbState" />
    دستیار One
  </button>

  <!-- The printer -->
  <Transition
    enter-from-class="-translate-x-full"
    leave-to-class="-translate-x-full"
    enter-active-class="transition duration-500 ease-[cubic-bezier(0.2,0.9,0.2,1)]"
    leave-active-class="transition duration-200 ease-in"
  >
    <aside v-if="agent.open" class="printer fixed inset-y-0 left-0 z-50 flex w-full flex-col shadow-2xl shadow-black sm:w-[452px]">
      <!-- the head -->
      <header class="printer-head relative flex items-center gap-3 px-5 pt-4 pb-5">
        <AgentOrb :size="34" :state="orbState" />
        <div class="flex-1">
          <p class="text-sm font-bold text-bone">دستیار One</p>
          <p class="text-[11px] text-ink-400">{{ agent.busy ? 'دارم نگاه می‌کنم…' : 'حسابدار و مدیر کافه' }}</p>
        </div>
        <span class="flex items-center gap-1.5 text-[10px] text-ink-400">
          <i class="printer-led" :class="agent.mode === 'live' ? 'is-live' : 'is-demo'" />
          {{ agent.mode === 'live' ? 'آنلاین' : 'دمو' }}
        </span>
        <button class="rounded-lg p-1.5 text-ink-400 transition hover:bg-white/5 hover:text-ink-100" aria-label="بستن" @click="agent.open = false">
          <X class="size-5" />
        </button>
        <div v-if="agent.busy" class="printing-bar absolute inset-x-0 bottom-0" />
      </header>

      <!-- the conversation -->
      <div ref="scroller" class="flex-1 space-y-6 overflow-x-hidden overflow-y-auto px-5 py-6">
        <div v-if="!agent.messages.length">
          <p class="text-lg font-black text-bone">سلام{{ firstName ? ` ${firstName}` : '' }}</p>
          <p class="mt-2 text-sm leading-7 text-ink-300">
            بپرس چه خبره، یا فقط بگو چی خریدی و چقدر دادی؛ حسابش را می‌نویسم و فیشش را می‌دهم دستت.
          </p>
          <p class="mt-7 text-[10px] text-ink-500">بردار و بپرس</p>
          <button v-for="s in agent.suggestions" :key="s" class="slip-row text-sm text-ink-100" @click="agent.send(s)">
            <span class="mark shrink-0 text-xs">▸</span>
            <span class="flex-1 text-right leading-7">{{ s }}</span>
          </button>
        </div>

        <template v-for="m in agent.messages" :key="m.id">
          <!-- what the owner asked, echoed like a keyed-in line -->
          <p v-if="m.role === 'user'" class="ask-line animate-rise text-[15px] leading-7 font-medium text-bone">{{ m.text }}</p>

          <div v-else class="space-y-4">
            <div v-if="m.pending" class="space-y-2 py-1">
              <p class="text-xs text-ink-400">دارم نگاه می‌کنم…</p>
              <div class="h-[2px] overflow-hidden rounded bg-white/[0.06]"><div class="printing-bar" /></div>
            </div>
            <template v-else>
              <TypeText class="text-sm leading-8 text-ink-100" :text="m.text" :animate="m.fresh" @done="typed(m)" />
              <template v-if="!m.fresh">
                <AgentBlocks v-if="m.blocks?.length" :blocks="m.blocks" />
                <template v-if="m.suggestions?.length">
                  <p class="pt-2 text-[10px] text-ink-500">بعدش؟</p>
                  <button v-for="s in m.suggestions" :key="s" class="slip-row text-sm text-ink-200" @click="agent.send(s)">
                    <span class="mark shrink-0 text-xs">▸</span>
                    <span class="flex-1 text-right leading-7">{{ s }}</span>
                  </button>
                </template>
              </template>
            </template>
          </div>
        </template>
      </div>

      <!-- the keypad -->
      <form class="border-t border-white/[0.06] bg-ink-950/60 p-4 backdrop-blur-xl" @submit.prevent="submit">
        <div class="field-glow flex items-end gap-2 rounded-2xl border border-white/10 bg-ink-850 p-2 transition focus-within:border-one-500/60">
          <span class="px-1.5 pb-2.5 font-mono text-sm text-one-500" dir="ltr">&gt;</span>
          <textarea
            ref="input"
            v-model="draft"
            rows="1"
            class="max-h-32 min-h-10 flex-1 resize-none bg-transparent py-2 text-sm text-ink-100 outline-none placeholder:text-ink-500"
            placeholder="بنویس… مثلاً «۸ میلیون قبض برق دادم»"
            @keydown.enter.exact.prevent="submit"
          />
          <button
            data-ripple
            data-sfx="none"
            data-magnetic="0.4"
            class="flex h-10 shrink-0 items-center gap-2 rounded-xl bg-one-500 px-3.5 text-sm font-medium text-white shadow-[0_6px_20px_-6px_rgba(255,79,26,0.9)] transition hover:bg-one-400 disabled:opacity-30"
            :disabled="!draft.trim() || agent.busy"
          >
            بپرس
            <CornerDownLeft class="size-4" />
          </button>
        </div>
        <p class="mt-2 text-center text-[10px] text-ink-500">هیچ سندی بدون تأیید تو ثبت نمی‌شود · Ctrl + K</p>
      </form>
    </aside>
  </Transition>
</template>
