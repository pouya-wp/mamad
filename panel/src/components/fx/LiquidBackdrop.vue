<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { fxLite, GLSL_NOISE, runShader } from '@/lib/gl'

/** A dark espresso surface that barely moves; the pointer catches a warm sheen on it. */
const FRAGMENT = `${GLSL_NOISE}
void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  float aspect = uRes.x / uRes.y;
  vec2 p = uv * vec2(aspect, 1.0) * 1.3;
  float t = uTime * 0.035;
  vec2 q = vec2(fbm(p + vec2(t, 0.0)), fbm(p + vec2(1.7, 9.2) - t));
  vec2 r = vec2(fbm(p + 3.5 * q + vec2(8.3, 2.8) + t * 0.6), fbm(p + 3.5 * q + vec2(1.2, 5.4) - t * 0.4));
  float f = fbm(p + 2.5 * r);
  float sheen = pow(smoothstep(0.5, 0.95, f), 3.0);
  float light = smoothstep(0.55, 0.0, distance(uv * vec2(aspect, 1.0), uMouse * vec2(aspect, 1.0)));
  vec3 color = vec3(0.012, 0.008, 0.006) + vec3(0.07, 0.035, 0.016) * f * f;
  color += vec3(1.0, 0.33, 0.1) * sheen * (0.035 + 0.16 * light);
  gl_FragColor = vec4(color, 1.0);
}`

const canvas = ref<HTMLCanvasElement>()
const enabled = ref(!fxLite)
let stop: (() => void) | null = null

// Hold still while the page scrolls: the glass layers above re-blur on every canvas frame.
let scrollingUntil = 0
const onScroll = () => (scrollingUntil = performance.now() + 220)

onMounted(() => {
  if (!enabled.value || !canvas.value) return
  window.addEventListener('scroll', onScroll, { passive: true })
  stop = runShader(canvas.value, FRAGMENT, { scale: 0.35, fps: 24, paused: () => performance.now() < scrollingUntil })
  if (!stop) enabled.value = false
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  stop?.()
})
</script>

<template>
  <canvas v-if="enabled" ref="canvas" class="pointer-events-none fixed inset-0 -z-20 size-full" aria-hidden="true" />
</template>
