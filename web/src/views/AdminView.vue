<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import Avatar from '@/components/Avatar.vue'
import ItemImage from '@/components/ItemImage.vue'
import { api } from '@/lib/api'
import { useUiStore } from '@/stores/ui'
import { useCategoryStore } from '@/stores/category'
import {
  itemStatusChip, itemStatusLabel, statusChip, statusLabel,
  reviewChip, reviewLabel, catChip, catFg,
} from '@/lib/format'

const ui = useUiStore()
const categoryStore = useCategoryStore()
const router = useRouter()

const tab = ref('items')
const summary = ref({})
const items = ref([])
const reports = ref([])
const orders = ref([])
const users = ref([])
const products = ref([])
const categories = ref([])
const loading = ref(true)

const itemQuery = ref('')
const itemStatus = ref('')
const itemReview = ref('')
const reportStatus = ref('open')

const showProductForm = ref(false)
const pForm = ref({})
const pErr = ref('')
const savingProduct = ref(false)

const showCategoryForm = ref(false)
const cForm = ref({})
const cErr = ref('')
const savingCategory = ref(false)

// 驳回理由弹窗
const rejectTarget = ref(null)
const rejectNote = ref('')
const rejectErr = ref('')

const tabs = computed(() => [
  { key: 'items', label: '物品审核', icon: 'box', badge: summary.value.pending_review || 0 },
  { key: 'reports', label: '举报处理', icon: 'flag', badge: summary.value.open_reports || 0 },
  { key: 'orders', label: '全平台订单', icon: 'cart' },
  { key: 'users', label: '用户', icon: 'user' },
  { key: 'products', label: '礼品管理', icon: 'gift' },
  { key: 'categories', label: '分类管理', icon: 'archive' },
])

// 后端已按「待审核 → 已驳回 → 其它」排序，前端只做本地过滤
const filteredItems = computed(() => {
  const q = itemQuery.value.toLowerCase()
  return items.value.filter(i =>
    (!itemStatus.value || i.status === itemStatus.value) &&
    (!itemReview.value || i.review_status === itemReview.value) &&
    (!q || i.title.toLowerCase().includes(q) || i.owner_name.toLowerCase().includes(q)))
})

async function loadAll() {
  loading.value = true
  try {
    const [s, i, u, o, p, c] = await Promise.all([
      api.get('/api/admin/summary'), api.get('/api/admin/items'),
      api.get('/api/admin/users'), api.get('/api/admin/orders'),
      api.get('/api/products'), api.get('/api/categories'),
    ])
    summary.value = s; items.value = i; users.value = u
    orders.value = o; products.value = p; categories.value = c
    await loadReports()
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}
async function loadReports() {
  try {
    reports.value = await api.get('/api/admin/reports' + (reportStatus.value ? '?status=' + reportStatus.value : ''))
  } catch (e) { ui.toast(e.message, 'error') }
}

async function itemAction(it, act) {
  const label = act === 'offshelf' ? '下架' : '恢复上架'
  if (!(await ui.ask({ title: `${label}物品`, text: `确定要${label}《${it.title}》吗？`, ok: `确认${label}`, danger: act === 'offshelf' }))) return
  try {
    await api.post(`/api/admin/items/${it.id}/${act}`, {})
    ui.toast(`物品已${label}`)
    await loadAll()
  } catch (e) { ui.toast(e.message, 'error') }
}

/** 审核通过 */
async function approveItem(it) {
  if (!(await ui.ask({ title: '审核通过', text: `确认通过《${it.title}》的审核？通过后将在市集展示。`, ok: '审核通过' }))) return
  try {
    await api.post(`/api/admin/items/${it.id}/review`, { approve: true })
    ui.toast('已审核通过')
    await loadAll()
  } catch (e) { ui.toast(e.message, 'error') }
}

/** 打开驳回理由弹窗（驳回必须说明理由） */
function openReject(it) {
  rejectTarget.value = it
  rejectNote.value = ''
  rejectErr.value = ''
}
async function submitReject() {
  if (rejectNote.value.trim().length < 2) { rejectErr.value = '请填写驳回理由（至少 2 个字）'; return }
  try {
    await api.post(`/api/admin/items/${rejectTarget.value.id}/review`, { approve: false, note: rejectNote.value.trim() })
    ui.toast('已驳回该物品')
    rejectTarget.value = null
    await loadAll()
  } catch (e) { rejectErr.value = e.message }
}

async function resolveReport(r) {
  if (!(await ui.ask({ title: '处理举报', text: '确认将该举报标记为已处理吗？', ok: '标记已处理' }))) return
  try {
    await api.post(`/api/admin/reports/${r.id}/resolve`, {})
    ui.toast('举报已标记为处理完成')
    await loadAll()
  } catch (e) { ui.toast(e.message, 'error') }
}

/* ---------- 礼品 ---------- */
function openProductForm(p) {
  pForm.value = p ? { ...p } : { name: '', description: '', cost_points: 50, stock: 10, emoji: '🎁' }
  pErr.value = ''
  showProductForm.value = true
}
async function submitProduct() {
  if (!pForm.value.name) { pErr.value = '请填写礼品名称'; return }
  if (!pForm.value.cost_points || pForm.value.cost_points < 1) { pErr.value = '所需积分至少为 1'; return }
  savingProduct.value = true
  try {
    const body = {
      name: pForm.value.name, description: pForm.value.description,
      cost_points: pForm.value.cost_points, stock: pForm.value.stock, emoji: pForm.value.emoji,
    }
    if (pForm.value.id) await api.patch(`/api/admin/products/${pForm.value.id}`, body)
    else await api.post('/api/admin/products', body)
    ui.toast('礼品已保存')
    showProductForm.value = false
    await loadAll()
  } catch (e) {
    pErr.value = e.message
  } finally {
    savingProduct.value = false
  }
}
async function deleteProduct(p) {
  if (!(await ui.ask({ title: '删除礼品', text: `确定删除「${p.name}」吗？该操作不可撤销。`, ok: '确认删除', danger: true }))) return
  try {
    await api.del(`/api/admin/products/${p.id}`)
    ui.toast('礼品已删除')
    await loadAll()
  } catch (e) { ui.toast(e.message, 'error') }
}

/* ---------- 分类 ---------- */
const ICON_CHOICES = ['box', 'book', 'pencil', 'sofa', 'store', 'gift', 'image', 'leaf', 'recycle', 'coin']
function openCategoryForm(c) {
  cForm.value = c ? { ...c } : { name: '', icon: 'box', carbon_factor: 2.0, sort_order: 50 }
  cErr.value = ''
  showCategoryForm.value = true
}
async function submitCategory() {
  if (!cForm.value.name || !cForm.value.name.trim()) { cErr.value = '请填写分类名称'; return }
  if (cForm.value.carbon_factor == null || cForm.value.carbon_factor < 0) { cErr.value = '减碳系数不能为负'; return }
  savingCategory.value = true
  try {
    const body = {
      name: cForm.value.name.trim(), icon: cForm.value.icon,
      carbon_factor: cForm.value.carbon_factor, sort_order: cForm.value.sort_order ?? 50,
    }
    if (cForm.value.id) await api.patch(`/api/admin/categories/${cForm.value.id}`, body)
    else await api.post('/api/admin/categories', body)
    ui.toast('分类已保存')
    showCategoryForm.value = false
    await loadAll()
    await categoryStore.load(true)   // 让市集/发布表单立即拿到最新分类
  } catch (e) {
    cErr.value = e.message
  } finally {
    savingCategory.value = false
  }
}
async function deleteCategory(c) {
  if (!(await ui.ask({
    title: '删除分类',
    text: `确定删除分类「${c.name}」吗？${c.item_count ? `当前有 ${c.item_count} 件物品属于该分类。` : ''}`,
    ok: '确认删除', danger: true,
  }))) return
  try {
    await api.del(`/api/admin/categories/${c.id}`)
    ui.toast('分类已删除')
    await loadAll()
    await categoryStore.load(true)
  } catch (e) { ui.toast(e.message, 'error') }
}

const cards = computed(() => [
  { label: `订单总数 · 已完成 ${summary.value.orders_completed ?? 0}`, value: summary.value.orders_total ?? 0, icon: 'cart', bg: 'bg-blue-50 dark:bg-blue-500/10', fg: 'text-blue-600' },
  { label: '待审核物品', value: summary.value.pending_review ?? 0, icon: 'box', bg: summary.value.pending_review > 0 ? 'bg-amber-50 dark:bg-amber-500/10' : 'bg-canvas', fg: summary.value.pending_review > 0 ? 'text-amber-600' : 'text-subtle', danger: summary.value.pending_review > 0 },
  { label: `待处理举报 · 涉及 ${summary.value.flagged_items ?? 0} 件物品`, value: summary.value.open_reports ?? 0, icon: 'flag', bg: summary.value.open_reports > 0 ? 'bg-red-50 dark:bg-red-500/10' : 'bg-canvas', fg: summary.value.open_reports > 0 ? 'text-red-600' : 'text-subtle', danger: summary.value.open_reports > 0 },
  { label: '全校累计减碳（kg CO₂e）', value: summary.value.total_carbon_kg ?? 0, icon: 'tree', bg: 'bg-brand-50 dark:bg-brand-500/10', fg: 'text-brand-600' },
])

onMounted(loadAll)
</script>

<template>
  <div class="animate-rise">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-ink inline-flex items-center gap-2"><Icon name="shield" :size="20" class="text-brand-600" />平台管理后台</h1>
        <p class="mt-1 text-sm text-muted">审核物品、处理举报、维护分类与礼品</p>
      </div>
      <button type="button" @click="loadAll"
              class="h-10 px-4 rounded-xl bg-surface border border-line text-sm font-medium text-ink hover:bg-canvas transition-colors inline-flex items-center gap-2">
        <Icon name="refresh" :size="16" /> 刷新数据
      </button>
    </div>

    <div class="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="c in cards" :key="c.label" class="p-4 rounded-xl2 bg-surface border shadow-card"
           :class="c.danger ? 'border-red-300 dark:border-red-500/40' : 'border-line'">
        <span class="grid place-items-center w-9 h-9 rounded-xl" :class="c.bg"><Icon :name="c.icon" :size="18" :class="c.fg" /></span>
        <p class="mt-3 text-2xl font-bold tnum leading-none" :class="c.danger ? 'text-red-600' : 'text-ink'">{{ c.value }}</p>
        <p class="mt-1.5 text-[11px] text-muted">{{ c.label }}</p>
      </div>
    </div>

    <div class="mt-4 rounded-xl2 bg-surface border border-line shadow-card overflow-hidden">
      <div class="flex gap-1 p-2 border-b border-line overflow-x-auto no-bar" role="tablist">
        <button v-for="t in tabs" :key="t.key" type="button" role="tab" :aria-selected="tab === t.key" @click="tab = t.key"
                class="px-3.5 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors inline-flex items-center gap-2"
                :class="tab === t.key ? 'bg-brand-50 dark:bg-brand-500/15 text-brand-700 dark:text-brand-300' : 'text-muted hover:text-ink hover:bg-canvas'">
          <Icon :name="t.icon" :size="16" />{{ t.label }}
          <span v-if="t.badge" class="px-1.5 rounded-md bg-red-500 text-white text-[10px] font-bold tnum">{{ t.badge }}</span>
        </button>
      </div>

      <!-- 物品审核 -->
      <div v-show="tab === 'items'" class="p-5">
        <div class="flex flex-wrap items-center gap-2 mb-4">
          <input v-model.trim="itemQuery" placeholder="搜索物品或发布者…" aria-label="搜索物品"
                 class="h-9 flex-1 min-w-[180px] px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          <select v-model="itemReview" aria-label="审核状态筛选"
                  class="h-9 px-3 rounded-xl bg-canvas border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500/40">
            <option value="">全部审核状态</option><option value="pending">待审核</option>
            <option value="rejected">已驳回</option><option value="approved">已通过</option>
          </select>
          <select v-model="itemStatus" aria-label="上架状态筛选"
                  class="h-9 px-3 rounded-xl bg-canvas border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500/40">
            <option value="">全部上架状态</option><option value="available">在售</option><option value="reserved">已预约</option>
            <option value="completed">已流转</option><option value="offshelf">已下架</option>
          </select>
        </div>
        <p class="mb-3 text-[12px] text-subtle inline-flex items-center gap-1.5">
          <Icon name="info" :size="14" /> 点击任意一行可查看物品详情（含图片与完整描述），便于逐条审核
        </p>
        <div class="overflow-x-auto -mx-5 px-5">
          <table class="w-full text-sm min-w-[860px]">
            <thead><tr class="text-left text-[11px] uppercase tracking-wider text-subtle border-b border-line">
              <th class="py-2.5 font-medium">物品</th><th class="py-2.5 font-medium">发布者</th>
              <th class="py-2.5 font-medium">审核</th><th class="py-2.5 font-medium">上架</th>
              <th class="py-2.5 font-medium">举报</th><th class="py-2.5 font-medium text-right">操作</th>
            </tr></thead>
            <tbody class="divide-y divide-line">
              <!-- 整行可点击进入详情页；操作按钮用 .stop 阻止冒泡 -->
              <tr v-for="it in filteredItems" :key="it.id"
                  class="hover:bg-canvas/70 transition-colors cursor-pointer"
                  tabindex="0" role="link" :aria-label="`查看《${it.title}》详情`"
                  @click="router.push(`/items/${it.id}`)" @keyup.enter="router.push(`/items/${it.id}`)">
                <td class="py-3 pr-3">
                  <div class="flex items-center gap-2.5 group">
                    <span class="w-10 h-10 shrink-0"><ItemImage :item="it" ratio="aspect-square" /></span>
                    <span class="min-w-0">
                      <span class="block font-medium text-ink group-hover:text-brand-700 dark:group-hover:text-brand-400 truncate max-w-[220px]">{{ it.title }}</span>
                      <span class="block text-[11px] text-subtle tnum">¥{{ it.price.toFixed(2) }} · 循环 {{ it.cycle_count }} 次 · 减碳 {{ it.carbon_saved.toFixed(1) }} kg</span>
                    </span>
                  </div>
                </td>
                <td class="py-3 pr-3 text-muted">{{ it.owner_name }}</td>
                <td class="py-3 pr-3">
                  <span class="px-2.5 py-1 rounded-lg text-[11px] font-semibold whitespace-nowrap" :class="reviewChip(it.review_status)">{{ reviewLabel(it.review_status) }}</span>
                  <p v-if="it.review_status === 'rejected' && it.review_note" class="mt-1 text-[11px] text-rose-500 max-w-[160px] truncate" :title="it.review_note">{{ it.review_note }}</p>
                </td>
                <td class="py-3 pr-3"><span class="px-2.5 py-1 rounded-lg text-[11px] font-semibold whitespace-nowrap" :class="itemStatusChip(it.status)">{{ itemStatusLabel(it.status) }}</span></td>
                <td class="py-3 pr-3">
                  <span v-if="it.report_count > 0" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-red-100 dark:bg-red-500/15 text-red-600 text-[11px] font-bold">
                    <Icon name="flag" :size="12" />{{ it.report_count }}
                  </span>
                  <span v-else class="text-subtle text-xs">—</span>
                </td>
                <td class="py-3 text-right whitespace-nowrap" @click.stop>
                  <div class="inline-flex items-center gap-1.5 justify-end">
                    <template v-if="it.review_status !== 'approved'">
                      <button type="button" @click="approveItem(it)"
                              class="h-8 px-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold transition-colors">通过</button>
                      <button type="button" @click="openReject(it)"
                              class="h-8 px-2.5 rounded-lg border border-line text-red-600 text-xs font-medium hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors">驳回</button>
                    </template>
                    <button type="button" @click="router.push(`/items/${it.id}`)"
                            class="h-8 px-2.5 rounded-lg border border-line text-xs text-muted hover:text-ink hover:bg-canvas transition-colors">详情</button>
                    <button v-if="it.status !== 'offshelf' && it.status !== 'completed'" type="button" @click="itemAction(it, 'offshelf')"
                            class="h-8 px-2.5 rounded-lg bg-red-50 dark:bg-red-500/10 text-red-600 text-xs font-medium hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors">下架</button>
                    <button v-else-if="it.status === 'offshelf'" type="button" @click="itemAction(it, 'restore')"
                            class="h-8 px-2.5 rounded-lg bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300 text-xs font-medium hover:bg-brand-100 dark:hover:bg-brand-500/20 transition-colors">恢复上架</button>
                    <span v-else class="text-[11px] text-subtle">已结束</span>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredItems.length === 0"><td colspan="6" class="py-12 text-center text-sm text-subtle">没有匹配的物品</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 举报处理 -->
      <div v-show="tab === 'reports'" class="p-5">
        <div class="flex items-center gap-2 mb-4">
          <button v-for="s in [{ k: 'open', n: '待处理' }, { k: 'resolved', n: '已处理' }, { k: '', n: '全部' }]" :key="s.n"
                  type="button" @click="reportStatus = s.k; loadReports()"
                  class="h-9 px-3.5 rounded-xl text-sm font-medium transition-colors"
                  :class="reportStatus === s.k ? 'bg-brand-600 text-white' : 'bg-canvas border border-line text-muted hover:text-ink'">{{ s.n }}</button>
        </div>
        <div v-if="reports.length === 0" class="py-14 text-center">
          <span class="grid place-items-center w-14 h-14 rounded-2xl bg-brand-50 dark:bg-brand-500/10 text-brand-600 mx-auto"><Icon name="check" :size="26" /></span>
          <p class="mt-3 text-sm text-muted">暂无举报，平台风平浪静</p>
        </div>
        <ul v-else class="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <li v-for="r in reports" :key="r.id" class="p-4 rounded-xl border"
              :class="r.status === 'open' ? 'border-red-200 dark:border-red-500/30 bg-red-50/50 dark:bg-red-500/5' : 'border-line bg-canvas/50'">
            <div class="flex items-start justify-between gap-2">
              <RouterLink :to="`/items/${r.item_id}`" class="text-sm font-semibold text-ink hover:text-brand-700 dark:hover:text-brand-400">{{ r.item_title }}</RouterLink>
              <span class="px-2 py-0.5 rounded-lg text-[11px] font-semibold shrink-0"
                    :class="r.status === 'open' ? 'bg-red-100 dark:bg-red-500/15 text-red-600' : 'bg-canvas text-subtle border border-line'">
                {{ r.status === 'open' ? '待处理' : '已处理' }}
              </span>
            </div>
            <p class="mt-1.5 text-[13px] text-muted">“{{ r.reason }}”</p>
            <p class="mt-1 text-[11px] text-subtle">{{ r.reporter_name }} 举报 · {{ r.created_at }}</p>
            <div v-if="r.status === 'open'" class="mt-3 flex gap-2">
              <button type="button" @click="resolveReport(r)"
                      class="h-8 px-3 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold transition-colors">标记已处理</button>
              <button type="button" @click="itemAction({ id: r.item_id, title: r.item_title }, 'offshelf')"
                      class="h-8 px-3 rounded-lg bg-red-50 dark:bg-red-500/10 text-red-600 text-xs font-semibold hover:bg-red-100 transition-colors">下架该物品</button>
            </div>
          </li>
        </ul>
      </div>

      <!-- 全平台订单 -->
      <div v-show="tab === 'orders'" class="p-5">
        <div class="overflow-x-auto -mx-5 px-5">
          <table class="w-full text-sm min-w-[760px]">
            <thead><tr class="text-left text-[11px] uppercase tracking-wider text-subtle border-b border-line">
              <th class="py-2.5 font-medium">物品</th><th class="py-2.5 font-medium">买家</th><th class="py-2.5 font-medium">卖家</th>
              <th class="py-2.5 font-medium">自提码</th><th class="py-2.5 font-medium">状态</th><th class="py-2.5 font-medium">更新时间</th>
            </tr></thead>
            <tbody class="divide-y divide-line">
              <tr v-for="o in orders" :key="o.id" class="hover:bg-canvas/70 transition-colors">
                <td class="py-3 pr-3">
                  <RouterLink :to="`/items/${o.item_id}`" class="font-medium text-ink hover:text-brand-700 dark:hover:text-brand-400">{{ o.item_title }}</RouterLink>
                  <p class="text-[11px] text-subtle tnum">¥{{ o.price.toFixed(2) }}</p>
                </td>
                <td class="py-3 pr-3 text-muted">{{ o.buyer_name }}</td>
                <td class="py-3 pr-3 text-muted">{{ o.seller_name }}</td>
                <td class="py-3 pr-3"><code class="font-mono text-xs text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 px-1.5 py-0.5 rounded">{{ o.pickup_code }}</code></td>
                <td class="py-3 pr-3"><span class="px-2.5 py-1 rounded-lg text-[11px] font-semibold" :class="statusChip(o.status)">{{ statusLabel(o.status) }}</span></td>
                <td class="py-3 text-[11px] text-subtle">{{ o.updated_at }}</td>
              </tr>
              <tr v-if="orders.length === 0"><td colspan="6" class="py-12 text-center text-sm text-subtle">暂无订单</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 用户 -->
      <div v-show="tab === 'users'" class="p-5">
        <div class="overflow-x-auto -mx-5 px-5">
          <table class="w-full text-sm min-w-[680px]">
            <thead><tr class="text-left text-[11px] uppercase tracking-wider text-subtle border-b border-line">
              <th class="py-2.5 font-medium">用户</th><th class="py-2.5 font-medium">学院</th><th class="py-2.5 font-medium">角色</th>
              <th class="py-2.5 font-medium text-right">发布</th><th class="py-2.5 font-medium text-right">循环</th>
              <th class="py-2.5 font-medium text-right">减碳</th><th class="py-2.5 font-medium text-right">积分</th>
            </tr></thead>
            <tbody class="divide-y divide-line">
              <tr v-for="u in users" :key="u.id" class="hover:bg-canvas/70 transition-colors">
                <td class="py-3 pr-3">
                  <RouterLink :to="`/u/${u.id}`" class="inline-flex items-center gap-2.5 group">
                    <Avatar :user="u" :size="32" rounded="rounded-lg" />
                    <span>
                      <span class="block font-medium text-ink group-hover:text-brand-700 dark:group-hover:text-brand-400">{{ u.name }}</span>
                      <span class="block text-[11px] text-subtle">{{ u.student_no || '—' }}</span>
                    </span>
                  </RouterLink>
                </td>
                <td class="py-3 pr-3 text-muted">{{ u.college }}</td>
                <td class="py-3 pr-3"><span class="px-2 py-0.5 rounded-md text-[11px] font-semibold"
                      :class="u.role === 'admin' ? 'bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-300' : 'bg-canvas text-muted border border-line'">{{ u.role === 'admin' ? '管理员' : '学生' }}</span></td>
                <td class="py-3 pr-3 text-right tnum text-muted">{{ u.item_count }}</td>
                <td class="py-3 pr-3 text-right tnum text-muted">{{ u.cycles }}</td>
                <td class="py-3 pr-3 text-right tnum font-semibold text-brand-700 dark:text-brand-400">{{ u.carbon_kg.toFixed(1) }}</td>
                <td class="py-3 text-right tnum font-semibold text-amber-600">{{ u.points }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 礼品管理 -->
      <div v-show="tab === 'products'" class="p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm text-muted">共 {{ products.length }} 件礼品</p>
          <button type="button" @click="openProductForm(null)"
                  class="h-9 px-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold inline-flex items-center gap-1.5 transition-colors">
            <Icon name="plus" :size="15" /> 新增礼品
          </button>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <div v-for="p in products" :key="p.id" class="p-4 rounded-xl border border-line bg-canvas/50">
            <div class="flex items-start justify-between gap-2">
              <span class="grid place-items-center w-11 h-11 rounded-xl bg-surface border border-line text-2xl select-none" aria-hidden="true">{{ p.emoji }}</span>
              <div class="flex gap-1">
                <button type="button" @click="openProductForm(p)" aria-label="编辑礼品"
                        class="grid place-items-center w-8 h-8 rounded-lg border border-line text-muted hover:text-ink hover:bg-surface transition-colors"><Icon name="edit" :size="14" /></button>
                <button type="button" @click="deleteProduct(p)" aria-label="删除礼品"
                        class="grid place-items-center w-8 h-8 rounded-lg border border-line text-muted hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors"><Icon name="trash" :size="14" /></button>
              </div>
            </div>
            <p class="mt-2.5 font-semibold text-ink">{{ p.name }}</p>
            <p class="mt-0.5 text-[12px] text-muted clamp-2">{{ p.description }}</p>
            <div class="mt-2.5 flex items-center gap-3 text-[12px]">
              <span class="inline-flex items-center gap-1 text-amber-600 font-semibold"><Icon name="coin" :size="13" />{{ p.cost_points }}</span>
              <span class="text-muted">库存 <b class="tnum" :class="p.stock > 0 ? 'text-ink' : 'text-rose-500'">{{ p.stock }}</b></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 分类管理 -->
      <div v-show="tab === 'categories'" class="p-5">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm text-muted">共 {{ categories.length }} 个分类 · 「其它」为系统兜底分类，不可删除</p>
          <button type="button" @click="openCategoryForm(null)"
                  class="h-9 px-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold inline-flex items-center gap-1.5 transition-colors">
            <Icon name="plus" :size="15" /> 新增分类
          </button>
        </div>
        <div class="overflow-x-auto -mx-5 px-5">
          <table class="w-full text-sm min-w-[620px]">
            <thead><tr class="text-left text-[11px] uppercase tracking-wider text-subtle border-b border-line">
              <th class="py-2.5 font-medium">分类</th><th class="py-2.5 font-medium">单次减碳系数</th>
              <th class="py-2.5 font-medium">排序</th><th class="py-2.5 font-medium text-right">物品数</th>
              <th class="py-2.5 font-medium text-right">操作</th>
            </tr></thead>
            <tbody class="divide-y divide-line">
              <tr v-for="c in categories" :key="c.id" class="hover:bg-canvas/70 transition-colors">
                <td class="py-3 pr-3">
                  <span class="inline-flex items-center gap-2.5">
                    <span class="grid place-items-center w-9 h-9 rounded-xl border" :class="catChip(c.name)">
                      <Icon :name="c.icon || 'box'" :size="17" />
                    </span>
                    <span>
                      <span class="font-medium text-ink">{{ c.name }}</span>
                      <span v-if="c.protected" class="ml-2 px-1.5 py-px rounded-md bg-canvas border border-line text-[10px] text-subtle">兜底</span>
                    </span>
                  </span>
                </td>
                <td class="py-3 pr-3 text-muted tnum">{{ c.carbon_factor }} kg CO₂e</td>
                <td class="py-3 pr-3 text-muted tnum">{{ c.sort_order }}</td>
                <td class="py-3 pr-3 text-right text-muted tnum">{{ c.item_count }}</td>
                <td class="py-3 text-right whitespace-nowrap">
                  <div class="inline-flex items-center gap-1.5 justify-end">
                    <button type="button" @click="openCategoryForm(c)"
                            class="h-8 px-2.5 rounded-lg border border-line text-xs text-muted hover:text-ink hover:bg-canvas transition-colors">编辑</button>
                    <button v-if="!c.protected" type="button" @click="deleteCategory(c)"
                            class="h-8 px-2.5 rounded-lg bg-red-50 dark:bg-red-500/10 text-red-600 text-xs font-medium hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors">删除</button>
                    <span v-else class="text-[11px] text-subtle">受保护</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 礼品表单 -->
    <transition name="fade">
      <div v-if="showProductForm" class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
           @click.self="showProductForm = false">
        <transition name="sheet" appear>
          <div class="w-full sm:max-w-md bg-elevated rounded-t-2xl sm:rounded-2xl shadow-lift" role="dialog" aria-modal="true">
            <div class="flex items-center justify-between px-5 py-4 border-b border-line">
              <h3 class="font-semibold text-ink">{{ pForm.id ? '编辑礼品' : '新增礼品' }}</h3>
              <button type="button" @click="showProductForm = false" aria-label="关闭"
                      class="grid place-items-center w-8 h-8 rounded-lg text-muted hover:text-ink hover:bg-canvas transition-colors"><Icon name="close" :size="18" /></button>
            </div>
            <div class="p-5 space-y-4">
              <div class="grid grid-cols-[72px_1fr] gap-3">
                <div>
                  <label for="pr-emoji" class="block text-[13px] font-medium text-ink mb-1.5">图标</label>
                  <input id="pr-emoji" v-model="pForm.emoji" maxlength="4" class="w-full h-11 text-center text-xl rounded-xl bg-canvas border border-line focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                </div>
                <div>
                  <label for="pr-name" class="block text-[13px] font-medium text-ink mb-1.5">礼品名称 <span class="text-rose-500">*</span></label>
                  <input id="pr-name" v-model.trim="pForm.name" maxlength="40" placeholder="例如：定制帆布袋"
                         class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                </div>
              </div>
              <div>
                <label for="pr-desc" class="block text-[13px] font-medium text-ink mb-1.5">描述</label>
                <input id="pr-desc" v-model.trim="pForm.description" maxlength="200" placeholder="礼品说明"
                       class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label for="pr-cost" class="block text-[13px] font-medium text-ink mb-1.5">所需积分</label>
                  <input id="pr-cost" v-model.number="pForm.cost_points" type="number" min="1" class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink tnum focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                </div>
                <div>
                  <label for="pr-stock" class="block text-[13px] font-medium text-ink mb-1.5">库存</label>
                  <input id="pr-stock" v-model.number="pForm.stock" type="number" min="0" class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink tnum focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                </div>
              </div>
              <p v-if="pErr" class="text-[13px] text-rose-500">{{ pErr }}</p>
            </div>
            <div class="flex justify-end gap-2 px-5 py-4 border-t border-line">
              <button type="button" @click="showProductForm = false" class="h-10 px-4 rounded-xl text-sm font-medium text-muted hover:bg-canvas transition-colors">取消</button>
              <button type="button" @click="submitProduct" :disabled="savingProduct"
                      class="h-10 px-5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50 transition-colors">{{ savingProduct ? '保存中…' : '保存' }}</button>
            </div>
          </div>
        </transition>
      </div>
    </transition>

    <!-- 分类表单 -->
    <transition name="fade">
      <div v-if="showCategoryForm" class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
           @click.self="showCategoryForm = false">
        <transition name="sheet" appear>
          <div class="w-full sm:max-w-md bg-elevated rounded-t-2xl sm:rounded-2xl shadow-lift" role="dialog" aria-modal="true">
            <div class="flex items-center justify-between px-5 py-4 border-b border-line">
              <h3 class="font-semibold text-ink">{{ cForm.id ? '编辑分类' : '新增分类' }}</h3>
              <button type="button" @click="showCategoryForm = false" aria-label="关闭"
                      class="grid place-items-center w-8 h-8 rounded-lg text-muted hover:text-ink hover:bg-canvas transition-colors"><Icon name="close" :size="18" /></button>
            </div>
            <div class="p-5 space-y-4">
              <div>
                <label for="cf-name" class="block text-[13px] font-medium text-ink mb-1.5">分类名称 <span class="text-rose-500">*</span></label>
                <input id="cf-name" v-model.trim="cForm.name" maxlength="10" placeholder="例如：数码产品"
                       class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                <p class="mt-1 text-[11px] text-subtle">重命名分类会同步更新属于该分类的物品</p>
              </div>
              <div>
                <label class="block text-[13px] font-medium text-ink mb-1.5">图标</label>
                <div class="flex flex-wrap gap-1.5">
                  <button v-for="ic in ICON_CHOICES" :key="ic" type="button" @click="cForm.icon = ic"
                          class="grid place-items-center w-10 h-10 rounded-xl border transition-colors"
                          :class="cForm.icon === ic ? 'border-brand-500 bg-brand-50 dark:bg-brand-500/10 text-brand-600' : 'border-line text-muted hover:bg-canvas'"
                          :aria-label="`选择图标 ${ic}`">
                    <Icon :name="ic" :size="18" />
                  </button>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label for="cf-carbon" class="block text-[13px] font-medium text-ink mb-1.5">单次减碳系数（kg）</label>
                  <input id="cf-carbon" v-model.number="cForm.carbon_factor" type="number" min="0" step="0.1"
                         class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink tnum focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                </div>
                <div>
                  <label for="cf-sort" class="block text-[13px] font-medium text-ink mb-1.5">排序（越小越前）</label>
                  <input id="cf-sort" v-model.number="cForm.sort_order" type="number" min="0"
                         class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink tnum focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                </div>
              </div>
              <p v-if="cErr" class="text-[13px] text-rose-500">{{ cErr }}</p>
            </div>
            <div class="flex justify-end gap-2 px-5 py-4 border-t border-line">
              <button type="button" @click="showCategoryForm = false" class="h-10 px-4 rounded-xl text-sm font-medium text-muted hover:bg-canvas transition-colors">取消</button>
              <button type="button" @click="submitCategory" :disabled="savingCategory"
                      class="h-10 px-5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50 transition-colors">{{ savingCategory ? '保存中…' : '保存' }}</button>
            </div>
          </div>
        </transition>
      </div>
    </transition>

    <!-- 驳回理由 -->
    <transition name="fade">
      <div v-if="rejectTarget" class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
           @click.self="rejectTarget = null">
        <transition name="sheet" appear>
          <div class="w-full sm:max-w-md bg-elevated rounded-t-2xl sm:rounded-2xl shadow-lift" role="dialog" aria-modal="true">
            <div class="flex items-center justify-between px-5 py-4 border-b border-line">
              <h3 class="font-semibold text-ink">驳回物品</h3>
              <button type="button" @click="rejectTarget = null" aria-label="关闭"
                      class="grid place-items-center w-8 h-8 rounded-lg text-muted hover:text-ink hover:bg-canvas transition-colors"><Icon name="close" :size="18" /></button>
            </div>
            <div class="p-5">
              <p class="text-sm text-muted">驳回对象：<b class="text-ink">{{ rejectTarget.title }}</b></p>
              <label for="reject-note" class="block text-[13px] font-medium text-ink mt-4 mb-1.5">驳回理由（2–200 字，将展示给发布者）</label>
              <textarea id="reject-note" v-model.trim="rejectNote" rows="3" maxlength="200"
                        placeholder="例如：图片与描述不符，请补充实物照片后重新提交"
                        class="w-full px-3.5 py-2.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/40"></textarea>
              <p class="mt-1 text-right text-[11px] text-subtle tnum">{{ rejectNote.length }}/200</p>
              <p v-if="rejectErr" class="mt-1 text-[12px] text-rose-500">{{ rejectErr }}</p>
            </div>
            <div class="flex justify-end gap-2 px-5 py-4 border-t border-line">
              <button type="button" @click="rejectTarget = null" class="h-10 px-4 rounded-xl text-sm font-medium text-muted hover:bg-canvas transition-colors">取消</button>
              <button type="button" @click="submitReject"
                      class="h-10 px-5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-sm font-semibold transition-colors">确认驳回</button>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </div>
</template>
