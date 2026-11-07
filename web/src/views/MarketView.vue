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
const category = ref(typeof router.currentRoute.value.query.category === 'string' ? router.currentRoute.value.query.category : '')
const keyword = ref(typeof router.currentRoute.value.query.q === 'string' ? router.currentRoute.value.query.q.slice(0, 50) : '')
const sort = ref(['latest', 'price_asc', 'price_desc', 'cycle'].includes(router.currentRoute.value.query.sort) ? router.currentRoute.value.query.sort : 'latest')
const hasMore = ref(false)
const PAGE = 24
const counts = ref({})
const error = ref('')
let requestId = 0
let countsId = 0
const resultCount = computed(() => categoryCount(category.value))
function resetFilters() {
  keyword.value = ''; category.value = ''; sort.value = 'latest'
}
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
  clearTimeout(searchTimer)
  const id = ++requestId
  loading.value = true
  error.value = ''
  if (reset) {
    items.value = []
    countsId++
    router.replace({ query: { ...(category.value ? { category: category.value } : {}), ...(keyword.value ? { q: keyword.value } : {}), ...(sort.value !== 'latest' ? { sort: sort.value } : {}) } })
  }
  try {
    const p = new URLSearchParams()
    if (category.value) p.set('category', category.value)
    if (keyword.value) p.set('keyword', keyword.value)
    p.set('sort', sort.value)
    p.set('limit', String(PAGE + 1))
    if (!reset) p.set('offset', String(items.value.length))
    const list = await api.get('/api/items?' + p)
    if (id !== requestId) return
    hasMore.value = list.length > PAGE
    const page = list.slice(0, PAGE)
    items.value = reset ? page : items.value.concat(page)
    if (reset) { loadCounts(); if (auth.isLoggedIn) loadFavorites() }
  } catch (e) {
    if (id === requestId) error.value = e.message
  } finally {
    if (id === requestId) loading.value = false
  }
}

async function loadCounts() {
  try {
    const id = ++countsId
    const data = await api.get('/api/items/counts?' + new URLSearchParams({ keyword: keyword.value }))
    if (id === countsId) counts.value = data
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
  if (busyId.value !== null) return
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
  if (busyId.value !== null) return
  busyId.value = item.id
  try {
    const o = await api.post('/api/orders', { item_id: item.id })
    ui.toast('预约成功！自提码仅在「我买到的」中向你展示，交接后请卖家录入核销')
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
watch(keyword, () => { requestId++; countsId++; loading.value = true; items.value = []; onSearchInput() })
watch(() => auth.user?.id, () => { favIds.value = new Set(); if (auth.isLoggedIn) loadFavorites() })
onMounted(() => { categoryStore.load(); loadItems(true); loadSummary() })
onUnmounted(() => { clearTimeout(searchTimer); requestId++; countsId++ })
</script>

<template>
  <div class="animate-rise">
    <section class="market-hero">
      <div class="hero-copy">
        <span class="hero-eyebrow"><span class="status-dot"></span> GREEN CAMPUS · 校园循环计划</span>
        <h1>让闲置，<br />遇见<span>下一份热爱。</span></h1>
        <p class="hero-description">一本读过的书，一件陪伴过的好物。<br class="hidden sm:block" />在校园里继续它们的故事，也让绿色生活多一种可能。</p>
        <div class="mt-6 flex flex-wrap gap-3">
          <button type="button" @click="openPublish" class="primary-action"><Icon name="plus" :size="18" />发布我的闲置</button>
          <RouterLink to="/dashboard" class="secondary-action">看看循环的力量 <Icon name="chart" :size="17" /></RouterLink>
        </div>
        <div class="hero-note"><Icon name="shield" :size="14" /> 校园内流转 <span>·</span> 线下验货自提 <span>·</span> 碳积分奖励</div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <span class="orbit orbit-one"></span><span class="orbit orbit-two"></span>
        <span class="art-spark art-spark-one">+</span><span class="art-spark art-spark-two">+</span>
        <div class="art-label"><Icon name="recycle" :size="15" /> 好物的下一站，就在校园</div>
        <div class="illustration-book book-back"><span>KEEP<br />GROWING.</span><Icon name="leaf" :size="38" /></div>
        <div class="illustration-book book-front"><small>THE CIRCULAR LIFE</small><span>旧物<br />新生<span class="book-period">.</span></span><div class="book-line"></div><small>每一次循环，都是新的开始</small></div>
        <div class="art-badge"><Icon name="leaf" :size="22" /><div><strong>小小循环，大大改变</strong><span>完成流转 · 卖家 +20 碳积分</span></div></div>
      </div>
    </section>

    <section class="impact-strip" aria-label="校园循环成果">
      <div><span class="impact-icon"><Icon name="recycle" :size="21" /></span><p><strong>{{ summary.total_cycles ?? '—' }}<small>次</small></strong><span>闲置重新出发</span></p></div>
      <div><span class="impact-icon"><Icon name="leaf" :size="21" /></span><p><strong>{{ summary.total_carbon_kg ?? '—' }}<small>kg</small></strong><span>累计估算减碳</span></p></div>
      <div><span class="impact-icon"><Icon name="user" :size="21" /></span><p><strong>{{ summary.total_users ?? '—' }}<small>人</small></strong><span>一起参与绿色生活</span></p></div>
      <RouterLink to="/mall" class="impact-invite"><Icon name="gift" :size="23" /><span><b>让绿色行动有回报</b><small>发布闲置赚积分，兑换校园好礼</small></span><Icon name="chevron" :size="16" class="-rotate-90" /></RouterLink>
    </section>

    <div class="market-heading"><div><p class="section-eyebrow">DISCOVER SOMETHING GOOD</p><h2>逛逛校园好物<span>为需要的生活，发现刚刚好的选择</span></h2></div></div>
    <form class="market-search" role="search" @submit.prevent="loadItems(true)">
      <Icon name="search" :size="20" class="text-muted shrink-0" />
      <input v-model.trim="keyword" maxlength="50" placeholder="搜索教材、考研资料、生活好物…" aria-label="搜索闲置物品" />
      <button v-if="keyword" type="button" @click="keyword = ''" aria-label="清除搜索" class="search-clear"><Icon name="close" :size="17" /></button>
      <button type="submit" class="search-submit">搜索好物</button>
    </form>
    <!-- 筛选 -->
    <div class="mt-5 flex flex-wrap items-center gap-2">
      <div class="category-filters flex flex-wrap items-center gap-1 p-1 rounded-xl bg-surface border border-line" role="group" aria-label="分类筛选">
        <button v-for="c in categories" :key="c.key || 'all'" type="button" :aria-pressed="category === c.key"
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

    <div class="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-muted" aria-live="polite">
      <span>{{ loading ? '正在寻找校园好物…' : `共 ${resultCount} 件好物${keyword ? '与「' + keyword + '」相关' : '，等你发现'}` }}</span>
      <button v-if="keyword || category || sort !== 'latest'" type="button" @click="resetFilters" class="text-brand-700 dark:text-brand-300 hover:underline">重置筛选</button>
    </div>
    <div v-if="error" role="alert" class="mt-4 rounded-xl border border-line bg-surface p-5 flex flex-wrap items-center justify-between gap-3">
      <span class="text-sm text-muted">{{ error }}</span><button type="button" @click="loadItems(items.length === 0)" class="secondary-action"><Icon name="refresh" :size="16" />重新加载</button>
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
    <div v-else-if="items.length === 0 && !error" class="mt-8 grid place-items-center py-20 rounded-xl2 bg-surface border border-dashed border-line">
      <span class="grid place-items-center w-16 h-16 rounded-2xl bg-brand-50 dark:bg-brand-500/10 text-brand-600"><Icon name="search" :size="28" /></span>
      <p class="mt-4 font-semibold text-ink">暂无符合条件的闲置物品</p>
      <p class="mt-1 text-sm text-muted">换个关键词或分类试试，也可以成为第一个发布者</p>
      <button type="button" @click="openPublish"
              class="mt-4 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold inline-flex items-center gap-2 transition-colors">
        <Icon name="plus" :size="16" /> 发布闲置
      </button>
    </div>

    <!-- 网格 -->
    <div v-else-if="items.length" class="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <ItemCard v-for="it in items" :key="it.id" :item="it" :me="auth.user"
                :favorited="favIds.has(it.id)" :busy="busyId !== null"
                @reserve="reserve" @favorite="toggleFavorite" />
    </div>

    <div v-if="items.length > 0 && hasMore" class="mt-6 text-center">
      <button type="button" @click="loadItems(false)" :disabled="loading"
              class="px-5 py-2.5 rounded-xl bg-surface border border-line text-sm font-medium text-ink hover:bg-canvas transition-colors inline-flex items-center gap-2">
        <Icon name="arrowdown" :size="16" /> {{ loading ? '加载中…' : '发现更多好物' }}
      </button>
    </div>

    <p v-if="!loading && items.length && !hasMore" class="py-9 text-center text-xs text-muted">好物已全部呈现 · 让每一次循环都有意义</p>

    <PublishDialog v-if="showPublish" @close="showPublish = false" @saved="onPublished" />
  </div>
</template>
