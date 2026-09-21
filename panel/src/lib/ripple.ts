/**
 * Material 3 Expressive–style press feedback for every button in the panel:
 * a cursor-following hover light, and on press a ripple that dissolves into grain
 * while a few sparkles scatter from the touch point.
 *
 * Works through event delegation, so any `.btn*` or `[data-ripple]` element gets it.
 */

const SELECTOR = '.btn, .btn-primary, .btn-ghost, [data-ripple]'
const SPARKLES = 9

function target(event: Event) {
  const element = (event.target as Element | null)?.closest?.(SELECTOR) as HTMLElement | null
  if (!element || element.matches(':disabled, [aria-disabled="true"]')) return null
  return element
}

function press(event: PointerEvent) {
  const element = target(event)
  if (!element || event.button > 0) return

  const rect = element.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const radius = Math.hypot(Math.max(x, rect.width - x), Math.max(y, rect.height - y))

  const wave = document.createElement('span')
  wave.className = 'ripple-wave'
  Object.assign(wave.style, {
    left: `${x - radius}px`,
    top: `${y - radius}px`,
    width: `${radius * 2}px`,
    height: `${radius * 2}px`,
  })
  element.appendChild(wave)

  const spread = Math.min(Math.max(rect.width, rect.height), 220)
  for (let i = 0; i < SPARKLES; i++) {
    const sparkle = document.createElement('span')
    const angle = (Math.PI * 2 * i) / SPARKLES + Math.random() * 0.6
    const distance = spread * (0.25 + Math.random() * 0.35)
    const size = 2 + Math.random() * 3
    sparkle.className = i % 3 === 0 ? 'ripple-sparkle is-accent' : 'ripple-sparkle'
    Object.assign(sparkle.style, {
      left: `${x - size / 2}px`,
      top: `${y - size / 2}px`,
      width: `${size}px`,
      height: `${size}px`,
      animationDelay: `${Math.random() * 90}ms`,
    })
    sparkle.style.setProperty('--dx', `${Math.cos(angle) * distance}px`)
    sparkle.style.setProperty('--dy', `${Math.sin(angle) * distance}px`)
    element.appendChild(sparkle)
    sparkle.addEventListener('animationend', () => sparkle.remove(), { once: true })
  }

  wave.addEventListener('animationend', () => wave.remove(), { once: true })
}

export function installRipple() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  // the hover light position (--mx/--my) is tracked by motion.ts
  document.addEventListener('pointerdown', press, { passive: true })
}
