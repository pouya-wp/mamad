import { ref, type Ref } from 'vue'

import { toastError } from './toast'

/** Keeps the last good data while reloading, and surfaces failures as toasts. */
export function useLoader<T>(fetcher: () => Promise<T>) {
  const data = ref(null) as Ref<T | null>
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      data.value = await fetcher()
    } catch (error) {
      toastError(error)
    } finally {
      loading.value = false
    }
  }

  return { data, loading, load }
}
