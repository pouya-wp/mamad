<script setup lang="ts">
import { CornerDownLeft, LoaderCircle, Mic, Paperclip, Square, Volume2, VolumeX, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AgentBlocks from '@/components/agent/AgentBlocks.vue'
import AgentOrb from '@/components/agent/AgentOrb.vue'
import TypeText from '@/components/agent/TypeText.vue'
import { sound } from '@/lib/sound'
import { post, postAudio } from '@/lib/api'
import { DEMO } from '@/demo'
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
const fileInput = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)
const attachmentPreview = ref<string | null>(null)
const attachmentError = ref('')
const recording = ref(false)
const processingVoice = ref(false)
const voiceReplies = ref(false)
const voiceError = ref('')
const preparingSpeech = ref(false)
const speechVoices = [
  { id: 'marin', label: 'مارین' },
  { id: 'cedar', label: 'سیدار' },
  { id: 'nova', label: 'نووا' },
  { id: 'coral', label: 'کورال' },
] as const
type SpeechVoice = typeof speechVoices[number]['id']
const selectedVoice = ref<SpeechVoice>('nova')
let recorder: MediaRecorder | null = null
let stream: MediaStream | null = null
let audioContext: AudioContext | null = null
let playing: AudioBufferSourceNode | null = null
let lastSpoken = 0
let speechRequest = 0

function unlockAudio() {
  if (typeof AudioContext === 'undefined') return
  audioContext ??= new AudioContext()
  void audioContext.resume()
}

function toggleVoiceReplies() {
  voiceReplies.value = !voiceReplies.value
  if (voiceReplies.value) unlockAudio()
  else { speechRequest++; playing?.stop(); preparingSpeech.value = false }
}

function splitSpeech(text: string): string[] {
  const answer = text.slice(0, 1000).trim()
  if (answer.length <= 130) return [answer]
  const punctuation = /[.!؟؛\n]/g
  let split = 0
  for (const match of answer.slice(0, 140).matchAll(punctuation)) {
    const end = (match.index ?? 0) + 1
    if (end >= 50) { split = end; break }
  }
  if (!split) split = answer.lastIndexOf(' ', 100)
  if (split < 50) split = 100
  return [answer.slice(0, split).trim(), answer.slice(split).trim()]
}

function changeVoice(event: Event) {
  const voice = (event.target as HTMLSelectElement).value
  if (!speechVoices.some((item) => item.id === voice)) return
  selectedVoice.value = voice as SpeechVoice
  try { localStorage.setItem('one-cafe-agent-voice', voice) } catch { /* private browsing */ }
}

const allowedFileExtensions = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf', 'docx', 'xlsx', 'txt', 'md', 'csv', 'json'])

function clearAttachment() {
  if (attachmentPreview.value) URL.revokeObjectURL(attachmentPreview.value)
  attachmentPreview.value = null
  selectedFile.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function selectAttachment(file?: File) {
  if (!file) return
  const extension = file.name.split('.').at(-1)?.toLowerCase() ?? ''
  if (!allowedFileExtensions.has(extension)) {
    attachmentError.value = 'فرمت فایل پشتیبانی نمی‌شود'
    return
  }
  if (file.size > 4_000_000 || (file.type.startsWith('image/') && file.size > 3_000_000)) {
    attachmentError.value = 'فایل باید کمتر از ۴ مگابایت و تصویر کمتر از ۳ مگابایت باشد'
    return
  }
  clearAttachment()
  selectedFile.value = file
  if (file.type.startsWith('image/')) attachmentPreview.value = URL.createObjectURL(file)
  attachmentError.value = ''
}

function onFileChange(event: Event) {
  selectAttachment((event.target as HTMLInputElement).files?.[0])
  ;(event.target as HTMLInputElement).value = ''
}

function onPaste(event: ClipboardEvent) {
  const file = Array.from(event.clipboardData?.files ?? []).find((item) => item.type.startsWith('image/'))
  if (file) { event.preventDefault(); selectAttachment(file) }
}

function onDrop(event: DragEvent) {
  selectAttachment(event.dataTransfer?.files[0])
}

async function playReply(text: string) {
  playing?.stop()
  const request = ++speechRequest
  unlockAudio()
  voiceError.value = ''
  preparingSpeech.value = true
  try {
    if (DEMO) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'fa-IR'
      speechSynthesis.cancel()
      speechSynthesis.speak(utterance)
      preparingSpeech.value = false
      return
    }
    const voice = selectedVoice.value
    if (!audioContext) throw new Error('پخش صدا در این مرورگر پشتیبانی نمی‌شود')
    const context = audioContext
    // Generate both pieces at once; the short opening can play while the rest is still being made.
    const clips = splitSpeech(text).map(async (part) => {
      const result = await post<{ audio: string; mime: string }>(
        'cafe_app.api.voice.speak', { text: part, voice },
      )
      const bytes = Uint8Array.from(atob(result.audio), (char) => char.charCodeAt(0))
      return context.decodeAudioData(bytes.buffer)
    }).map((clip) => clip.then((value) => ({ value, error: null }), (error: unknown) => ({ value: null, error })))
    for (const clip of clips) {
      const result = await clip
      if (request !== speechRequest) return
      if (result.error) throw result.error
      await new Promise<void>((resolve) => {
        const source = context.createBufferSource()
        playing = source
        source.buffer = result.value!
        source.connect(context.destination)
        source.onended = () => { if (playing === source) playing = null; resolve() }
        preparingSpeech.value = false
        source.start()
      })
      if (request !== speechRequest) return
    }
  } catch (error) {
    if (request === speechRequest) voiceError.value = error instanceof Error ? error.message : 'پخش پاسخ صوتی انجام نشد'
  } finally {
    if (request === speechRequest) preparingSpeech.value = false
  }
}

async function toggleRecording() {
  if (recording.value) {
    processingVoice.value = true
    recorder?.stop()
    recording.value = false
    return
  }
  voiceError.value = ''
  if (DEMO) { voiceError.value = 'ضبط ویس در نسخه متصل به سرور فعال است'; return }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    voiceError.value = 'مرورگر این دستگاه ضبط صدا را پشتیبانی نمی‌کند'
    return
  }
  try {
    unlockAudio()
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mime = ['audio/webm', 'audio/mp4', 'audio/ogg'].find((type) => MediaRecorder.isTypeSupported(type))
    if (!mime) throw new Error('فرمت ضبط صدای این مرورگر پشتیبانی نمی‌شود')
    recorder = new MediaRecorder(stream, { mimeType: mime })
    const chunks: Blob[] = []
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data) }
    recorder.onstop = async () => {
      stream?.getTracks().forEach((track) => track.stop())
      stream = null
      recording.value = false
      const clip = new Blob(chunks, { type: mime })
      if (!clip.size) return
      processingVoice.value = true
      try {
        const result = await postAudio<{ text: string }>('cafe_app.api.voice.transcribe', clip)
        if (!result.text) throw new Error('صدایی برای تبدیل به متن تشخیص داده نشد')
        draft.value = result.text
        voiceReplies.value = true
        await submit()
      } catch (error) {
        voiceError.value = error instanceof Error ? error.message : 'تبدیل ویس انجام نشد'
      } finally {
        processingVoice.value = false
      }
    }
    recorder.start()
    recording.value = true
    const activeRecorder = recorder
    window.setTimeout(() => { if (activeRecorder?.state === 'recording') { processingVoice.value = true; activeRecorder.stop() } }, 45_000)
  } catch (error) {
    stream?.getTracks().forEach((track) => track.stop())
    stream = null
    voiceError.value = error instanceof Error ? error.message : 'دسترسی به میکروفون ممکن نشد'
  }
}

const orbState = computed(() => (agent.busy ? 'thinking' : agent.messages.some((m) => m.fresh) ? 'speaking' : 'idle'))
const firstName = computed(() => session.user?.full_name?.split(' ')[0] ?? '')

async function submit() {
  const text = draft.value
  const file = selectedFile.value ?? undefined
  if ((!text.trim() && !file) || agent.busy) return
  sound.send()
  draft.value = ''
  const sent = await agent.send(text, file)
  if (sent) clearAttachment()
  else draft.value = text
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
watch(() => agent.messages.at(-1)?.text, (text) => {
  const message = agent.messages.at(-1)
  if (voiceReplies.value && text && message?.role === 'assistant' && !message.pending && message.id !== lastSpoken) {
    lastSpoken = message.id
    void playReply(text)
  }
})
watch(
  () => agent.open,
  async (open) => {
    if (!open) {
      if (recorder?.state === 'recording') {
        recorder.onstop = null
        recorder.stop()
        stream?.getTracks().forEach((track) => track.stop())
        recording.value = false
      }
      return sound.whooshOut()
    }
    sound.whoosh()
    await nextTick()
    input.value?.focus()
  },
)

onMounted(() => {
  try {
    const saved = localStorage.getItem('one-cafe-agent-voice')
    if (speechVoices.some((item) => item.id === saved)) selectedVoice.value = saved as SpeechVoice
  } catch { /* private browsing */ }
  window.addEventListener('keydown', onKey)
  agent.loadStatus()
})
onBeforeUnmount(() => {
  clearAttachment()
  window.removeEventListener('keydown', onKey)
  if (recorder?.state === 'recording') { recorder.onstop = null; recorder.stop() }
  stream?.getTracks().forEach((track) => track.stop())
  playing?.stop()
  void audioContext?.close()
  if (DEMO) speechSynthesis.cancel()
})
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
          <div v-if="m.role === 'user'" class="ask-line animate-rise space-y-2 text-[15px] leading-7 font-medium text-bone">
            <p>{{ m.text }}</p>
            <div v-if="m.attachment" class="inline-flex max-w-full items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-2 text-xs text-ink-200">
              <img v-if="m.attachment.previewUrl" :src="m.attachment.previewUrl" alt="تصویر پیوست" class="size-12 rounded-lg object-cover" />
              <Paperclip v-else class="size-4 shrink-0" />
              <span class="truncate" dir="auto">{{ m.attachment.name }}</span>
            </div>
          </div>

          <div v-else class="space-y-4">
            <div v-if="m.pending" class="space-y-2 py-1">
              <p class="text-xs text-ink-400">دارم نگاه می‌کنم…</p>
              <div class="h-[2px] overflow-hidden rounded bg-white/[0.06]"><div class="printing-bar" /></div>
            </div>
            <template v-else>
              <TypeText class="text-sm leading-8 text-ink-100" :text="m.text" :animate="m.fresh" @done="typed(m)" />
              <button v-if="m.text" class="mt-1 inline-flex items-center gap-1 text-[11px] text-ink-400 hover:text-one-400" title="پخش پاسخ صوتی" @click="playReply(m.text)"><Volume2 class="size-3.5" /> شنیدن پاسخ</button>
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
      <form class="border-t border-white/[0.06] bg-ink-950/60 p-4 backdrop-blur-xl" @submit.prevent="submit" @dragover.prevent @drop.prevent="onDrop">
        <div v-if="selectedFile" class="mb-2 flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-2 text-xs text-ink-200">
          <img v-if="attachmentPreview" :src="attachmentPreview" alt="پیش‌نمایش پیوست" class="size-12 rounded-lg object-cover" />
          <Paperclip v-else class="size-4 shrink-0" />
          <span class="min-w-0 flex-1 truncate" dir="auto">{{ selectedFile.name }}</span>
          <button type="button" class="rounded-lg p-1 hover:bg-white/10" aria-label="حذف پیوست" @click="clearAttachment"><X class="size-4" /></button>
        </div>
        <input ref="fileInput" type="file" class="hidden" accept="image/jpeg,image/png,image/webp,image/gif,.pdf,.docx,.xlsx,.txt,.md,.csv,.json" aria-label="انتخاب تصویر یا فایل" @change="onFileChange" />
        <div class="field-glow flex items-end gap-2 rounded-2xl border border-white/10 bg-ink-850 p-2 transition focus-within:border-one-500/60">
          <button type="button" class="grid size-10 shrink-0 place-items-center rounded-xl text-ink-300 hover:bg-white/5" :disabled="agent.busy" title="افزودن تصویر یا فایل" aria-label="افزودن تصویر یا فایل" @click="fileInput?.click()"><Paperclip class="size-4" /></button>
          <button type="button" class="grid size-10 shrink-0 place-items-center rounded-xl text-ink-300 hover:bg-white/5" :class="recording ? 'bg-rose-400/20 text-rose-300' : ''" :disabled="processingVoice || agent.busy" :title="recording ? 'پایان ضبط' : 'ضبط ویس'" :aria-label="recording ? 'پایان ضبط' : 'ضبط ویس'" @click="toggleRecording">
            <LoaderCircle v-if="processingVoice" class="size-4 animate-spin" /><Square v-else-if="recording" class="size-4" /><Mic v-else class="size-4" />
          </button>
          <span class="px-1.5 pb-2.5 font-mono text-sm text-one-500" dir="ltr">&gt;</span>
          <textarea
            ref="input"
            v-model="draft"
            rows="1"
            class="max-h-32 min-h-10 flex-1 resize-none bg-transparent py-2 text-sm text-ink-100 outline-none placeholder:text-ink-500"
            placeholder="بنویس… مثلاً «۸ میلیون قبض برق دادم»"
            @keydown.enter.exact.prevent="submit"
            @paste="onPaste"
          />
          <button
            data-ripple
            data-sfx="none"
            data-magnetic="0.4"
            class="flex h-10 shrink-0 items-center gap-2 rounded-xl bg-one-500 px-3.5 text-sm font-medium text-white shadow-[0_6px_20px_-6px_rgba(255,79,26,0.9)] transition hover:bg-one-400 disabled:opacity-30"
            :disabled="(!draft.trim() && !selectedFile) || agent.busy"
          >
            بپرس
            <CornerDownLeft class="size-4" />
          </button>
        </div>
        <div class="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10px] text-ink-500">
          <span>{{ attachmentError || (recording ? 'در حال ضبط؛ برای ارسال دوباره بزن' : processingVoice ? 'در حال تبدیل ویس…' : voiceError || (preparingSpeech ? 'در حال آماده‌سازی صدا…' : 'تصویر یا فایل هم می‌توانی بفرستی · صدای پاسخ ساختهٔ هوش مصنوعی است')) }}</span>
          <div class="flex items-center gap-2">
            <label class="flex items-center gap-1">صدا
              <select :value="selectedVoice" class="rounded-lg border border-white/10 bg-ink-850 px-1.5 py-1 text-ink-100 outline-none" aria-label="انتخاب صدای دستیار" @change="changeVoice">
                <option v-for="voice in speechVoices" :key="voice.id" :value="voice.id">{{ voice.label }}</option>
              </select>
            </label>
            <button type="button" class="inline-flex items-center gap-1 hover:text-bone" :aria-label="voiceReplies ? 'خاموش کردن پاسخ صوتی' : 'روشن کردن پاسخ صوتی'" @click="toggleVoiceReplies">
              <Volume2 v-if="voiceReplies" class="size-3.5" /><VolumeX v-else class="size-3.5" /> پاسخ صوتی {{ voiceReplies ? 'روشن' : 'خاموش' }}
            </button>
          </div>
        </div>
        <p class="mt-2 text-center text-[10px] text-ink-500">هیچ سندی بدون تأیید تو ثبت نمی‌شود · Ctrl + K</p>
      </form>
    </aside>
  </Transition>
</template>
