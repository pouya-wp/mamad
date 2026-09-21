import { nextTick } from 'vue'
import type { Router } from 'vue-router'

import { fxLite } from './motion'

/**
 * Animated route changes with the View Transitions API: the old page sinks and fades,
 * the new one wipes up like a curtain and a neon line sweeps under the header.
 * The sidebar and header have their own view-transition-names, so they stay put.
 */
export const pageTransitions = !fxLite && typeof document.startViewTransition === 'function'

export function installPageTransitions(router: Router) {
  if (!pageTransitions) return

  const root = document.documentElement
  let showNewPage: (() => void) | null = null

  router.beforeResolve((to, from) => {
    const animate = !document.hidden && from.matched.length > 0 && to.path !== from.path && !to.meta.public && !from.meta.public
    if (!animate) return

    // resolves once the browser has captured the old page, so navigation can continue
    return new Promise<void>((oldCaptured) => {
      root.classList.add('vt-route')
      const transition = document.startViewTransition(
        () =>
          new Promise<void>((newPageReady) => {
            showNewPage = newPageReady
            oldCaptured()
          }),
      )
      transition.ready.catch(() => undefined)
      transition.finished.finally(() => root.classList.remove('vt-route', 'vt-sweep'))
    })
  })

  router.afterEach(async () => {
    if (!showNewPage) return
    const done = showNewPage
    showNewPage = null
    root.classList.add('vt-sweep') // only the new snapshot carries the neon line
    await nextTick()
    done()
  })
}
