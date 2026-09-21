<script setup lang="ts">
import { ArrowLeft, Eye, EyeOff, LoaderCircle, TriangleAlert } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import SteamBackground from '@/components/fx/SteamBackground.vue'
import OneLogo from '@/components/OneLogo.vue'
import { sound } from '@/lib/sound'
import { useSession } from '@/stores/session'

const session = useSession()
const router = useRouter()
const route = useRoute()

const usr = ref('')
const pwd = ref('')
const reveal = ref(false)
const loading = ref(false)
const error = ref('')
const rejected = ref(false)
const capsLock = ref(false)

const canSubmit = computed(() => usr.value.trim().length > 0 && pwd.value.length > 0 && !loading.value)

// The browser's own "Please fill out this field" bubble is in English; say it in Persian.
function requiredMessage(event: Event) {
  const input = event.target as HTMLInputElement
  input.setCustomValidity(input.validity.valueMissing ? 'این فیلد را پر کن' : '')
}
function clearMessage(event: Event) {
  ;(event.target as HTMLInputElement).setCustomValidity('')
  error.value = ''
}

const trackCaps = (event: KeyboardEvent) => (capsLock.value = event.getModifierState?.('CapsLock') ?? false)

/** Frappe's messages are English and technical; say what actually happened. */
function reason(problem: unknown) {
  const text = problem instanceof Error ? problem.message : String(problem)
  if (/invalid|incorrect|not allowed|authentication/i.test(text)) return 'نام کاربری یا رمز عبور درست نیست.'
  if (/disabled|inactive/i.test(text)) return 'این حساب غیرفعال است.'
  if (/fetch|network|failed to|502|503|504/i.test(text)) return 'به سرور کافه وصل نشدم. بکند بالا هست؟'
  return text || 'ورود انجام نشد.'
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = ''
  try {
    await session.login(usr.value.trim(), pwd.value)
    sound.welcome()
    router.replace((route.query.next as string) || '/')
  } catch (problem) {
    error.value = reason(problem)
    sound.error()
    rejected.value = true
    setTimeout(() => (rejected.value = false), 500)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="relative grid min-h-dvh overflow-hidden bg-ink-950 lg:grid-cols-[1.1fr_1fr]">
    <!-- Brand side -->
    <div class="relative hidden overflow-hidden lg:block">
      <SteamBackground />
      <div class="absolute top-1/2 left-1/2 size-[560px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.05]" />
      <div class="absolute top-1/2 left-1/2 size-[400px] -translate-x-1/2 -translate-y-1/2 animate-[spin_40s_linear_infinite] rounded-full border border-one-500/30 border-t-one-500/80 shadow-[0_0_120px_-20px] shadow-one-500/50" />
      <div class="relative flex h-full flex-col items-center justify-center text-bone">
        <div class="scale-[2.4]"><OneLogo :size="40" animated with-wordmark /></div>
      </div>
      <div class="absolute right-10 bottom-10 left-10 space-y-2 text-center">
        <p class="text-sm text-ink-300" dir="ltr">One Good Coffee, One Good Cafe</p>
        <p class="text-xs text-ink-500">هر روز ۸:۳۰ تا ۲۳:۳۰ · یزد</p>
      </div>
    </div>

    <!-- Form side -->
    <div class="relative flex items-center justify-center px-6 py-16">
      <div class="absolute inset-0 bg-[radial-gradient(50%_40%_at_50%_0%,rgba(255,79,26,0.12),transparent)] lg:hidden" />
      <form class="relative w-full max-w-sm animate-rise" :class="rejected ? 'is-rejected' : ''" @submit.prevent="submit">
        <div class="mb-12 flex justify-center text-bone lg:hidden"><OneLogo :size="64" with-wordmark animated /></div>

        <p class="mask-line label-caps"><span>پنل مدیریت</span></p>
        <h1 class="mask-line mt-3 text-4xl font-black text-bone"><span class="[animation-delay:100ms]">خوش برگشتی</span></h1>
        <p class="mask-line mt-2 text-sm text-ink-400"><span class="[animation-delay:200ms]">برای ورود، ایمیل و رمز حساب کافه را وارد کن.</span></p>

        <div class="mt-10 space-y-4">
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">ایمیل یا نام کاربری</span>
            <input
              v-model="usr"
              class="field field-glow h-12"
              dir="ltr"
              autocomplete="username"
              autocapitalize="off"
              spellcheck="false"
              autofocus
              required
              @invalid="requiredMessage"
              @input="clearMessage"
            />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">رمز عبور</span>
            <div class="field-glow relative rounded-xl">
              <input
                v-model="pwd"
                :type="reveal ? 'text' : 'password'"
                class="field h-12 pl-11"
                dir="ltr"
                autocomplete="current-password"
                required
                @invalid="requiredMessage"
                @input="clearMessage"
                @keyup="trackCaps"
                @keydown="trackCaps"
              />
              <button
                type="button"
                data-sfx="toggle"
                class="absolute inset-y-0 left-0 grid w-11 place-items-center rounded-xl text-ink-400 transition hover:text-ink-100"
                :title="reveal ? 'پنهان کردن رمز' : 'نمایش رمز'"
                :aria-label="reveal ? 'پنهان کردن رمز' : 'نمایش رمز'"
                @click="reveal = !reveal"
              >
                <component :is="reveal ? EyeOff : Eye" class="size-4" />
              </button>
            </div>
            <Transition enter-active-class="animate-rise">
              <p v-if="capsLock" class="mt-2 text-xs text-amber-300">کلید Caps Lock روشن است.</p>
            </Transition>
          </label>
        </div>

        <Transition enter-active-class="animate-rise">
          <p v-if="error" class="mt-5 flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-400/[0.07] px-3.5 py-3 text-sm text-rose-400" role="alert">
            <TriangleAlert class="mt-0.5 size-4 shrink-0" />
            <span>{{ error }}</span>
          </p>
        </Transition>

        <button class="btn-primary mt-8 h-12 w-full text-base" :disabled="!canSubmit">
          <template v-if="loading"><LoaderCircle class="size-5 animate-spin" /> در حال ورود…</template>
          <template v-else>ورود <ArrowLeft class="size-4" /></template>
        </button>

        <p class="mt-10 text-center text-xs text-ink-500">یزد · بلوار دانشگاه · کوچه فرساد</p>
      </form>
    </div>
  </div>
</template>
