import { ref, watch } from 'vue'

/**
 * The panel's sound design, synthesized with WebAudio (no audio files).
 * Everything runs through one mix bus: a soft room reverb and a compressor so
 * layered sounds never clip. Frequent sounds are rate-limited so nothing gets noisy.
 */

const KEY = 'one-sound'

function readPreference() {
  try {
    return localStorage.getItem(KEY) !== 'off'
  } catch {
    return true
  }
}

export const soundOn = ref(readPreference())
watch(soundOn, (on) => {
  try {
    localStorage.setItem(KEY, on ? 'on' : 'off')
  } catch {
    // storage unavailable (private mode) — keep the in-memory preference
  }
})

// ---------------------------------------------------------------- mix bus

let context: AudioContext | null = null
let dry: GainNode | null = null
let wet: GainNode | null = null
let noiseBuffer: AudioBuffer | null = null

function roomImpulse(ctx: AudioContext, seconds: number, decay: number) {
  const length = Math.floor(ctx.sampleRate * seconds)
  const buffer = ctx.createBuffer(2, length, ctx.sampleRate)
  for (let channel = 0; channel < 2; channel++) {
    const data = buffer.getChannelData(channel)
    for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay)
  }
  return buffer
}

function audio() {
  if (!soundOn.value) return null
  if (!context) {
    context = new AudioContext()
    const compressor = context.createDynamicsCompressor()
    compressor.threshold.value = -16
    compressor.ratio.value = 5
    compressor.connect(context.destination)

    dry = context.createGain()
    dry.gain.value = 0.9
    dry.connect(compressor)

    const reverb = context.createConvolver()
    reverb.buffer = roomImpulse(context, 1.8, 3)
    wet = context.createGain()
    wet.gain.value = 0.22
    wet.connect(reverb).connect(dry)

    noiseBuffer = context.createBuffer(1, context.sampleRate * 2, context.sampleRate)
    const samples = noiseBuffer.getChannelData(0)
    for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1
  }
  if (context.state === 'suspended') void context.resume()
  return context
}

function route(ctx: AudioContext, node: AudioNode, reverb: boolean, pan: number) {
  let tail = node
  if (pan) {
    const panner = ctx.createStereoPanner()
    panner.pan.value = pan
    tail.connect(panner)
    tail = panner
  }
  tail.connect(dry!)
  if (reverb) tail.connect(wet!)
}

// ---------------------------------------------------------------- voices

type ToneOptions = {
  type?: OscillatorType
  gain?: number
  attack?: number
  slideTo?: number
  delay?: number
  reverb?: boolean
  pan?: number
}

function tone(frequency: number, duration: number, options: ToneOptions = {}) {
  const ctx = audio()
  if (!ctx) return
  const { type = 'sine', gain = 0.05, attack = 0.004, slideTo, delay = 0, reverb = false, pan = 0 } = options
  const at = ctx.currentTime + delay
  const osc = ctx.createOscillator()
  const amp = ctx.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(frequency, at)
  if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, at + duration)
  amp.gain.setValueAtTime(0.0001, at)
  amp.gain.exponentialRampToValueAtTime(gain, at + attack)
  amp.gain.exponentialRampToValueAtTime(0.0001, at + duration)
  osc.connect(amp)
  route(ctx, amp, reverb, pan)
  osc.start(at)
  osc.stop(at + duration + 0.05)
}

type NoiseOptions = { gain?: number; from?: number; to?: number; q?: number; delay?: number; reverb?: boolean; filter?: BiquadFilterType }

function hiss(duration: number, options: NoiseOptions = {}) {
  const ctx = audio()
  if (!ctx || !noiseBuffer) return
  const { gain = 0.04, from = 800, to = 3000, q = 0.8, delay = 0, reverb = false, filter = 'bandpass' } = options
  const at = ctx.currentTime + delay
  const source = ctx.createBufferSource()
  source.buffer = noiseBuffer
  const band = ctx.createBiquadFilter()
  band.type = filter
  band.Q.value = q
  band.frequency.setValueAtTime(from, at)
  band.frequency.exponentialRampToValueAtTime(to, at + duration)
  const amp = ctx.createGain()
  amp.gain.setValueAtTime(0.0001, at)
  amp.gain.exponentialRampToValueAtTime(gain, at + Math.max(0.005, duration * 0.25))
  amp.gain.exponentialRampToValueAtTime(0.0001, at + duration)
  source.connect(band).connect(amp)
  route(ctx, amp, reverb, 0)
  source.start(at, Math.random())
  source.stop(at + duration + 0.05)
}

const lastPlayed = new Map<string, number>()
/** Rate limit: true if `key` hasn't played in the last `ms`. */
function allow(key: string, ms: number) {
  const now = performance.now()
  if (now - (lastPlayed.get(key) ?? -Infinity) < ms) return false
  lastPlayed.set(key, now)
  return true
}

/** Frequency `semitones` above C5. */
const pitch = (semitones: number) => 523.25 * 2 ** (semitones / 12)
const PENTATONIC = [0, 2, 4, 7, 9]

function sparkle(delay = 0, count = 3) {
  for (let i = 0; i < count; i++) {
    tone(2800 + Math.random() * 2600, 0.09, { gain: 0.008, delay: delay + Math.random() * 0.07, reverb: true, pan: Math.random() * 1.2 - 0.6 })
  }
}

function arpeggio(semitones: number[], { gap = 0.07, gain = 0.04, type = 'triangle' as OscillatorType } = {}) {
  semitones.forEach((s, i) => tone(pitch(s), 0.35, { type, gain, delay: i * gap, reverb: true }))
}

export const sound = {
  // ---- interaction
  hover() {
    if (allow('hover', 45)) tone(2300 + Math.random() * 200, 0.03, { gain: 0.009 })
  },
  tap() {
    if (!allow('tap', 30)) return
    tone(1400, 0.045, { type: 'triangle', gain: 0.035, slideTo: 950 })
    hiss(0.02, { gain: 0.012, from: 5000, to: 4000 })
  },
  press() {
    if (!allow('tap', 30)) return
    tone(520, 0.09, { gain: 0.07, slideTo: 260 })
    tone(1560, 0.05, { type: 'triangle', gain: 0.018 })
    sparkle(0.02)
  },
  nav() {
    tone(880, 0.07, { gain: 0.03, reverb: true })
    tone(1318.5, 0.09, { gain: 0.024, delay: 0.035, reverb: true })
  },
  toggle() {
    tone(1200, 0.03, { type: 'triangle', gain: 0.03 })
    tone(1800, 0.035, { type: 'triangle', gain: 0.025, delay: 0.035 })
  },
  focus() {
    if (allow('focus', 120)) tone(1760, 0.06, { gain: 0.014, reverb: true })
  },

  // ---- space
  page() {
    hiss(0.5, { gain: 0.03, from: 300, to: 1800, reverb: true })
    tone(110, 0.45, { gain: 0.045, slideTo: 220, attack: 0.08 })
    sparkle(0.32, 2)
  },
  open() {
    tone(440, 0.18, { gain: 0.045, slideTo: 880, reverb: true })
    hiss(0.14, { gain: 0.018, from: 1200, to: 3200 })
  },
  close() {
    tone(880, 0.16, { gain: 0.035, slideTo: 440 })
  },
  whoosh() {
    hiss(0.35, { gain: 0.045, from: 500, to: 2600, reverb: true })
  },
  whooshOut() {
    hiss(0.3, { gain: 0.035, from: 2600, to: 450 })
  },
  neon() {
    if (!allow('neon', 900)) return
    for (let i = 0; i < 3; i++) {
      tone(118 + Math.random() * 6, 0.035, { type: 'sawtooth', gain: 0.022, delay: i * 0.06 + Math.random() * 0.03 })
    }
    hiss(0.12, { gain: 0.01, from: 1800, to: 1900, q: 3 })
  },
  introDraw() {
    hiss(1.1, { gain: 0.012, from: 4000, to: 8000, reverb: true })
    tone(220, 1.2, { gain: 0.03, slideTo: 440, attack: 0.3, reverb: true })
  },

  // ---- assistant
  send() {
    tone(660, 0.09, { type: 'triangle', gain: 0.045, slideTo: 1320 })
    sparkle(0.05, 2)
  },
  reply() {
    tone(1318.5, 0.3, { gain: 0.032, reverb: true })
    tone(1760, 0.35, { gain: 0.026, delay: 0.07, reverb: true })
  },
  typing() {
    if (allow('typing', 55)) tone(2100 + Math.random() * 500, 0.018, { type: 'triangle', gain: 0.008 })
  },
  stamp() {
    tone(120, 0.22, { gain: 0.16, slideTo: 55 })
    hiss(0.08, { gain: 0.06, from: 2200, to: 700, q: 0.5 })
    sparkle(0.12, 4)
  },
  dismiss() {
    tone(600, 0.12, { gain: 0.03, slideTo: 300 })
  },

  // ---- notifications
  success() {
    tone(988, 0.35, { type: 'triangle', gain: 0.045, reverb: true })
    tone(1245, 0.5, { type: 'triangle', gain: 0.04, delay: 0.09, reverb: true })
  },
  error() {
    if (!allow('error', 250)) return
    tone(220, 0.07, { type: 'square', gain: 0.022 })
    tone(196, 0.09, { type: 'square', gain: 0.022, delay: 0.1 })
  },
  info() {
    tone(1046.5, 0.14, { gain: 0.03, reverb: true })
  },

  // ---- register
  add(quantity = 1) {
    tone(1500 * 2 ** (Math.min(quantity - 1, 8) / 12), 0.05, { type: 'triangle', gain: 0.04 })
    tone(180, 0.04, { gain: 0.05 })
  },
  remove() {
    tone(900, 0.07, { type: 'triangle', gain: 0.035, slideTo: 560 })
  },
  clear() {
    hiss(0.35, { gain: 0.04, from: 2400, to: 400 })
    tone(500, 0.25, { gain: 0.03, slideTo: 200 })
  },
  register() {
    // the "ka-ching": a short metallic strike, then a bright bell
    hiss(0.05, { gain: 0.05, from: 6500, to: 5000, q: 2 })
    for (const f of [2093, 2637, 3136]) tone(f, 0.5, { type: 'triangle', gain: 0.022, reverb: true })
    for (const f of [2637, 3520, 4186]) tone(f, 0.7, { type: 'sine', gain: 0.02, delay: 0.09, reverb: true })
    tone(988, 0.4, { type: 'triangle', gain: 0.035, delay: 0.16, reverb: true })
  },
  shiftOpen() {
    arpeggio([0, 4, 7, 12])
  },
  shiftClose() {
    arpeggio([12, 7, 4, 0])
  },

  // ---- data
  roll() {
    if (!allow('roll', 700)) return
    for (let i = 0; i < 7; i++) tone(2600 - i * 90, 0.02, { type: 'triangle', gain: 0.012 * (1 - i / 9), delay: i * 0.045 })
  },
  note(index: number) {
    if (!allow('note', 40)) return
    const semis = PENTATONIC[index % 5] + 12 * Math.floor(index / 5) - 12
    tone(pitch(semis), 0.3, { gain: 0.028, reverb: true })
  },
  bubble() {
    if (allow('bubble', 60)) tone(600 + Math.random() * 300, 0.07, { gain: 0.025, slideTo: 1100 + Math.random() * 300 })
  },

  // ---- system
  enable() {
    arpeggio([7, 12], { gap: 0.08, gain: 0.035, type: 'sine' })
  },
  welcome() {
    arpeggio([0, 7, 12, 16], { gap: 0.09, gain: 0.035 })
    sparkle(0.3, 4)
  },
}

export const vibrate = (ms = 8) => navigator.vibrate?.(ms)

// ---------------------------------------------------------------- automatic UI sounds

const INTERACTIVE = 'button, a[href], [role="button"], [data-ripple], select, summary, input[type="checkbox"], input[type="radio"]'

/** Named sounds an element can request with data-sfx="…" ("none" silences it). */
const NAMED: Record<string, () => void> = {
  none: () => undefined,
  toggle: sound.toggle,
  send: sound.send,
  clear: sound.clear,
  press: sound.press,
  tap: sound.tap,
  nav: sound.nav,
  dismiss: sound.dismiss,
}

/**
 * Hover, press and focus sounds for every control, via event delegation.
 * Components only add sounds for meaning (a sale, a stamp); the basics come from here.
 */
export function installSoundEvents() {
  let hovered: Element | null = null

  document.addEventListener(
    'pointerover',
    (event) => {
      if (event.pointerType !== 'mouse') return
      const target = event.target as Element
      const el = target.closest?.(INTERACTIVE) ?? target.closest?.('.logo-link') ?? null
      if (el === hovered) return
      hovered = el
      if (!el || el.matches(':disabled') || el.getAttribute('data-sfx') === 'none') return
      if (el.closest('.logo-link')) sound.neon()
      else sound.hover()
    },
    { passive: true },
  )

  document.addEventListener(
    'pointerdown',
    (event) => {
      if (event.button > 0) return
      const el = (event.target as Element).closest?.(INTERACTIVE) as HTMLElement | null
      if (!el || el.matches(':disabled')) return
      const named = el.dataset.sfx
      if (named) return (NAMED[named] ?? sound.tap)()
      if (el.matches('.btn-primary')) sound.press()
      else if (el.closest('aside nav')) sound.nav()
      else sound.tap()
    },
    { passive: true },
  )

  document.addEventListener('focusin', (event) => {
    if ((event.target as Element).matches?.('input:not([type="checkbox"]):not([type="radio"]), textarea, select')) sound.focus()
  })

  // native form validation ("این فیلد را پر کن")
  document.addEventListener('invalid', () => sound.error(), true)
}
