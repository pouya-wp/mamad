import { fxLite, pointer } from './motion'

export { fxLite }

/** Value noise + fractal Brownian motion, shared by the shaders. */
export const GLSL_NOISE = `
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; }
  return v;
}
`

const HEADER = 'precision mediump float;\nuniform vec2 uRes;\nuniform float uTime;\nuniform vec2 uMouse;\n'
const VERTEX = 'attribute vec2 a;void main(){gl_Position=vec4(a,0.0,1.0);}'

type Options = {
  /** Render resolution relative to CSS pixels (lower = cheaper). */
  scale?: number
  fps?: number
  alpha?: boolean
  /** Extra float uniforms, read every frame. */
  uniforms?: Record<string, () => number>
  /** Skip frames while this returns true (e.g. during scroll). */
  paused?: () => boolean
}

function compile(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type)!
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader
  console.warn('[gl]', gl.getShaderInfoLog(shader))
  return null
}

/**
 * Draw a full-screen fragment shader into a canvas. Pauses while the tab is hidden.
 * Returns a stop function, or null when WebGL is unavailable (callers show a CSS fallback).
 */
export function runShader(canvas: HTMLCanvasElement, fragment: string, options: Options = {}) {
  const { scale = 1, fps = 60, alpha = false, uniforms = {}, paused } = options
  const gl = canvas.getContext('webgl', { alpha, antialias: false, depth: false, premultipliedAlpha: false, powerPreference: 'low-power' })
  if (!gl) return null

  const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX)
  const frag = compile(gl, gl.FRAGMENT_SHADER, HEADER + fragment)
  if (!vertex || !frag) return null
  const program = gl.createProgram()!
  gl.attachShader(program, vertex)
  gl.attachShader(program, frag)
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null
  gl.useProgram(program)

  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer())
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
  const position = gl.getAttribLocation(program, 'a')
  gl.enableVertexAttribArray(position)
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)

  const uRes = gl.getUniformLocation(program, 'uRes')
  const uTime = gl.getUniformLocation(program, 'uTime')
  const uMouse = gl.getUniformLocation(program, 'uMouse')
  const custom = Object.entries(uniforms).map(([name, read]) => [gl.getUniformLocation(program, name), read] as const)

  const resize = () => {
    const ratio = Math.min(window.devicePixelRatio || 1, 2) * scale
    const width = Math.max(1, Math.round(canvas.clientWidth * ratio))
    const height = Math.max(1, Math.round(canvas.clientHeight * ratio))
    if (canvas.width === width && canvas.height === height) return
    canvas.width = width
    canvas.height = height
    gl.viewport(0, 0, width, height)
  }
  const observer = new ResizeObserver(resize)
  observer.observe(canvas)
  resize()

  const start = performance.now()
  let last = 0
  let raf = 0
  const draw = (now: number) => {
    raf = requestAnimationFrame(draw)
    if (document.hidden || paused?.() || now - last < 1000 / fps) return
    last = now
    gl.uniform2f(uRes, canvas.width, canvas.height)
    gl.uniform1f(uTime, (now - start) / 1000)
    gl.uniform2f(uMouse, pointer.x, pointer.y)
    for (const [location, read] of custom) gl.uniform1f(location, read())
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
  }
  raf = requestAnimationFrame(draw)

  return () => {
    cancelAnimationFrame(raf)
    observer.disconnect()
    gl.getExtension('WEBGL_lose_context')?.loseContext()
  }
}
