import { createRouter, createWebHistory } from 'vue-router'

import AppShell from '@/components/AppShell.vue'
import { DEMO } from '@/demo'
import { installPageTransitions } from '@/lib/pageTransition'
import { sound } from '@/lib/sound'
import { useSession } from '@/stores/session'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/pages/LoginPage.vue'), meta: { public: true } },
    { path: '/pos', component: () => import('@/pages/PosPage.vue'), meta: { title: 'صندوق' } },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', component: () => import('@/pages/DashboardPage.vue'), meta: { title: 'داشبورد' } },
        { path: 'orders', component: () => import('@/pages/OrdersPage.vue'), meta: { title: 'سفارش‌ها' } },
        { path: 'menu', component: () => import('@/pages/MenuPage.vue'), meta: { title: 'منو و رسپی' } },
        { path: 'inventory', component: () => import('@/pages/InventoryPage.vue'), meta: { title: 'انبار' } },
        { path: 'purchases', component: () => import('@/pages/PurchasesPage.vue'), meta: { title: 'خرید و تأمین‌کنندگان' } },
        { path: 'accounting', component: () => import('@/pages/AccountingPage.vue'), meta: { title: 'حسابداری' } },
        { path: 'shifts', component: () => import('@/pages/ShiftsPage.vue'), meta: { title: 'شیفت‌ها' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to) => {
  const session = useSession()
  if (!session.checked) await session.boot().catch(() => false)

  // the demo build signs itself in: no login, no backend
  if (DEMO) return to.meta.public ? '/' : true
  if (to.meta.public) return session.user ? '/' : true
  if (!session.user) return { path: '/login', query: to.fullPath === '/' ? {} : { next: to.fullPath } }
})

installPageTransitions(router)

router.afterEach((to, from, failure) => {
  if (!failure && from.matched.length > 0 && to.path !== from.path) sound.page()
})
