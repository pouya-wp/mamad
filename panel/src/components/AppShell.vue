<script setup lang="ts">
import {
  BookOpenText,
  ChartNoAxesCombined,
  Clock3,
  LogOut,
  Menu,
  MonitorSmartphone,
  Package,
  ReceiptText,
  Sparkles,
  Truck,
  Volume2,
  VolumeX,
  Wallet,
  X,
} from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AgentDock from '@/components/agent/AgentDock.vue'
import IntroSplash from '@/components/fx/IntroSplash.vue'
import LivePulse from '@/components/fx/LivePulse.vue'
import LiquidBackdrop from '@/components/fx/LiquidBackdrop.vue'
import OneLogo from '@/components/OneLogo.vue'
import { DEMO } from '@/demo'
import { jDate, jWeekday } from '@/lib/format'
import { pageTransitions } from '@/lib/pageTransition'
import { sound, soundOn } from '@/lib/sound'
import { useAgent } from '@/stores/agent'
import { useSession } from '@/stores/session'

const session = useSession()
const agent = useAgent()
const route = useRoute()
const router = useRouter()
const drawer = ref(false)
const now = ref(new Date())
let timer: number

// Grouped so eight links read as three short lists instead of one long one.
const nav = [
  {
    section: 'هر روز',
    items: [
      { to: '/', label: 'داشبورد', icon: ChartNoAxesCombined },
      { to: '/pos', label: 'صندوق', icon: MonitorSmartphone },
      { to: '/orders', label: 'سفارش‌ها', icon: ReceiptText },
    ],
  },
  {
    section: 'کافه',
    items: [
      { to: '/menu', label: 'منو و رسپی', icon: BookOpenText },
      { to: '/inventory', label: 'انبار', icon: Package },
      { to: '/purchases', label: 'خرید و تأمین', icon: Truck },
    ],
  },
  {
    section: 'مالی',
    items: [
      { to: '/accounting', label: 'حسابداری', icon: Wallet },
      { to: '/shifts', label: 'شیفت‌ها', icon: Clock3 },
    ],
  },
]

// ONE CAFE is open 8:30 to 23:30; the header says so, live.
const hours = computed(() => {
  const clock = now.value.getHours() + now.value.getMinutes() / 60
  const isOpen = clock >= 8.5 && clock < 23.5
  return { isOpen, text: isOpen ? 'باز · تا ۲۳:۳۰' : 'بسته · از ۸:۳۰' }
})

const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to))

// One liquid indicator for the whole menu: the leading edge moves fast and the
// trailing edge follows slowly, so it stretches like a drop on its way.
const navEl = ref<HTMLElement>()
const indicator = ref({ top: 0, bottom: 0, ready: false, down: true })

async function moveIndicator() {
  await nextTick()
  const nav = navEl.value
  const active = nav?.querySelector<HTMLElement>('[data-active="true"]')
  if (!nav || !active) {
    indicator.value = { ...indicator.value, ready: false }
    return
  }
  const top = active.offsetTop + 10
  const bottom = nav.scrollHeight - (active.offsetTop + active.offsetHeight) + 10
  indicator.value = { top, bottom, ready: true, down: top >= indicator.value.top }
}

watch(
  () => route.fullPath,
  () => {
    drawer.value = false
    moveIndicator()
  },
)

// the page behind the mobile drawer must not scroll with it
watch(drawer, (open) => document.body.classList.toggle('overflow-hidden', open))

// the header only separates itself from the page once there is something above it
const scrolled = ref(false)
const onScroll = () => (scrolled.value = window.scrollY > 4)

onMounted(() => {
  timer = window.setInterval(() => (now.value = new Date()), 30_000)
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
  moveIndicator()
})
onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('scroll', onScroll)
  document.body.classList.remove('overflow-hidden')
})

function toggleSound() {
  soundOn.value = !soundOn.value
  if (soundOn.value) sound.enable()
}

async function logout() {
  await session.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="min-h-dvh">
    <LiquidBackdrop />
    <!-- page-wide warm light that follows the pointer -->
    <div
      data-aura
      class="pointer-events-none fixed top-0 left-0 -z-10 size-[1100px] rounded-full bg-[radial-gradient(circle,rgba(255,79,26,0.075),transparent_60%)] will-change-transform"
      style="transform: translate3d(-9999px, -9999px, 0)"
    />

    <!-- Sidebar -->
    <aside
      style="view-transition-name: shell-sidebar"
      class="glass-edge fixed inset-y-0 right-0 z-40 flex w-68 flex-col border-l border-white/[0.06] bg-ink-900/88 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0"
      :class="drawer ? 'translate-x-0' : 'translate-x-full'"
    >
      <div class="flex items-center justify-between px-6 pt-7 pb-8">
        <RouterLink to="/" class="logo-link text-bone"><OneLogo :size="34" with-wordmark animated /></RouterLink>
        <button class="text-ink-300 lg:hidden" aria-label="بستن منو" @click="drawer = false"><X class="size-5" /></button>
      </div>

      <nav ref="navEl" class="relative flex-1 space-y-1 overflow-y-auto px-3">
        <span
          class="pointer-events-none absolute right-3 w-[3px] rounded-full bg-one-500 shadow-[0_0_16px_3px_rgba(255,79,26,0.75)]"
          :style="{
            top: `${indicator.top}px`,
            bottom: `${indicator.bottom}px`,
            opacity: indicator.ready ? 1 : 0,
            transition: indicator.down
              ? 'top 0.7s var(--ease-spring), bottom 0.28s cubic-bezier(0.3,0,0.2,1), opacity 0.3s'
              : 'top 0.28s cubic-bezier(0.3,0,0.2,1), bottom 0.7s var(--ease-spring), opacity 0.3s',
          }"
        />
        <template v-for="group in nav" :key="group.section">
          <p class="nav-section">{{ group.section }}</p>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            data-ripple
            :data-active="isActive(item.to)"
            :aria-current="isActive(item.to) ? 'page' : undefined"
            class="group flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] transition"
            :class="isActive(item.to) ? 'bg-white/[0.06] text-bone' : 'text-ink-300 hover:bg-white/[0.03] hover:text-ink-100'"
          >
            <component
              :is="item.icon"
              class="size-[18px] transition duration-300 group-hover:scale-110"
              :class="isActive(item.to) ? 'text-one-500 drop-shadow-[0_0_6px_rgba(255,79,26,0.8)]' : ''"
              :stroke-width="1.8"
            />
            {{ item.label }}
          </RouterLink>
        </template>
      </nav>

      <div class="m-3 rounded-2xl border border-white/[0.06] bg-ink-850/80 p-4">
        <div class="flex items-center gap-3">
          <div class="grid size-10 place-items-center rounded-full bg-one-500/15 font-bold text-one-400 shadow-[0_0_20px_-4px_rgba(255,79,26,0.5)]">
            {{ session.user?.full_name?.charAt(0) ?? 'O' }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-ink-100">{{ session.user?.full_name }}</p>
            <p class="truncate text-xs text-ink-400">{{ session.cafe?.company }}</p>
          </div>
          <button v-if="!DEMO" class="rounded-lg p-2 text-ink-400 transition hover:bg-white/5 hover:text-rose-400" title="خروج" @click="logout">
            <LogOut class="size-4" />
          </button>
        </div>
      </div>
    </aside>

    <div v-if="drawer" class="fixed inset-0 z-30 bg-black/70 backdrop-blur-sm lg:hidden" aria-hidden="true" @click="drawer = false" />

    <!-- Main -->
    <div class="lg:pr-68">
      <header
        style="view-transition-name: shell-header"
        class="sticky top-0 z-20 flex h-18 items-center gap-3 px-4 backdrop-blur-xl transition-colors duration-300 sm:px-8"
        :class="scrolled ? 'header-glow bg-ink-950/85 shadow-[0_18px_40px_-34px_rgba(0,0,0,1)]' : 'bg-ink-950/40'"
      >
        <button class="rounded-xl border border-white/10 p-2.5 text-ink-200 lg:hidden" aria-label="منو" @click="drawer = true">
          <Menu class="size-5" />
        </button>
        <div class="min-w-0 flex-1">
          <slot name="title">
            <h1 class="truncate text-lg font-bold text-bone">{{ route.meta.title }}</h1>
          </slot>
        </div>
        <slot name="actions" />
        <button
          data-ripple
          data-magnetic="0.18"
          class="flex h-10 items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] px-3 text-sm text-ink-300 transition hover:border-one-500/40 hover:text-bone md:w-72"
          @click="agent.open = true"
        >
          <Sparkles class="size-4 text-one-500" />
          <span class="hidden flex-1 text-right md:inline">از دستیار One بپرس…</span>
          <kbd class="hidden rounded-md border border-white/10 px-1.5 py-0.5 text-[10px] text-ink-500 md:inline" dir="ltr">Ctrl K</kbd>
        </button>
        <button
          data-ripple
          class="grid size-10 place-items-center rounded-xl border border-white/10 bg-white/[0.03] text-ink-300 transition hover:text-bone"
          data-sfx="none"
          :title="soundOn ? 'بی‌صدا' : 'صدا'"
          @click="toggleSound"
        >
          <component :is="soundOn ? Volume2 : VolumeX" class="size-4" />
        </button>
        <span v-if="DEMO" class="hidden rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1.5 text-[11px] text-amber-300 sm:inline-block">
          نسخه نمایشی
        </span>
        <LivePulse />
        <span
          class="hidden items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-[11px] xl:flex"
          :class="hours.isOpen ? 'text-mint-400' : 'text-ink-400'"
        >
          <i class="printer-led" :class="hours.isOpen ? 'is-live' : ''" />
          {{ hours.text }}
        </span>
        <div class="hidden text-left text-xs leading-5 text-ink-400 xl:block">
          <p class="text-ink-200">{{ jWeekday(now) }}</p>
          <p>{{ jDate(now) }}</p>
        </div>
      </header>

      <!-- bottom room so the floating assistant button never covers the last row -->
      <!-- neon line that sweeps under the header during a page transition (see router.ts) -->
      <span class="route-sweep pointer-events-none fixed top-18 right-0 left-0 z-30 h-[2px] lg:right-68" aria-hidden="true" />

      <main style="view-transition-name: page" class="px-4 pt-6 pb-28 sm:px-8 sm:pt-8">
        <RouterView v-slot="{ Component }">
          <!-- the View Transition in router.ts animates the page; plain CSS entrance where unsupported -->
          <component :is="Component" v-if="pageTransitions" />
          <Transition v-else enter-active-class="animate-rise" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>

    <AgentDock />
    <IntroSplash />
  </div>
</template>
