import { defineStore } from 'pinia'
import { ref } from 'vue'

import { ApiError, get, post, setCsrfToken } from '@/lib/api'

export type CafeContext = {
  company: string
  pos_profile?: string
  warehouse?: string
  customer?: string
  price_list?: string
  currency?: string
}

type Boot = {
  csrf_token: string
  user: { name: string; full_name: string; image?: string; roles: string[] }
  cafe: CafeContext
}

export const useSession = defineStore('session', () => {
  const user = ref<Boot['user'] | null>(null)
  const cafe = ref<CafeContext | null>(null)
  const checked = ref(false)
  /** Set by a real sign-in, so the shell plays the intro again after login. */
  const justLoggedIn = ref(false)

  async function boot() {
    try {
      const data = await get<Boot>('cafe_app.api.session.boot')
      setCsrfToken(data.csrf_token)
      user.value = data.user
      cafe.value = data.cafe
    } catch (error) {
      if (!(error instanceof ApiError && error.isAuthError)) throw error
      user.value = null
    } finally {
      checked.value = true
    }
    return !!user.value
  }

  async function login(usr: string, pwd: string) {
    await post('login', { usr, pwd })
    justLoggedIn.value = true
    return boot()
  }

  async function logout() {
    await post('logout').catch(() => undefined)
    setCsrfToken('')
    user.value = null
    cafe.value = null
  }

  const hasRole = (...roles: string[]) =>
    !!user.value && (user.value.name === 'Administrator' || roles.some((r) => user.value!.roles.includes(r)))

  return { user, cafe, checked, justLoggedIn, boot, login, logout, hasRole }
})
