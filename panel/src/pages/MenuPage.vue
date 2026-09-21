<script setup lang="ts">
import { BookOpenText, CookingPot, LoaderCircle, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import Modal from '@/components/Modal.vue'
import Segmented from '@/components/Segmented.vue'
import { get, post } from '@/lib/api'
import { faNumber, percent, toman, toRial, toToman, UOM_LABELS, uom } from '@/lib/format'
import { fxLite } from '@/lib/motion'
import { toast, toastError } from '@/lib/toast'
import type { Ingredient, MenuItem, MenuItemDetail, RecipeRow } from '@/lib/types'

type Tab = 'menu' | 'ingredients'
const tab = ref<Tab>('menu')
const tabs: { value: Tab; label: string }[] = [
  { value: 'menu', label: 'منو' },
  { value: 'ingredients', label: 'مواد اولیه' },
]

const groups = ref<{ menu: string[]; ingredients: string[] }>({ menu: [], ingredients: [] })
const menu = ref<MenuItem[]>([])
const ingredients = ref<Ingredient[]>([])
const loading = ref(true)
const filter = ref('همه')
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    ;[groups.value, menu.value, ingredients.value] = await Promise.all([
      get<typeof groups.value>('cafe_app.api.menu.get_groups'),
      get<MenuItem[]>('cafe_app.api.menu.list_menu'),
      get<Ingredient[]>('cafe_app.api.menu.list_ingredients'),
    ])
  } catch (error) {
    toastError(error)
  } finally {
    loading.value = false
  }
}
onMounted(load)

const visibleMenu = computed(() => menu.value.filter((m) => filter.value === 'همه' || m.item_group === filter.value))
const marginTone = (m: number) => (m >= 65 ? 'text-mint-400 bg-mint-400/10' : m >= 45 ? 'text-amber-300 bg-amber-300/10' : 'text-rose-400 bg-rose-400/10')

// ---- Menu item editor ----
type Editor = { item_code?: string; item_name: string; item_group: string; rateToman: number | null; description: string; active: boolean; recipe: RecipeRow[] }
const editorOpen = ref(false)
const editor = ref<Editor>(blankEditor())

function blankEditor(): Editor {
  return { item_name: '', item_group: groups.value.menu[0] ?? '', rateToman: null, description: '', active: true, recipe: [] }
}

/** The clicked card morphs into the editor (View Transitions API); plain modal elsewhere. */
function openEditor(item: MenuItem, event: MouseEvent) {
  const card = event.currentTarget as HTMLElement | null
  if (fxLite || !card || !document.startViewTransition || document.hidden) return editItem(item)

  card.style.viewTransitionName = 'menu-morph'
  const transition = document.startViewTransition(async () => {
    card.style.viewTransitionName = ''
    void editItem(item)
    await nextTick()
  })
  // the browser aborts the morph on rapid clicks; the editor still opens, so ignore it
  transition.ready.catch(() => undefined)
}

async function editItem(item?: MenuItem) {
  editor.value = blankEditor()
  editorOpen.value = true
  if (!item) return
  try {
    const d = await get<MenuItemDetail>('cafe_app.api.menu.get_menu_item', { item_code: item.item_code })
    editor.value = {
      item_code: d.item_code,
      item_name: d.item_name,
      item_group: d.item_group,
      rateToman: toToman(d.rate),
      description: d.description ?? '',
      active: !d.disabled,
      recipe: d.recipe,
    }
  } catch (error) {
    toastError(error)
  }
}

const ingredientBy = computed(() => new Map(ingredients.value.map((i) => [i.item_code, i])))
const recipeCost = computed(() =>
  editor.value.recipe.reduce((sum, r) => sum + (Number(r.qty) || 0) * (ingredientBy.value.get(r.item_code)?.valuation_rate ?? 0), 0),
)
const editorMargin = computed(() => {
  const rate = toRial(editor.value.rateToman ?? 0)
  return rate ? ((rate - recipeCost.value) / rate) * 100 : 0
})

async function saveItem() {
  saving.value = true
  try {
    await post('cafe_app.api.menu.save_menu_item', {
      data: {
        item_code: editor.value.item_code,
        item_name: editor.value.item_name.trim(),
        item_group: editor.value.item_group,
        rate: toRial(editor.value.rateToman ?? 0),
        description: editor.value.description,
        disabled: editor.value.active ? 0 : 1,
        recipe: editor.value.recipe.filter((r) => r.item_code && Number(r.qty) > 0),
      },
    })
    toast('آیتم منو ذخیره شد')
    editorOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}

// ---- Ingredient editor ----
type IngredientForm = { item_code?: string; item_name: string; item_group: string; stock_uom: string; safety_stock: number | null; costToman: number | null }
const ingredientOpen = ref(false)
const ingredientForm = ref<IngredientForm>({ item_name: '', item_group: '', stock_uom: 'Gram', safety_stock: null, costToman: null })

function editIngredient(i?: Ingredient) {
  ingredientForm.value = i
    ? { item_code: i.item_code, item_name: i.item_name, item_group: i.item_group, stock_uom: i.stock_uom, safety_stock: i.safety_stock, costToman: i.valuation_rate / 10 }
    : { item_name: '', item_group: groups.value.ingredients[0] ?? '', stock_uom: 'Gram', safety_stock: null, costToman: null }
  ingredientOpen.value = true
}

async function saveIngredient() {
  saving.value = true
  try {
    const f = ingredientForm.value
    await post('cafe_app.api.menu.save_ingredient', {
      data: {
        item_code: f.item_code,
        item_name: f.item_name.trim(),
        item_group: f.item_group,
        stock_uom: f.stock_uom,
        safety_stock: f.safety_stock ?? 0,
        valuation_rate: (f.costToman ?? 0) * 10,
      },
    })
    toast('ماده اولیه ذخیره شد')
    ingredientOpen.value = false
    load()
  } catch (error) {
    toastError(error)
  } finally {
    saving.value = false
  }
}

const costPerUnit = (i: Ingredient) => faNumber(i.valuation_rate / 10, i.valuation_rate < 100 ? 1 : 0)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <Segmented v-model="tab" :options="tabs" />
      <div class="flex-1" />
      <button v-if="tab === 'menu'" class="btn-primary" @click="editItem()"><Plus class="size-4" /> آیتم جدید</button>
      <button v-else class="btn-primary" @click="editIngredient()"><Plus class="size-4" /> ماده اولیه جدید</button>
    </div>

    <!-- MENU -->
    <template v-if="tab === 'menu'">
      <div class="-mx-1 flex gap-2 overflow-x-auto pb-1">
        <button
          v-for="g in ['همه', ...groups.menu]"
          :key="g"
          class="shrink-0 rounded-full border px-4 py-1.5 text-sm transition"
          :class="filter === g ? 'border-bone bg-bone font-medium text-ink-950' : 'border-white/10 text-ink-300 hover:text-ink-100'"
          @click="filter = g"
        >
          {{ g }}
        </button>
      </div>

      <div v-if="loading" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        <div v-for="i in 8" :key="i" class="card h-44 animate-pulse" />
      </div>
      <div v-else-if="visibleMenu.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        <button
          v-for="m in visibleMenu"
          :key="m.item_code"
          data-ripple
          data-tilt="6"
          class="card group flex flex-col p-5 text-right transition hover:border-white/15"
          :class="m.disabled ? 'opacity-45' : ''"
          @click="openEditor(m, $event)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-[11px] text-ink-400">{{ m.item_group }}</p>
              <p data-depth class="mt-1 truncate text-lg font-bold text-bone">{{ m.item_name }}</p>
            </div>
            <Pencil class="size-4 shrink-0 text-ink-500 transition group-hover:text-one-400" />
          </div>
          <p class="num mt-4 text-2xl font-black text-bone">{{ toman(m.rate) }} <span class="text-xs font-normal text-ink-400">تومان</span></p>
          <div class="mt-auto flex items-center gap-2 pt-5 text-xs">
            <template v-if="m.has_recipe">
              <span class="text-ink-400">بهای تمام‌شده {{ toman(m.cost) }}</span>
              <span class="flex-1" />
              <span class="num rounded-full px-2 py-0.5 font-medium" :class="marginTone(m.margin)">سود {{ percent(m.margin) }}</span>
            </template>
            <span v-else class="rounded-full bg-one-500/10 px-2 py-0.5 text-one-400">بدون رسپی</span>
            <span v-if="m.disabled" class="rounded-full bg-white/5 px-2 py-0.5 text-ink-300">غیرفعال</span>
          </div>
        </button>
      </div>
      <EmptyState v-else :icon="BookOpenText" title="منو خالیه" text="اولین آیتم منو را با رسپی‌اش بساز." />
    </template>

    <!-- INGREDIENTS -->
    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[720px] text-sm">
          <thead>
            <tr class="border-b border-white/[0.06] text-right text-xs text-ink-400">
              <th class="px-6 py-4 font-medium">ماده اولیه</th>
              <th class="px-4 py-4 font-medium">دسته</th>
              <th class="px-4 py-4 font-medium">موجودی</th>
              <th class="px-4 py-4 font-medium">حد مجاز</th>
              <th class="px-4 py-4 font-medium">بهای واحد (تومان)</th>
              <th class="px-6 py-4" />
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.04]">
            <tr v-for="i in ingredients" :key="i.item_code" class="transition hover:bg-white/[0.02]">
              <td class="px-6 py-3.5 font-medium text-ink-100">{{ i.item_name }}</td>
              <td class="px-4 py-3.5 text-ink-400">{{ i.item_group }}</td>
              <td class="num px-4 py-3.5" :class="i.actual_qty <= i.safety_stock ? 'text-amber-300' : 'text-ink-200'">
                {{ faNumber(i.actual_qty) }} <span class="text-xs text-ink-500">{{ uom(i.stock_uom) }}</span>
              </td>
              <td class="num px-4 py-3.5 text-ink-400">{{ faNumber(i.safety_stock) }}</td>
              <td class="num px-4 py-3.5 text-ink-300">{{ costPerUnit(i) }} <span class="text-xs text-ink-500">/ {{ uom(i.stock_uom) }}</span></td>
              <td class="px-6 py-3.5 text-left">
                <button class="rounded-lg p-2 text-ink-400 hover:bg-white/5 hover:text-one-400" @click="editIngredient(i)"><Pencil class="size-4" /></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-if="!loading && !ingredients.length" :icon="CookingPot" title="ماده اولیه‌ای تعریف نشده" />
    </div>

    <!-- Menu item modal -->
    <Modal v-model="editorOpen" :title="editor.item_code ? 'ویرایش آیتم منو' : 'آیتم جدید منو'" width="max-w-2xl" morph="menu-morph">
      <div class="space-y-6">
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block sm:col-span-2">
            <span class="mb-2 block text-sm text-ink-300">نام آیتم</span>
            <input v-model="editor.item_name" class="field" :disabled="!!editor.item_code" placeholder="مثلاً: لاته" />
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">دسته</span>
            <select v-model="editor.item_group" class="field">
              <option v-for="g in groups.menu" :key="g" :value="g">{{ g }}</option>
            </select>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm text-ink-300">قیمت فروش (تومان)</span>
            <input v-model.number="editor.rateToman" type="number" min="0" class="field" />
          </label>
          <label class="block sm:col-span-2">
            <span class="mb-2 block text-sm text-ink-300">توضیحات</span>
            <input v-model="editor.description" class="field" />
          </label>
        </div>

        <div>
          <div class="mb-3 flex items-center justify-between">
            <p class="font-bold text-bone">رسپی</p>
            <button class="btn-ghost h-8 px-3 text-xs" @click="editor.recipe.push({ item_code: '', qty: 0 })"><Plus class="size-3.5" /> ماده</button>
          </div>
          <div v-if="editor.recipe.length" class="space-y-2">
            <div v-for="(row, index) in editor.recipe" :key="index" class="grid grid-cols-[1fr_120px_auto] items-center gap-2">
              <select v-model="row.item_code" class="field h-10">
                <option value="" disabled>انتخاب ماده اولیه</option>
                <option v-for="i in ingredients" :key="i.item_code" :value="i.item_code">{{ i.item_name }}</option>
              </select>
              <div class="relative">
                <input v-model.number="row.qty" type="number" min="0" step="any" class="field h-10 pl-14" />
                <span class="absolute inset-y-0 left-3 grid place-items-center text-xs text-ink-400">{{ uom(ingredientBy.get(row.item_code)?.stock_uom) }}</span>
              </div>
              <button class="grid size-10 place-items-center rounded-xl text-ink-400 hover:bg-white/5 hover:text-rose-400" @click="editor.recipe.splice(index, 1)">
                <Trash2 class="size-4" />
              </button>
            </div>
          </div>
          <p v-else class="rounded-2xl border border-dashed border-white/10 px-4 py-6 text-center text-sm text-ink-400">
            با تعریف رسپی، هر فروش این آیتم مواد اولیه‌اش را از انبار کم می‌کند.
          </p>
          <div class="mt-4 grid grid-cols-2 gap-3">
            <div class="rounded-2xl bg-white/[0.03] p-4">
              <p class="text-xs text-ink-400">بهای تمام‌شده</p>
              <p class="num mt-1 font-bold text-bone">{{ toman(recipeCost) }} <span class="text-xs font-normal text-ink-400">تومان</span></p>
            </div>
            <div class="rounded-2xl bg-white/[0.03] p-4">
              <p class="text-xs text-ink-400">حاشیه سود</p>
              <p class="num mt-1 font-bold" :class="marginTone(editorMargin).split(' ')[0]">{{ percent(editorMargin) }}</p>
            </div>
          </div>
        </div>

        <label class="flex items-center gap-3 text-sm text-ink-200">
          <input v-model="editor.active" type="checkbox" class="size-4 accent-one-500" />
          در منو و صندوق نمایش داده شود
        </label>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="editorOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || !editor.item_name.trim()" @click="saveItem">
          <LoaderCircle v-if="saving" class="size-4 animate-spin" /> ذخیره
        </button>
      </template>
    </Modal>

    <!-- Ingredient modal -->
    <Modal v-model="ingredientOpen" :title="ingredientForm.item_code ? 'ویرایش ماده اولیه' : 'ماده اولیه جدید'">
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="block sm:col-span-2">
          <span class="mb-2 block text-sm text-ink-300">نام</span>
          <input v-model="ingredientForm.item_name" class="field" :disabled="!!ingredientForm.item_code" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">دسته</span>
          <select v-model="ingredientForm.item_group" class="field">
            <option v-for="g in groups.ingredients" :key="g" :value="g">{{ g }}</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">واحد</span>
          <select v-model="ingredientForm.stock_uom" class="field" :disabled="!!ingredientForm.item_code">
            <option v-for="(label, value) in UOM_LABELS" :key="value" :value="value">{{ label }}</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">حد مجاز موجودی</span>
          <input v-model.number="ingredientForm.safety_stock" type="number" min="0" class="field" />
        </label>
        <label class="block">
          <span class="mb-2 block text-sm text-ink-300">بهای هر {{ uom(ingredientForm.stock_uom) }} (تومان)</span>
          <input v-model.number="ingredientForm.costToman" type="number" min="0" step="any" class="field" />
        </label>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="ingredientOpen = false">انصراف</button>
        <button class="btn-primary" :disabled="saving || !ingredientForm.item_name.trim()" @click="saveIngredient">
          <LoaderCircle v-if="saving" class="size-4 animate-spin" /> ذخیره
        </button>
      </template>
    </Modal>
  </div>
</template>
