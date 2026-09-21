<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { watch } from 'vue'

import { sound } from '@/lib/sound'

const open = defineModel<boolean>({ required: true })
const props = withDefaults(
  defineProps<{
    title: string
    width?: string
    /** view-transition-name shared with the element that opened the modal, so it morphs out of it */
    morph?: string
  }>(),
  { width: 'max-w-lg' },
)

watch(open, (value) => {
  document.body.classList.toggle('overflow-hidden', value)
  if (value) sound.open()
  else sound.close()
})
</script>

<template>
  <Teleport to="body">
    <Transition
      :css="!props.morph"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
      enter-active-class="transition duration-300"
      leave-active-class="transition duration-200"
    >
      <div v-if="open" class="fixed inset-0 z-50 flex items-end justify-center bg-black/75 backdrop-blur-md sm:items-center sm:p-6" @click.self="open = false">
        <div
          class="card relative flex max-h-[92dvh] w-full flex-col overflow-hidden bg-ink-800 shadow-2xl shadow-black"
          :class="[width, morph ? '' : 'animate-pop']"
          :style="morph ? { viewTransitionName: morph } : undefined"
        >
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-l from-transparent via-one-500/60 to-transparent" />
          <header class="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
            <h3 class="font-bold text-bone">{{ title }}</h3>
            <button data-ripple class="rounded-lg p-1.5 text-ink-400 hover:bg-white/5 hover:text-ink-100" @click="open = false">
              <X class="size-5" />
            </button>
          </header>
          <div class="overflow-y-auto p-6"><slot /></div>
          <footer v-if="$slots.footer" class="flex items-center justify-end gap-2 border-t border-white/[0.06] bg-black/20 px-6 py-4">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
