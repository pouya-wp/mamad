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
        { path: 'menu', component: () => import('@/pages/MenuPage.vue'), meta: { title: 'منو و رسپی', buyer: 'Restaurant' } },
        { path: 'inventory', component: () => import('@/pages/InventoryPage.vue'), meta: { title: 'انبار' } },
        { path: 'purchases', component: () => import('@/pages/BuyingPage.vue'), meta: { title: 'دفتر خرید', buyer: true } },
        { path: 'expenses', component: () => import('@/pages/BuyerExpensesPage.vue'), meta: { title: 'هزینه‌ها', buyer: true } },
        { path: 'calendar', component: () => import('@/pages/CalendarPage.vue'), meta: { title: 'تقویم خریدها', buyer: true } },
        { path: 'cheques', component: () => import('@/pages/ChequesPage.vue'), meta: { title: 'چک‌ها' } },
        { path: 'staff', component: () => import('@/pages/StaffPage.vue'), meta: { title: 'پرسنل و قراردادها' } },
        { path: 'accounting', component: () => import('@/pages/AccountingPage.vue'), meta: { title: 'حسابداری' } },
        { path: 'buyer-activity', component: () => import('@/pages/BuyerActivityPage.vue'), meta: { title: 'فعالیت مسئولان خرید' } },
        { path: 'shifts', component: () => import('@/pages/ShiftsPage.vue'), meta: { title: 'شیفت‌ها', hidden: true } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to) => {
  if (to.meta.hidden) return '/'
  const session = useSession()
  if (!session.checked) await session.boot().catch(() => false)

  // the demo build signs itself in: no login, no backend
  if (DEMO) return to.meta.public ? '/' : true
  if (to.meta.public) return session.user ? '/' : true
  if (!session.user) return { path: '/login', query: to.fullPath === '/' ? {} : { next: to.fullPath } }
  // Purchase managers may see the purchase register, purchase calendar and permitted recipes.
  if (session.isBuyer && to.meta.buyer !== true && !session.buyerScopes.includes(to.meta.buyer as 'Restaurant' | 'Cafe')) return '/purchases'
})

installPageTransitions(router)

router.afterEach((to, from, failure) => {
  if (!failure && from.matched.length > 0 && to.path !== from.path) sound.page()
})
