<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { sound } from '@/lib/sound'

/** Reveals an answer word by word (never mid-word, so Persian letters stay joined) behind a neon caret. */
const props = defineProps<{ text: string; animate?: boolean }>()
const emit = defineEmits<{ done: [] }>()

const tokens = computed(() => props.text.split(/(\s+)/))
const shown = ref(props.animate ? 0 : tokens.value.length)
let timer = 0

onMounted(() => {
  if (!props.animate) return emit('done')
  timer = window.setInterval(() => {
    shown.value += 1
    if (shown.value % 2 === 0) sound.typing()
    if (shown.value < tokens.value.length) return
    clearInterval(timer)
    emit('done')
  }, 22)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <p class="whitespace-pre-line">
    {{ tokens.slice(0, shown).join('') }}<span v-if="shown < tokens.length" class="type-caret" />
  </p>
</template>
