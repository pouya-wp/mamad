<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { fxLite, GLSL_NOISE, runShader } from '@/lib/gl'

/** Rising coffee steam lit by the orange glow of the brand. */
const FRAGMENT = `${GLSL_NOISE}
void main() {
  vec2 uv = gl_FragCoord.xy / uRes;
  vec2 p = vec2((uv.x - 0.5) * uRes.x / uRes.y, uv.y);
  p.x += (uMouse.x - 0.5) * 0.08;
  float t = uTime * 0.07;
  vec2 q = vec2(fbm(p * 1.8 + vec2(0.0, -t * 3.0)), fbm(p * 1.8 + vec2(5.2, -t * 2.3)));
  float smoke = fbm(p * 2.4 + q * 2.0 + vec2(0.0, -t * 4.2));
  float sway = (q.x - 0.5) * 0.45 * uv.y;
  float column = smoothstep(0.55, 0.0, abs(p.x - sway));
  float fade = smoothstep(0.02, 0.35, uv.y) * smoothstep(1.05, 0.45, uv.y);
  float steam = smoothstep(0.42, 0.95, smoke * column * 1.25) * fade;
  float glow = smoothstep(0.95, 0.0, length(vec2(p.x * 1.1, uv.y + 0.12)));
  vec3 color = vec3(0.96, 0.93, 0.89) * steam * 0.28;
  color += vec3(1.0, 0.31, 0.10) * glow * (0.22 + 0.2 * smoke);
  color += vec3(1.0, 0.55, 0.35) * steam * glow * 0.35;
  gl_FragColor = vec4(color, 1.0);
}`

const canvas = ref<HTMLCanvasElement>()
const fallback = ref(fxLite)
let stop: (() => void) | null = null

onMounted(() => {
  if (fallback.value || !canvas.value) return
  stop = runShader(canvas.value, FRAGMENT, { scale: 0.6, fps: 40 })
  if (!stop) fallback.value = true
})
onBeforeUnmount(() => stop?.())
</script>

<template>
  <canvas v-if="!fallback" ref="canvas" class="absolute inset-0 size-full" />
  <div v-else class="absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_100%,rgba(255,79,26,0.3),transparent_70%)]" />
</template>
