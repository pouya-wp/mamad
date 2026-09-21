<script setup lang="ts">
import { Clock3, LoaderCircle, MonitorSmartphone } from 'lucide-vue-next'
import { onMounted } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import { get } from '@/lib/api'
import { faNumber, jDateTime, toman } from '@/lib/format'
import type { Shift } from '@/lib/types'
import { useLoader } from '@/lib/useLoader'

const { data: shifts, loading, load } = useLoader(() => get<Shift[]>('cafe_app.api.pos.list_shifts', { limit: 60 }))
onMounted(load)

const diffTone = (d: number | null) => (d === null ? 'text-ink-500' : d === 0 ? 'text-mint-400' : d > 0 ? 'text-amber-300' : 'text-rose-400')
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <p class="text-sm text-ink-400">هر صندوقدار شیفتش را با موجودی نقد باز می‌کند و با شمارش صندوق می‌بندد؛ مغایرت اینجا دیده می‌شود.</p>
      <div class="flex-1" />
      <RouterLink to="/pos" class="btn-primary"><MonitorSmartphone class="size-4" /> رفتن به صندوق</RouterLink>
    </div>

    <div class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[860px] text-sm">
          <thead>
            <tr class="border-b border-white/[0.06] text-right text-xs text-ink-400">
              <th class="px-6 py-4 font-medium">صندوقدار</th>
              <th class="px-4 py-4 font-medium">شروع</th>
              <th class="px-4 py-4 font-medium">پایان</th>
              <th class="px-4 py-4 font-medium">سفارش</th>
              <th class="px-4 py-4 font-medium">فروش کل</th>
              <th class="px-4 py-4 font-medium">نقد مورد انتظار</th>
              <th class="px-4 py-4 font-medium">شمارش‌شده</th>
              <th class="px-6 py-4 font-medium">مغایرت</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.04]">
            <tr v-for="s in shifts ?? []" :key="s.name">
              <td class="px-6 py-3.5">
                <p class="font-medium text-ink-100" dir="ltr">{{ s.user.split('@')[0] }}</p>
                <span v-if="s.status === 'Open'" class="text-xs text-mint-400">● باز</span>
              </td>
              <td class="px-4 py-3.5 text-ink-300">{{ jDateTime(s.opening_time) }}</td>
              <td class="px-4 py-3.5 text-ink-300">{{ s.closing_time ? jDateTime(s.closing_time) : '—' }}</td>
              <td class="num px-4 py-3.5 text-ink-300">{{ faNumber(s.orders_count) }}</td>
              <td class="num px-4 py-3.5 font-medium text-bone">{{ toman(s.total_sales) }}</td>
              <td class="num px-4 py-3.5 text-ink-300">{{ toman(s.expected_cash) }}</td>
              <td class="num px-4 py-3.5 text-ink-300">{{ s.closing_cash === null ? '—' : toman(s.closing_cash) }}</td>
              <td class="num px-6 py-3.5 font-bold" :class="diffTone(s.status === 'Open' ? null : s.difference)" dir="ltr">
                {{ s.status === 'Open' ? '—' : toman(s.difference) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="loading" class="flex justify-center py-6"><LoaderCircle class="size-5 animate-spin text-ink-400" /></div>
      <EmptyState v-else-if="!shifts?.length" :icon="Clock3" title="هنوز شیفتی ثبت نشده" />
    </div>
  </div>
</template>
