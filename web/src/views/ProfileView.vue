<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import Icon from '@/components/Icon.vue'
import Avatar from '@/components/Avatar.vue'
import ItemImage from '@/components/ItemImage.vue'
import FulfillDialog from '@/components/FulfillDialog.vue'
import PublishDialog from '@/components/PublishDialog.vue'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { itemStatusChip, itemStatusLabel, statusChip, statusLabel, catBg, catFg, catIcon, isGain, reviewChip, reviewLabel } from '@/lib/format'

const auth = useAuthStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()

const validTabs = ['points', 'buy', 'sell', 'items', 'fav', 'reports', 'gifts']
const tab = ref(validTabs.includes(route.query.tab) ? route.query.tab : 'points')
const summary = ref({})
const pointLogs = ref([])
const orders = ref([])
const myItems = ref([])
const favorites = ref([])
const myReports = ref([])
const loading = ref(true)
const editItem = ref(null)
const completing = ref(null)
const busyOrder = ref(null)
const orderFilter = ref('')
const loadError = ref('')
const redemptions = ref([])

const tabs = computed(() => [
  { key: 'gifts', label: '兑换记录', icon: 'gift', count: redemptions.value.length },
  { key: 'points', label: '积分流水', icon: 'coin' },
  { key: 'buy', label: '我买到的', icon: 'cart', count: ordersFor('buy').length },
  { key: 'sell', label: '我卖出的', icon: 'handshake', count: ordersFor('sell').length },
  { key: 'items', label: '我发布的', icon: 'box', count: myItems.value.length },
  { key: 'fav', label: '我的收藏', icon: 'heart', count: favorites.value.length },
  { key: 'reports', label: '我的举报', icon: 'flag', count: myReports.value.length },
])
const stats = computed(() => {
  const s = summary.value.stats || {}
  return [
    { label: '累计减碳（kg）', value: (s.carbon_kg ?? 0).toFixed(1) },
    { label: '循环流转（次）', value: s.cycles ?? 0 },
    { label: '发布物品（件）', value: s.published ?? 0 },
    { label: '收藏关注（件）', value: s.favorites ?? 0 },
  ]
})

const ordersFor = (kind) => orders.value.filter(o => kind === 'buy' ? o.buyer_id === auth.user?.id : o.seller_id === auth.user?.id)

function orderActions(o) {
  const acts = []
  if (o.status === 'reserved' && o.seller_id === auth.user?.id)
    acts.push({ act: 'confirm', label: '确认预约', cls: 'bg-brand-600 hover:bg-brand-700 text-white' })
  if (o.status === 'confirmed')
    acts.push({ act: 'complete', label: '完成流转', cls: 'bg-blue-600 hover:bg-blue-700 text-white' })
  if (['reserved', 'confirmed'].includes(o.status))
    acts.push({ act: 'cancel', label: '取消订单', cls: 'bg-canvas border border-line text-muted hover:text-rose-600' })
  return acts
}

async function doOrderAction(o, act) {
  if (busyOrder.value !== null) return
  if (act === 'complete') { completing.value = o; return }
  if (act === 'cancel') {
    if (!(await ui.ask({ title: '取消订单', text: `确定取消《${o.item_title}》的订单吗？物品将重新上架。`, ok: '确认取消', danger: true }))) return
  }
  busyOrder.value = o.id
  try {
    await api.post(`/api/orders/${o.id}/${act}`, {})
    ui.toast(act === 'confirm' ? '已确认预约，请与买家约定自提' : '订单已取消')
    await loadAll()
    await auth.refresh()
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally { busyOrder.value = null }
}

async function removeFavorite(f) {
  if (!(await ui.ask({ title: '取消收藏', text: `确定取消收藏《${f.item_title}》吗？`, ok: '取消收藏' }))) return
  try {
    await api.del(`/api/favorites/${f.item_id}`)
    ui.toast('已取消收藏')
    await loadAll()
  } catch (e) { ui.toast(e.message, 'error') }
}

async function askOffshelf(it) {
  if (!(await ui.ask({ title: '下架物品', text: `确定下架《${it.title}》吗？下架后市集不再展示。`, ok: '确认下架', danger: true }))) return
  try {
    await api.del(`/api/items/${it.id}`)
    ui.toast('物品已下架')
    await loadAll()
  } catch (e) { ui.toast(e.message, 'error') }
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    const [s, logs, ords, mine, favs, reps, gifts] = await Promise.all([
      api.get('/api/me/summary'), api.get('/api/point-logs'),
      api.get('/api/orders'), api.get('/api/items/mine'), api.get('/api/favorites'),
      api.get('/api/reports/mine'), api.get('/api/redemptions'),
    ])
    summary.value = s; pointLogs.value = logs; orders.value = ords
    myItems.value = mine; favorites.value = favs; myReports.value = reps; redemptions.value = gifts
  } catch (e) {
    if (e.status !== 401) loadError.value = e.message
  } finally {
    loading.value = false
  }
}

watch(() => route.query.tab, (t) => { tab.value = validTabs.includes(t) ? t : 'points' })
watch(tab, (t) => router.replace({ name: 'me', query: { tab: t } }))
onMounted(loadAll)
</script>

<template>
  <div class="animate-rise">
    <div v-if="loading" class="space-y-4">
      <div class="skel h-40 rounded-xl2"></div>
      <div class="skel h-64 rounded-xl2"></div>
    </div>

    <div v-else-if="loadError" role="alert" class="p-8 rounded-xl2 border border-line bg-surface text-center"><p class="text-muted">{{ loadError }}</p><button type="button" @click="loadAll" class="primary-action mt-4">重新加载个人中心</button></div>
    <template v-else-if="auth.user">
      <!-- 资料卡 -->
      <div class="p-6 rounded-xl2 bg-gradient-to-br from-brand-600 to-emerald-800 text-white shadow-card">
        <div class="flex flex-wrap items-center gap-5">
          <Avatar :user="auth.user" :size="64" rounded="rounded-2xl" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="text-xl font-bold">{{ auth.user.name }}</h1>
              <span class="px-2 py-0.5 rounded-md bg-white/15 text-[11px] font-semibold">{{ auth.isAdmin ? '平台管理员' : '在校学生' }}</span>
            </div>
            <p class="mt-1 text-sm text-white/75">{{ auth.user.college }}<span v-if="auth.user.student_no"> · 学号 {{ auth.user.student_no }}</span></p>
            <p v-if="auth.user.bio" class="mt-1 text-[13px] text-white/70">{{ auth.user.bio }}</p>
          </div>
          <div class="text-right">
            <p class="text-[11px] text-white/70">我的碳积分</p>
            <p class="text-3xl font-bold tnum">{{ auth.user.points }}</p>
          </div>
          <RouterLink :to="{ name: 'profile-edit' }"
                      class="h-10 px-4 rounded-xl bg-white/15 hover:bg-white/25 backdrop-blur text-sm font-semibold inline-flex items-center gap-2 transition-colors">
            <Icon name="edit" :size="16" /> 编辑资料
          </RouterLink>
        </div>
        <div class="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div v-for="s in stats" :key="s.label" class="p-3 rounded-xl bg-white/10 backdrop-blur">
            <p class="text-lg font-bold tnum">{{ s.value }}</p>
            <p class="text-[11px] text-white/70">{{ s.label }}</p>
          </div>
        </div>
      </div>

      <!-- 分栏 -->
      <div class="mt-4 rounded-xl2 bg-surface border border-line shadow-card overflow-hidden">
        <div class="flex gap-1 p-2 border-b border-line overflow-x-auto no-bar" role="group" aria-label="个人中心分栏">
          <button v-for="t in tabs" :key="t.key" type="button" :aria-pressed="tab === t.key" @click="tab = t.key"
                  class="px-3.5 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors inline-flex items-center gap-2"
                  :class="tab === t.key ? 'bg-brand-50 dark:bg-brand-500/15 text-brand-700 dark:text-brand-300' : 'text-muted hover:text-ink hover:bg-canvas'">
            <Icon :name="t.icon" :size="16" />{{ t.label }}
            <span v-if="t.count != null && t.count > 0" class="px-1.5 rounded-md bg-canvas text-[10px] tnum">{{ t.count }}</span>
          </button>
        </div>

        <div v-show="tab === 'gifts'" class="p-5">
          <div class="mb-4 flex flex-wrap justify-between gap-2"><div><h2 class="font-semibold text-ink">我的绿色好礼</h2><p class="mt-1 text-xs text-muted">请凭兑换凭证到学生会办公室领取；兑换后积分已扣除。</p></div><RouterLink to="/mall" class="text-sm text-brand-700 dark:text-brand-300 hover:underline">去积分商城 →</RouterLink></div>
          <p v-if="!redemptions.length" class="py-14 text-center text-sm text-muted">暂无兑换记录，参与闲置流转赚取积分后可兑换礼品。</p>
          <ul v-else class="space-y-3"><li v-for="gift in redemptions" :key="gift.id" class="rounded-xl border border-line bg-canvas p-4"><div class="flex justify-between gap-3"><h3 class="font-semibold text-sm">{{ gift.product_name }}</h3><span class="text-sm text-amber-700 dark:text-amber-300">−{{ gift.cost_points }} 积分</span></div><p class="mt-2 text-xs text-muted">兑换凭证 <code class="text-ink break-all">{{ gift.pickup_code }}</code></p><p class="mt-1 text-xs text-muted">{{ gift.created_at }} · 领取地点：学生会办公室</p></li></ul>
          <p class="mt-4 text-xs text-muted">新增凭证仅涵盖本次升级后的兑换；历史兑换仍可在积分流水中查看。</p>
        </div>
        <!-- 积分流水 -->
        <div v-show="tab === 'points'" class="p-5">
          <p v-if="pointLogs.length === 0" class="py-14 text-center text-sm text-muted">暂无积分记录，发布一件闲置即可获得 10 碳积分</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="log in pointLogs" :key="log.id" class="py-3 flex items-center gap-3">
              <span class="grid place-items-center w-9 h-9 rounded-xl shrink-0"
                    :class="isGain(log) ? 'bg-brand-50 dark:bg-brand-500/10 text-brand-600' : 'bg-rose-50 dark:bg-rose-500/10 text-rose-500'">
                <Icon :name="isGain(log) ? 'arrowdown' : 'arrowup'" :size="16" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm text-ink truncate">{{ log.reason }}</span>
                <span class="block text-[11px] text-subtle">{{ log.created_at }}</span>
              </span>
              <span class="text-sm font-bold tnum shrink-0" :class="isGain(log) ? 'text-brand-600' : 'text-rose-500'">{{ log.delta >= 0 ? '+' : '' }}{{ log.delta }}</span>
            </li>
          </ul>
        </div>

        <!-- 我买到的 / 我卖出的 -->
        <div v-show="tab === 'buy' || tab === 'sell'" class="p-5">
          <div class="mb-4 flex flex-wrap justify-between items-center gap-3"><p class="text-xs text-muted">预约 → 卖家确认 → 线下验货 → 输入自提码完成</p><select v-model="orderFilter" aria-label="订单状态筛选" class="rounded-lg border border-line bg-canvas px-3 py-2 text-xs"><option value="">全部订单</option><option value="reserved">已预约</option><option value="confirmed">待自提</option><option value="completed">已完成</option><option value="cancelled">已取消</option></select></div>
          <p v-if="ordersFor(tab).filter(o => !orderFilter || o.status === orderFilter).length === 0" class="py-14 text-center text-sm text-muted">
            {{ orderFilter ? '当前状态下暂无订单' : tab === 'buy' ? '还没有预约过物品' : '还没有卖出记录' }}
            <RouterLink :to="{ name: 'market' }" class="block mt-2 text-brand-600 hover:underline">去市集逛逛 →</RouterLink>
          </p>
          <ul v-else class="space-y-3">
            <li v-for="o in ordersFor(tab).filter(o => !orderFilter || o.status === orderFilter)" :key="o.id" class="p-4 rounded-xl border border-line bg-canvas/60">
              <div class="flex flex-wrap items-center gap-3">
                <RouterLink :to="`/items/${o.item_id}`" class="w-12 h-12 shrink-0">
                  <ItemImage :item="{ image: o.item_image, category: o.item_category, title: o.item_title }" ratio="aspect-square" />
                </RouterLink>
                <div class="min-w-0 flex-1">
                  <RouterLink :to="`/items/${o.item_id}`" class="text-sm font-semibold text-ink hover:text-brand-700 dark:hover:text-brand-400 truncate block">
                    {{ o.item_title }} <span class="text-subtle font-normal tnum">¥{{ o.price.toFixed(2) }}</span>
                  </RouterLink>
                  <p class="mt-0.5 text-[11px] text-subtle flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    <span>{{ tab === 'buy' ? '卖家 ' + o.seller_name : '买家 ' + o.buyer_name }}</span>
                    <span class="inline-flex items-center gap-1">自提码
                      <code class="font-mono text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 px-1.5 rounded">{{ o.pickup_code }}</code>
                    </span>
                    <span>{{ o.updated_at }}</span>
                  </p>
                  <!-- 线下履约需要联系对方：仅在订单处于进行中时展示对方联系方式 -->
                  <p v-if="['reserved', 'confirmed'].includes(o.status) && o.counterparty_contact"
                     class="mt-1 text-[11px] inline-flex items-center gap-1 text-brand-700 dark:text-brand-400">
                    <Icon name="phone" :size="12" />
                    <span>联系{{ tab === 'buy' ? '卖家' : '买家' }}{{ o.counterparty_name }}：</span>
                    <code class="font-mono bg-brand-50 dark:bg-brand-500/10 px-1.5 rounded">{{ o.counterparty_contact }}</code>
                  </p>
                  <p v-else-if="['reserved', 'confirmed'].includes(o.status)"
                     class="mt-1 text-[11px] text-subtle">
                    对方尚未填写联系方式，可在个人资料中补充后告知
                  </p>
                </div>
                <span class="px-2.5 py-1 rounded-lg text-[11px] font-semibold shrink-0" :class="statusChip(o.status)">{{ statusLabel(o.status) }}</span>
              </div>
              <div v-if="orderActions(o).length" class="mt-3 pt-3 border-t border-line flex flex-wrap gap-2">
                <button v-for="a in orderActions(o)" :key="a.act" type="button" @click="doOrderAction(o, a.act)"
                        :disabled="busyOrder !== null" class="h-9 px-3 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50" :class="a.cls">{{ a.label }}</button>
              </div>
            </li>
          </ul>
        </div>

        <!-- 我发布的 -->
        <div v-show="tab === 'items'" class="p-5">
          <p v-if="myItems.length === 0" class="py-14 text-center text-sm text-muted">
            还没有发布过闲置物品
            <RouterLink :to="{ name: 'market' }" class="block mt-2 text-brand-600 hover:underline">去发布 →</RouterLink>
          </p>
          <ul v-else class="divide-y divide-line">
            <li v-for="it in myItems" :key="it.id" class="py-3 flex flex-wrap items-center gap-3">
              <RouterLink :to="`/items/${it.id}`" class="w-12 h-12 shrink-0">
                <ItemImage :item="it" ratio="aspect-square" />
              </RouterLink>
              <div class="min-w-0 flex-1">
                <RouterLink :to="`/items/${it.id}`" class="text-sm font-semibold text-ink hover:text-brand-700 dark:hover:text-brand-400 truncate block">{{ it.title }}</RouterLink>
                <p v-if="it.review_note" class="mt-1 text-xs text-rose-600 dark:text-rose-300">审核意见：{{ it.review_note }}</p>
                <p class="mt-0.5 text-[11px] text-subtle tnum">¥{{ it.price.toFixed(2) }} · 循环 {{ it.cycle_count }} 次 · 减碳 {{ it.carbon_saved.toFixed(1) }} kg · {{ it.created_at }}</p>
              </div>
              <span v-if="it.review_status !== 'approved'" class="px-2.5 py-1 rounded-lg text-[11px] font-semibold" :class="reviewChip(it.review_status)">{{ reviewLabel(it.review_status) }}</span>
              <span class="px-2.5 py-1 rounded-lg text-[11px] font-semibold shrink-0" :class="itemStatusChip(it.status)">{{ itemStatusLabel(it.status) }}</span>
              <div class="flex gap-1.5 shrink-0">
                <button v-if="it.status === 'available'" type="button" @click="editItem = it"
                        class="h-8 px-2.5 rounded-lg border border-line text-xs text-muted hover:text-ink hover:bg-canvas transition-colors inline-flex items-center gap-1">
                  <Icon name="edit" :size="13" />编辑
                </button>
                <button v-if="it.status === 'available'" type="button" @click="askOffshelf(it)"
                        class="h-8 px-2.5 rounded-lg border border-line text-xs text-muted hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors inline-flex items-center gap-1">
                  <Icon name="archive" :size="13" />下架
                </button>
              </div>
            </li>
          </ul>
        </div>

        <!-- 我的收藏 -->
        <div v-show="tab === 'fav'" class="p-5">
          <p v-if="favorites.length === 0" class="py-14 text-center text-sm text-muted">还没有收藏任何物品</p>
          <ul v-else class="divide-y divide-line">
            <li v-for="f in favorites" :key="f.id" class="py-3 flex flex-wrap items-center gap-3">
              <RouterLink :to="`/items/${f.item_id}`" class="w-12 h-12 shrink-0">
                <ItemImage :item="{ image: f.image, category: f.category, title: f.item_title }" ratio="aspect-square" />
              </RouterLink>
              <div class="min-w-0 flex-1">
                <RouterLink :to="`/items/${f.item_id}`" class="text-sm font-semibold text-ink hover:text-brand-700 dark:hover:text-brand-400 truncate block">{{ f.item_title }}</RouterLink>
                <p class="mt-0.5 text-[11px] text-subtle tnum">¥{{ f.price.toFixed(2) }} · {{ f.owner_name }} · 收藏于 {{ f.created_at }}</p>
              </div>
              <span class="px-2.5 py-1 rounded-lg text-[11px] font-semibold shrink-0" :class="itemStatusChip(f.status)">{{ itemStatusLabel(f.status) }}</span>
              <button type="button" @click="removeFavorite(f)"
                      class="h-8 px-2.5 rounded-lg border border-line text-xs text-muted hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors shrink-0">取消收藏</button>
            </li>
          </ul>
        </div>

        <!-- 我的举报 -->
        <div v-show="tab === 'reports'" class="p-5">
          <p v-if="myReports.length === 0" class="py-14 text-center text-sm text-muted">
            还没有提交过举报
            <span class="block mt-1 text-xs text-subtle">在物品详情页可举报描述失实或违规的物品</span>
          </p>
          <ul v-else class="space-y-3">
            <li v-for="r in myReports" :key="r.id" class="p-4 rounded-xl border"
                :class="r.status === 'open' ? 'border-amber-200 dark:border-amber-500/30 bg-amber-50/40 dark:bg-amber-400/5' : 'border-line bg-canvas/50'">
              <div class="flex items-start justify-between gap-2">
                <RouterLink :to="`/items/${r.item_id}`" class="text-sm font-semibold text-ink hover:text-brand-700 dark:hover:text-brand-400">{{ r.item_title }}</RouterLink>
                <span class="px-2 py-0.5 rounded-lg text-[11px] font-semibold shrink-0"
                      :class="r.status === 'open' ? 'bg-amber-100 dark:bg-amber-400/15 text-amber-700 dark:text-amber-300' : 'bg-brand-100 dark:bg-brand-400/15 text-brand-700 dark:text-brand-300'">
                  {{ r.status === 'open' ? '处理中' : '已处理' }}
                </span>
              </div>
              <p class="mt-1.5 text-[13px] text-muted">“{{ r.reason }}”</p>
              <p class="mt-1 text-[11px] text-subtle">提交于 {{ r.created_at }}</p>
            </li>
          </ul>
        </div>
      </div>
    </template>

    <FulfillDialog v-if="completing" :order="completing" @close="completing = null" @saved="completing = null; loadAll(); auth.refresh()" />
    <PublishDialog v-if="editItem" :item="editItem" @close="editItem = null" @saved="editItem = null; loadAll()" />
  </div>
</template>
