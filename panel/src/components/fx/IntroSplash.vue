<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import OneLogo from '@/components/OneLogo.vue'
import { fxLite } from '@/lib/motion'
import { sound } from '@/lib/sound'
import { useSession } from '@/stores/session'

/**
 * The logo draws itself, the "1" flickers on like a neon tube, then an iris opens
 * onto the panel. It plays right after a sign-in, and once per browser session
 * on a cold load — on weak machines a short, cheap version of the same thing.
 */
const session = useSession()
const show = ref(false)
const opening = ref(false)
const timers: number[] = []

function coldStart() {
  try {
    if (sessionStorage.getItem('one-intro')) return false
    sessionStorage.setItem('one-intro', '1')
  } catch {
    // no storage: still play it
  }
  return true
}

/** A fresh sign-in always earns the full entrance, even in the same tab session. */
function shouldPlay() {
  if (!session.justLoggedIn) return coldStart()
  session.justLoggedIn = false
  try {
    sessionStorage.setItem('one-intro', '1')
  } catch {
    // ignore
  }
  return true
}

function open() {
  opening.value = true
  sound.whoosh()
  timers.push(window.setTimeout(() => (show.value = false), 1050))
}

onMounted(() => {
  if (!shouldPlay()) return
  show.value = true
  sound.introDraw()
  if (fxLite) return timers.push(window.setTimeout(open, 1200))
  // crackles in sync with the "1" flickering on (see the neon-flicker keyframes)
  timers.push(window.setTimeout(sound.neon, 1150))
  timers.push(window.setTimeout(open, 2300))
})
onBeforeUnmount(() => timers.forEach(clearTimeout))
</script>

<template>
  <template v-if="show">
    <div class="intro" :class="{ 'is-opening': opening }" @click="open">
      <div class="intro-logo flex flex-col items-center text-bone">
        <OneLogo :size="112" animated with-wordmark />
        <p class="intro-hint">در حال آماده‌سازی کافه…</p>
        <span class="intro-bar"><i /></span>
      </div>
    </div>
    <span class="intro-ring" :class="{ 'is-opening': opening }" />
  </template>
</template>
