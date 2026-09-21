/**
 * Global interaction effects: hover light, page aura, magnetic buttons, 3D tilt and
 * scroll reveal. All pointer work is batched into one animation frame and only touches
 * the element under the pointer — never the document root, which would restyle the whole page.
 */

export const fxLite = (() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const weakCpu = (navigator.hardwareConcurrency ?? 8) <= 4
  const saveData = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData === true
  return reduced || weakCpu || saveData
})()

/** Pointer position normalised to 0..1 (y up), read by the WebGL shaders. */
export const pointer = { x: 0.5, y: 0.5 }

const LIGHT = '.card, .spotlight, .btn, .btn-primary, .btn-ghost, [data-ripple]'
const MAGNETIC = '.btn-primary, [data-magnetic]'

let pending: PointerEvent | null = null
let frame = 0
let magnetEl: HTMLElement | null = null
let tiltEl: HTMLElement | null = null

function magnet(event: PointerEvent) {
  const el = (event.target as Element | null)?.closest?.(MAGNETIC) as HTMLElement | null
  if (magnetEl && magnetEl !== el) magnetEl.style.translate = ''
  magnetEl = el
  if (!el || el.matches(':disabled')) return

  const rect = el.getBoundingClientRect()
  const dx = event.clientX - (rect.left + rect.width / 2)
  const dy = event.clientY - (rect.top + rect.height / 2)
  // wide buttons move less, so a full-width button doesn't slide around
  const strength = Number(el.dataset.magnetic || 0.3) * Math.min(1, 72 / Math.max(rect.width, rect.height))
  el.style.translate = `${dx * strength}px ${dy * strength * 1.3}px`
}

function tilt(event: PointerEvent) {
  const el = (event.target as Element | null)?.closest?.('[data-tilt]') as HTMLElement | null
  if (tiltEl && tiltEl !== el) {
    for (const prop of ['--rx', '--ry', '--px', '--py']) tiltEl.style.removeProperty(prop)
    tiltEl.classList.remove('is-tilting')
  }
  tiltEl = el
  if (!el) return

  const rect = el.getBoundingClientRect()
  const nx = (event.clientX - rect.left) / rect.width - 0.5
  const ny = (event.clientY - rect.top) / rect.height - 0.5
  const max = Number(el.dataset.tilt || 8)
  el.style.setProperty('--rx', `${(-ny * max).toFixed(2)}deg`)
  el.style.setProperty('--ry', `${(nx * max).toFixed(2)}deg`)
  el.style.setProperty('--px', nx.toFixed(3))
  el.style.setProperty('--py', ny.toFixed(3))
  el.classList.add('is-tilting')
}

function onFrame() {
  frame = 0
  const event = pending
  pending = null
  if (!event) return

  const lit = (event.target as Element | null)?.closest?.(LIGHT) as HTMLElement | null
  if (lit) {
    const rect = lit.getBoundingClientRect()
    lit.style.setProperty('--mx', `${event.clientX - rect.left}px`)
    lit.style.setProperty('--my', `${event.clientY - rect.top}px`)
  }
  if (!fxLite && event.pointerType === 'mouse') {
    magnet(event)
    tilt(event)
  }
}

// ---- page aura: a soft light that eases after the pointer (transform only, GPU-composited)
const aura = { x: 0, y: 0, tx: 0, ty: 0, placed: false, raf: 0 }

function moveAura() {
  const el = document.querySelector<HTMLElement>('[data-aura]')
  if (!el) {
    aura.raf = 0
    return
  }
  aura.x += (aura.tx - aura.x) * 0.12
  aura.y += (aura.ty - aura.y) * 0.12
  el.style.transform = `translate3d(${aura.x}px, ${aura.y}px, 0) translate(-50%, -50%)`
  const settled = Math.abs(aura.tx - aura.x) < 0.5 && Math.abs(aura.ty - aura.y) < 0.5
  aura.raf = settled ? 0 : requestAnimationFrame(moveAura)
}

function installReveal() {
  if (!('IntersectionObserver' in window)) return
  document.documentElement.classList.add('fx-reveal')

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        entry.target.classList.add('is-revealed')
        observer.unobserve(entry.target)
      }
    },
    // starts a touch before the element enters, so a fast scroll never lands on a blank card
    { rootMargin: '0px 0px 6% 0px', threshold: 0 },
  )
  const scan = (node: ParentNode) => node.querySelectorAll('[data-reveal]:not(.is-revealed)').forEach((el) => observer.observe(el))

  scan(document)
  new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof Element)) return
        if (node.matches('[data-reveal]')) observer.observe(node)
        scan(node)
      })
    }
  }).observe(document.body, { childList: true, subtree: true })
}

export function installMotion() {
  document.documentElement.dataset.fx = fxLite ? 'lite' : 'full'

  document.addEventListener(
    'pointermove',
    (event) => {
      pointer.x = event.clientX / window.innerWidth
      pointer.y = 1 - event.clientY / window.innerHeight
      pending = event
      if (!frame) frame = requestAnimationFrame(onFrame)

      aura.tx = event.clientX
      aura.ty = event.clientY
      if (!aura.placed) {
        aura.x = aura.tx
        aura.y = aura.ty
        aura.placed = true
      }
      if (!aura.raf) aura.raf = requestAnimationFrame(moveAura)
    },
    { passive: true },
  )

  installReveal()
}
