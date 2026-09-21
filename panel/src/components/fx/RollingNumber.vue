<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { sound } from '@/lib/sound'

/** Slot-machine digits: each digit column rolls to its value independently. */
const props = defineProps<{ value: number; format: (value: number) => string }>()

const DIGITS = '۰۱۲۳۴۵۶۷۸۹'
const ready = ref(false)
const rolling = ref(false)
let settle: number | undefined

/** While the columns move, the whole number glows a little. */
function roll() {
  sound.roll()
  rolling.value = true
  clearTimeout(settle)
  settle = window.setTimeout(() => (rolling.value = false), 1400)
}

onMounted(() =>
  requestAnimationFrame(() => {
    ready.value = true
    roll()
  }),
)
watch(() => props.value, roll)
onBeforeUnmount(() => clearTimeout(settle))

const text = computed(() => props.format(props.value))
// keyed from the right so columns keep their identity when the number grows
const chars = computed(() => [...text.value].map((char, i, all) => ({ char, digit: DIGITS.indexOf(char), key: all.length - i })))
</script>

<template>
  <span class="rolling num" :class="rolling ? 'is-rolling' : ''" dir="ltr" :aria-label="text">
    <template v-for="c in chars" :key="c.key">
      <span v-if="c.digit >= 0" class="rolling-col" aria-hidden="true">
        <span class="rolling-strip" :style="{ transform: `translateY(${ready ? -c.digit * 10 : 0}%)`, transitionDelay: `${c.key * 45}ms` }">
          <span v-for="d in DIGITS" :key="d">{{ d }}</span>
        </span>
      </span>
      <span v-else class="rolling-sep" aria-hidden="true">{{ c.char }}</span>
    </template>
  </span>
</template>
