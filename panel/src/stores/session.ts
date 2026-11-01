import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

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
  user: {
    name: string
    full_name: string
    image?: string
    roles: string[]
    /** set for a restaurant/café purchase manager, who only gets the purchase register */
    buyer_scope?: 'Restaurant' | 'Cafe' | null
    buyer_scope_label?: string | null
    buyer_scopes?: ('Restaurant' | 'Cafe')[]
    is_buyer?: boolean
  }
  cafe: CafeContext
}

export const useSession = defineStore('session', () => {
  const user = ref<Boot['user'] | null>(null)
  const cafe = ref<CafeContext | null>(null)
  const checked = ref(false)
  const bootNetworkError = ref(false)
  /** Set by a real sign-in, so the shell plays the intro again after login. */
  const justLoggedIn = ref(false)

  async function boot() {
    try {
      // A stalled network must not keep the desktop window blank indefinitely.
      const data = await get<Boot>('cafe_app.api.session.boot', undefined, 6000)
      bootNetworkError.value = false
      setCsrfToken(data.csrf_token)
      user.value = data.user
      cafe.value = data.cafe
    } catch (error) {
      if (!(error instanceof ApiError && error.isAuthError)) {
        bootNetworkError.value = true
        throw error
      }
      bootNetworkError.value = false
      user.value = null
    } finally {
      checked.value = true
    }
    return !!user.value
  }

  async function login(usr: string, pwd: string) {
    await post('login', { usr, pwd })
    const ready = await boot()
    if (!ready) throw new ApiError('نشست ورود برقرار نشد؛ دوباره تلاش کن.', 401)
    justLoggedIn.value = true
    return ready
  }

  async function logout() {
    await post('logout').catch(() => undefined)
    setCsrfToken('')
    user.value = null
    cafe.value = null
  }

  const hasRole = (...roles: string[]) =>
    !!user.value && (user.value.name === 'Administrator' || roles.some((r) => user.value!.roles.includes(r)))

  const buyerScope = computed(() => user.value?.buyer_scope ?? null)
  const buyerScopes = computed(() => user.value?.buyer_scopes ?? (buyerScope.value ? [buyerScope.value] : []))
  const isBuyer = computed(() => user.value?.is_buyer ?? buyerScopes.value.length > 0)

  return { user, cafe, checked, bootNetworkError, justLoggedIn, boot, login, logout, hasRole, buyerScope, buyerScopes, isBuyer }
})
