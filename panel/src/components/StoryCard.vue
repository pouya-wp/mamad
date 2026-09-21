<script setup lang="ts">
import { Copy, Download, LoaderCircle } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import Modal from '@/components/Modal.vue'
import { jDate } from '@/lib/format'
import { sound } from '@/lib/sound'
import { drawStory, storyBlob } from '@/lib/story'
import { toast, toastError } from '@/lib/toast'
import type { DashboardSummary } from '@/lib/types'

/**
 * The café's numbers, ready to post: a 1080×1920 story drawn in the brand's own
 * black-and-orange, downloadable or straight into the clipboard.
 */
const open = defineModel<boolean>({ required: true })
const props = defineProps<{ data: DashboardSummary; label: string }>()

const canvas = ref<HTMLCanvasElement>()
const busy = ref(false)

const story = computed(() => {
  const top = props.data.top_items[0]
  const peak = [...props.data.hourly].sort((a, b) => b.orders - a.orders)[0]
  const kpis = props.data.kpis
  return {
    label: props.label,
    date: jDate(props.data.range.to),
    revenue: kpis.revenue,
    orders: kpis.orders,
    topItem: top?.item_name,
    topQty: top?.qty,
    peakHour: peak?.orders ? peak.hour : undefined,
    margin: kpis.revenue ? (kpis.gross_profit / kpis.revenue) * 100 : undefined,
  }
})

async function render() {
  if (!canvas.value) return
  busy.value = true
  await drawStory(canvas.value, story.value)
  busy.value = false
}

watch(open, async (value) => {
  if (!value) return
  // the canvas only exists once the modal is in the DOM
  await new Promise((resolve) => setTimeout(resolve, 60))
  render()
})
watch(() => props.data, render)

async function download() {
  const blob = canvas.value && (await storyBlob(canvas.value))
  if (!blob) return
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `one-cafe-${props.data.range.to}.png`
  link.click()
  URL.revokeObjectURL(url)
  sound.register()
  toast('استوری ذخیره شد', 'success', 3800, false)
}

async function copy() {
  try {
    const blob = canvas.value && (await storyBlob(canvas.value))
    if (!blob) return
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    sound.success()
    toast('کپی شد — مستقیم بچسبان توی اینستاگرام', 'success', 3800, false)
  } catch (error) {
    toastError(error)
  }
}
</script>

<template>
  <Modal v-model="open" title="استوری کافه" width="max-w-md">
    <div class="relative mx-auto w-[260px] overflow-hidden rounded-2xl border border-white/10 shadow-2xl shadow-black">
      <canvas ref="canvas" class="block w-full" />
      <div v-if="busy" class="absolute inset-0 grid place-items-center bg-black/60">
        <LoaderCircle class="size-6 animate-spin text-one-500" />
      </div>
    </div>
    <p class="mt-4 text-center text-xs text-ink-400">۱۰۸۰×۱۹۲۰ — اندازه‌ی استوری اینستاگرام</p>

    <template #footer>
      <button class="btn-ghost" @click="copy"><Copy class="size-4" /> کپی</button>
      <button class="btn-primary" @click="download"><Download class="size-4" /> دانلود</button>
    </template>
  </Modal>
</template>
