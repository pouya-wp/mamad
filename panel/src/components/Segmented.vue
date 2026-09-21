<script setup lang="ts" generic="T extends string">
import { nextTick, onMounted, ref, watch } from 'vue'

const model = defineModel<T>({ required: true })
const props = defineProps<{ options: { value: T; label: string }[] }>()

const buttons = ref<HTMLButtonElement[]>([])
const pill = ref({ left: 0, width: 0, ready: false })

/** Slide the highlight under the selected option. */
async function measure() {
  await nextTick()
  const button = buttons.value[props.options.findIndex((o) => o.value === model.value)]
  if (button) pill.value = { left: button.offsetLeft, width: button.offsetWidth, ready: true }
}

onMounted(measure)
watch([model, () => props.options], measure)
</script>

<template>
  <div class="relative inline-flex rounded-xl border border-white/10 bg-ink-900 p-1 shadow-[inset_0_2px_6px_-2px_rgba(0,0,0,0.6)]">
    <span
      class="absolute top-1 bottom-1 left-0 rounded-lg bg-bone shadow-[0_6px_20px_-6px_rgba(245,242,236,0.45)]"
      :style="{
        width: `${pill.width}px`,
        transform: `translateX(${pill.left}px)`,
        opacity: pill.ready ? 1 : 0,
        transition: 'transform 0.55s var(--ease-spring), width 0.55s var(--ease-spring), opacity 0.2s',
      }"
    />
    <button
      v-for="o in options"
      :key="o.value"
      ref="buttons"
      data-ripple
      data-sfx="toggle"
      class="z-10 rounded-lg px-3.5 py-1.5 text-sm transition-colors duration-300"
      :class="model === o.value ? 'font-medium text-ink-950' : 'text-ink-300 hover:text-ink-100'"
      @click="model = o.value"
    >
      {{ o.label }}
    </button>
  </div>
</template>
