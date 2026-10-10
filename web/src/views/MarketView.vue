<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import ItemCard from '@/components/ItemCard.vue'
import PublishDialog from '@/components/PublishDialog.vue'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useCategoryStore } from '@/stores/category'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const categoryStore = useCategoryStore()

const items = ref([])
const loading = ref(false)
const category = ref('')
const keyword = ref('')
const sort = ref('latest')
const hasMore = ref(false)
const PAGE = 24
const counts = ref({})
const favIds = ref(new Set())
const busyId = ref(null)
const showPublish = ref(false)

// 分类由管理员维护：首项固定为「全部」，其余动态来自后端
const categories = computed(() => [
  { key: '', label: '全部', icon: 'box' },
  ...categoryStore.list.map(c => ({ key: c.name, label: c.name, icon: c.icon })),
])
const categoryCount = (key) => key
  ? (counts.value[key] || 0)
  : Object.values(counts.value).reduce((a, b) => a + b, 0)

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadItems(true), 320)
}

async function loadItems(reset = true) {
  loading.value = true
  try {
    const p = new URLSearchParams()
    if (category.value) p.set('category', category.value)
    if (keyword.value) p.set('keyword', keyword.value)
    p.set('sort', sort.value)
    p.set('limit', String(PAGE + 1))
    if (!reset) p.set('offset', String(items.value.length))
    const list = await api.get('/api/items?' + p)
    hasMore.value = list.length > PAGE
    const page = list.slice(0, PAGE)
    items.value = reset ? page : items.value.concat(page)
    if (reset) { loadCounts(); if (auth.isLoggedIn) loadFavorites() }
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function loadCounts() {
  try {
    const all = await api.get('/api/items?limit=200')
    const c = {}
    all.forEach(i => { c[i.category] = (c[i.category] || 0) + 1 })
    counts.value = c
  } catch { /* 计数失败不影响主列表 */ }
}

async function loadFavorites() {
  try {
    const list = await api.get('/api/favorites')
    favIds.value = new Set(list.map(f => f.item_id))
  } catch { /* 未登录或会话失效时静默 */ }
}

async function toggleFavorite(item) {
  if (!auth.isLoggedIn) { router.push({ name: 'login', query: { redirect: '/' } }); return }
  busyId.value = item.id
  const on = favIds.value.has(item.id)
  try {
    if (on) await api.del(`/api/favorites/${item.id}`)
    else await api.post('/api/favorites', { item_id: item.id })
    const next = new Set(favIds.value)
    on ? next.delete(item.id) : next.add(item.id)
    favIds.value = next
    ui.toast(on ? '已取消收藏' : '已加入收藏')
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    busyId.value = null
  }
}

async function reserve(item) {
  if (!auth.isLoggedIn) { router.push({ name: 'login', query: { redirect: '/' } }); return }
  busyId.value = item.id
  try {
    const o = await api.post('/api/orders', { item_id: item.id })
    ui.toast(`预约成功！自提码 ${o.pickup_code}，请线下联系卖家验货`)
    await loadItems(true)
    await auth.refresh()
    router.push({ name: 'me', query: { tab: 'buy' } })
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    busyId.value = null
  }
}

function openPublish() {
  if (!auth.isLoggedIn) { router.push({ name: 'login', query: { redirect: '/' } }); return }
  showPublish.value = true
}

async function onPublished() {
  showPublish.value = false
  await loadItems(true)
  await auth.refresh()
}

const summary = ref({})
async function loadSummary() {
  try { summary.value = await api.get('/api/stats/summary') } catch { /* 首页统计非关键 */ }
}

watch([category, sort], () => loadItems(true))
onMounted(() => { categoryStore.load(); loadItems(true); loadSummary() })
onUnmounted(() => clearTimeout(searchTimer))
</script>

<template>
  <div class="animate-rise">
    <!-- Hero -->
    <div class="relative overflow-hidden rounded-xl2 border border-line bg-gradient-to-br from-brand-600 via-brand-700 to-emerald-900 text-white p-6 sm:p-8 shadow-card">
      <div class="absolute -right-16 -top-20 w-72 h-72 rounded-full bg-white/10 blur-2xl"></div>
      <div class="absolute right-24 -bottom-24 w-56 h-56 rounded-full bg-brand-300/20 blur-2xl"></div>
      <div class="relative">
        <p class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/15 text-[11px] font-medium backdrop-blur">
          <Icon name="sparkle" :size="13" /> 让每一本教材多流转一次
        </p>
        <h1 class="mt-3 text-2xl sm:text-3xl font-bold tracking-tight">绿色市集</h1>
        <p class="mt-1.5 text-sm text-white/80 max-w-xl">
          浏览、检索并预约校园闲置教材与物品。完成一次流转，卖家即得
          <b class="text-white">20 碳积分</b>，物品循环度 +1。
        </p>

        <div class="mt-5 flex flex-col sm:flex-row gap-2.5 max-w-2xl">
          <div class="relative flex-1">
            <Icon name="search" :size="18" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/60 pointer-events-none" />
            <input v-model.trim="keyword" @keyup.enter="loadItems(true)" @input="onSearchInput"
                   placeholder="搜索教材、考研资料、生活用品…" aria-label="搜索闲置物品"
                   class="w-full h-11 pl-11 pr-10 rounded-xl bg-white/95 text-ink placeholder:text-slate-400 border-0 text-sm focus:outline-none focus:ring-2 focus:ring-white/70" />
            <button v-if="keyword" type="button" @click="keyword = ''; loadItems(true)" aria-label="清除搜索"
                    class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <Icon name="close" :size="16" />
            </button>
          </div>
          <button type="button" @click="openPublish"
                  class="h-11 px-5 rounded-xl bg-white text-brand-700 text-sm font-semibold hover:bg-brand-50 transition-colors inline-flex items-center justify-center gap-2 shadow-sm">
            <Icon name="plus" :size="17" /> 发布闲置
          </button>
        </div>

        <div class="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-xs text-white/75">
          <span class="inline-flex items-center gap-1.5"><Icon name="box" :size="14" /> 在售 <b class="text-white tnum">{{ items.length }}</b> 件</span>
          <span class="inline-flex items-center gap-1.5"><Icon name="recycle" :size="14" /> 累计循环 <b class="text-white tnum">{{ summary.total_cycles ?? 0 }}</b> 次</span>
          <span class="inline-flex items-center gap-1.5"><Icon name="tree" :size="14" /> 累计减碳 <b class="text-white tnum">{{ summary.total_carbon_kg ?? 0 }}</b> kg</span>
        </div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="mt-5 flex flex-wrap items-center gap-2">
      <div class="flex items-center gap-1 p-1 rounded-xl bg-surface border border-line" role="tablist" aria-label="分类筛选">
        <button v-for="c in categories" :key="c.key || 'all'" type="button" role="tab" :aria-selected="category === c.key"
                @click="category = c.key"
                class="px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-1.5"
                :class="category === c.key ? 'bg-brand-600 text-white shadow-sm' : 'text-muted hover:text-ink hover:bg-canvas'">
          <Icon :name="c.icon" :size="14" />{{ c.label }}<span class="text-[11px] opacity-70 tnum">{{ categoryCount(c.key) }}</span>
        </button>
      </div>

      <div class="relative ml-auto">
        <select v-model="sort" aria-label="排序方式"
                class="h-10 pl-3.5 pr-9 rounded-xl bg-surface border border-line text-sm text-ink appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-500/40">
          <option value="latest">最新发布</option>
          <option value="price_asc">价格从低到高</option>
          <option value="price_desc">价格从高到低</option>
          <option value="cycle">循环度最高</option>
        </select>
        <Icon name="chevron" :size="15" class="absolute right-3 top-1/2 -translate-y-1/2 text-subtle pointer-events-none" />
      </div>
    </div>

    <!-- 骨架屏 -->
    <div v-if="loading && items.length === 0" class="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div v-for="n in 8" :key="n" class="p-3 rounded-xl2 bg-surface border border-line">
        <div class="skel aspect-[4/3] w-full"></div>
        <div class="skel h-4 mt-3 w-3/4"></div>
        <div class="skel h-3 mt-2 w-full"></div>
        <div class="skel h-8 mt-4 w-full"></div>
      </div>
    </div>

    <!-- 空态 -->
    <div v-else-if="items.length === 0" class="mt-8 grid place-items-center py-20 rounded-xl2 bg-surface border border-dashed border-line">
      <span class="grid place-items-center w-16 h-16 rounded-2xl bg-brand-50 dark:bg-brand-500/10 text-brand-600"><Icon name="search" :size="28" /></span>
      <p class="mt-4 font-semibold text-ink">暂无符合条件的闲置物品</p>
      <p class="mt-1 text-sm text-muted">换个关键词或分类试试，也可以成为第一个发布者</p>
      <button type="button" @click="openPublish"
              class="mt-4 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold inline-flex items-center gap-2 transition-colors">
        <Icon name="plus" :size="16" /> 发布闲置
      </button>
    </div>

    <!-- 网格 -->
    <div v-else class="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <ItemCard v-for="it in items" :key="it.id" :item="it" :me="auth.user"
                :favorited="favIds.has(it.id)" :busy="busyId === it.id"
                @reserve="reserve" @favorite="toggleFavorite" />
    </div>

    <div v-if="!loading && items.length > 0 && hasMore" class="mt-6 text-center">
      <button type="button" @click="loadItems(false)"
              class="px-5 py-2.5 rounded-xl bg-surface border border-line text-sm font-medium text-ink hover:bg-canvas transition-colors inline-flex items-center gap-2">
        <Icon name="arrowdown" :size="16" /> 加载更多
      </button>
    </div>

    <PublishDialog v-if="showPublish" @close="showPublish = false" @saved="onPublished" />
  </div>
</template>
