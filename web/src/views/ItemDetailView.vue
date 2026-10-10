<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import Icon from '@/components/Icon.vue'
import ItemImage from '@/components/ItemImage.vue'
import Avatar from '@/components/Avatar.vue'
import PublishDialog from '@/components/PublishDialog.vue'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useCategoryStore } from '@/stores/category'
import { catChip, itemStatusChip, itemStatusLabel, reviewChip, reviewLabel } from '@/lib/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()
const categories = useCategoryStore()

const item = ref(null)
const loading = ref(true)
const notFound = ref(false)
const busy = ref(false)
const showEdit = ref(false)
const showReport = ref(false)
const reportReason = ref('')
const reportErr = ref('')
const reporting = ref(false)

const isOwner = computed(() => auth.user && item.value && item.value.owner_id === auth.user.id)
const canReserve = computed(() => auth.isLoggedIn && item.value && !isOwner.value && item.value.status === 'available')
const isPending = computed(() => item.value && item.value.review_status !== 'approved')
const carbonFactor = computed(() => categories.factorOf(item.value?.category))

async function load() {
  loading.value = true
  notFound.value = false
  try {
    item.value = await api.get(`/api/items/${route.params.id}`)
  } catch (e) {
    if (e.status === 404) notFound.value = true
    else ui.toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function reserve() {
  if (!auth.isLoggedIn) { router.push({ name: 'login', query: { redirect: route.fullPath } }); return }
  busy.value = true
  try {
    const o = await api.post('/api/orders', { item_id: item.value.id })
    ui.toast(`预约成功！自提码 ${o.pickup_code}，请线下联系卖家验货`)
    await auth.refresh()
    router.push({ name: 'me', query: { tab: 'buy' } })
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

async function toggleFavorite() {
  if (!auth.isLoggedIn) { router.push({ name: 'login', query: { redirect: route.fullPath } }); return }
  busy.value = true
  try {
    if (item.value.favorited) {
      await api.del(`/api/favorites/${item.value.id}`)
      item.value.favorited = false
      item.value.favorite_count--
      ui.toast('已取消收藏')
    } else {
      await api.post('/api/favorites', { item_id: item.value.id })
      item.value.favorited = true
      item.value.favorite_count++
      ui.toast('已加入收藏')
    }
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    busy.value = false
  }
}

async function submitReport() {
  if (reportReason.value.length < 2) { reportErr.value = '举报理由至少 2 个字'; return }
  reporting.value = true
  try {
    await api.post('/api/reports', { item_id: item.value.id, reason: reportReason.value })
    ui.toast('举报已提交，管理员将尽快核实')
    showReport.value = false
    reportReason.value = ''
  } catch (e) {
    reportErr.value = e.message
  } finally {
    reporting.value = false
  }
}

async function askOffshelf() {
  if (await ui.ask({ title: '下架物品', text: `确定下架《${item.value.title}》吗？下架后市集不再展示，历史与统计会保留。`, ok: '确认下架', danger: true })) {
    try {
      await api.del(`/api/items/${item.value.id}`)
      ui.toast('物品已下架')
      router.push({ name: 'me', query: { tab: 'items' } })
    } catch (e) {
      ui.toast(e.message, 'error')
    }
  }
}

onMounted(() => { categories.load(); load() })
</script>

<template>
  <div class="animate-rise">
    <RouterLink :to="{ name: 'market' }" class="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink transition-colors">
      <Icon name="arrowleft" :size="16" /> 返回市集
    </RouterLink>

    <div v-if="loading" class="mt-5 grid lg:grid-cols-2 gap-6">
      <div class="skel aspect-[4/3] rounded-xl2"></div>
      <div class="space-y-3"><div class="skel h-7 w-2/3"></div><div class="skel h-4 w-full"></div><div class="skel h-24 w-full"></div></div>
    </div>

    <div v-else-if="notFound" class="mt-8 grid place-items-center py-24 rounded-xl2 bg-surface border border-dashed border-line">
      <span class="grid place-items-center w-16 h-16 rounded-2xl bg-canvas text-subtle"><Icon name="box" :size="28" /></span>
      <p class="mt-4 font-semibold text-ink">物品不存在或已被移除</p>
      <RouterLink :to="{ name: 'market' }" class="mt-3 text-sm text-brand-600 hover:underline">去市集看看 →</RouterLink>
    </div>

    <div v-else-if="item" class="mt-5 grid lg:grid-cols-2 gap-6">
      <!-- 图片 -->
      <div>
        <ItemImage :item="item" ratio="aspect-[4/3]" />
        <div class="mt-3 grid grid-cols-3 gap-3">
          <div class="p-3 rounded-xl bg-surface border border-line">
            <p class="text-[11px] text-subtle">循环度</p>
            <p class="mt-0.5 text-lg font-bold text-ink tnum">{{ item.cycle_count }} 次</p>
          </div>
          <div class="p-3 rounded-xl bg-surface border border-line">
            <p class="text-[11px] text-subtle">累计减碳</p>
            <p class="mt-0.5 text-lg font-bold text-ink tnum">{{ item.carbon_saved.toFixed(1) }} kg</p>
          </div>
          <div class="p-3 rounded-xl bg-surface border border-line">
            <p class="text-[11px] text-subtle">单次减碳</p>
            <p class="mt-0.5 text-lg font-bold text-ink tnum">{{ carbonFactor }} kg</p>
          </div>
        </div>
      </div>

      <!-- 信息 -->
      <div>
        <div class="flex flex-wrap items-center gap-2">
          <span class="px-2 py-0.5 rounded-md text-[11px] font-medium border inline-flex items-center gap-1" :class="catChip(item.category)">
            <Icon :name="categories.iconOf(item.category)" :size="12" />{{ item.category }}
          </span>
          <span class="px-2.5 py-0.5 rounded-lg text-[11px] font-semibold" :class="itemStatusChip(item.status)">{{ itemStatusLabel(item.status) }}</span>
          <span v-if="isPending" class="px-2.5 py-0.5 rounded-lg text-[11px] font-semibold" :class="reviewChip(item.review_status)">{{ reviewLabel(item.review_status) }}</span>
          <span class="inline-flex items-center gap-1 text-[11px] text-subtle"><Icon name="heart" :size="12" />{{ item.favorite_count }} 人收藏</span>
        </div>

        <!-- 待审核/已驳回提示：仅物主与管理员可见该物品 -->
        <div v-if="isPending" class="mt-3 p-3.5 rounded-xl flex items-start gap-2.5 text-[13px]"
             :class="item.review_status === 'rejected' ? 'bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-300' : 'bg-amber-50 dark:bg-amber-400/10 text-amber-700 dark:text-amber-300'">
          <Icon name="info" :size="17" class="mt-px shrink-0" />
          <span>
            <template v-if="item.review_status === 'rejected'">
              该物品审核未通过，暂不对外展示。<template v-if="item.review_note">驳回理由：{{ item.review_note }}。</template>
              修改后可重新提交审核。
            </template>
            <template v-else>该物品正在审核中，通过后将在市集展示。</template>
          </span>
        </div>

        <h1 class="mt-3 text-2xl font-bold text-ink leading-snug">{{ item.title }}</h1>
        <p class="mt-2 text-3xl font-bold text-brand-700 dark:text-brand-400 tnum">¥{{ item.price.toFixed(2) }}</p>

        <p class="mt-4 text-[14px] text-muted leading-relaxed whitespace-pre-wrap">{{ item.description || '发布者未填写描述' }}</p>

        <RouterLink :to="`/u/${item.owner_id}`"
                    class="mt-5 p-3.5 rounded-xl bg-surface border border-line flex items-center gap-3 hover:border-brand-300 dark:hover:border-brand-500/40 transition-colors">
          <Avatar :name="item.owner_name" :user="{ name: item.owner_name, avatar: item.owner_avatar }" :size="40" />
          <span class="min-w-0 flex-1">
            <span class="block text-sm font-semibold text-ink">{{ item.owner_name }}</span>
            <span class="block text-[11px] text-subtle">{{ item.owner_college }} · 发布于 {{ item.created_at }}</span>
          </span>
          <Icon name="chevron" :size="16" class="text-subtle -rotate-90" />
        </RouterLink>

        <div class="mt-5 flex flex-wrap gap-2">
          <button v-if="canReserve" type="button" @click="reserve" :disabled="busy"
                  class="flex-1 min-w-[150px] h-11 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50 inline-flex items-center justify-center gap-2 transition-colors">
            <Icon name="handshake" :size="17" /> 发起预约意向
          </button>
          <button v-if="auth.isLoggedIn" type="button" @click="toggleFavorite" :disabled="busy"
                  class="h-11 px-4 rounded-xl border text-sm font-semibold inline-flex items-center justify-center gap-2 transition-colors"
                  :class="item.favorited ? 'border-rose-300 text-rose-500 bg-rose-50 dark:bg-rose-500/10' : 'border-line text-muted hover:text-ink hover:bg-canvas'">
            <Icon :name="item.favorited ? 'heartfill' : 'heart'" :size="17" />{{ item.favorited ? '已收藏' : '收藏' }}
          </button>

          <template v-if="isOwner">
            <button type="button" @click="showEdit = true"
                    class="h-11 px-4 rounded-xl border border-line text-sm font-medium text-ink hover:bg-canvas inline-flex items-center gap-2 transition-colors">
              <Icon name="edit" :size="16" /> 编辑
            </button>
            <button v-if="item.status !== 'offshelf' && item.status !== 'completed'" type="button" @click="askOffshelf"
                    class="h-11 px-4 rounded-xl border border-line text-sm font-medium text-muted hover:text-rose-600 hover:border-rose-300 hover:bg-rose-50 dark:hover:bg-rose-500/10 inline-flex items-center gap-2 transition-colors">
              <Icon name="archive" :size="16" /> 下架
            </button>
          </template>

          <button v-if="auth.isLoggedIn && !isOwner" type="button" @click="showReport = true"
                  class="h-11 px-4 rounded-xl border border-line text-sm font-medium text-muted hover:text-red-600 hover:border-red-300 hover:bg-red-50 dark:hover:bg-red-500/10 inline-flex items-center gap-2 transition-colors">
            <Icon name="flag" :size="16" /> 举报
          </button>
        </div>

        <p v-if="!auth.isLoggedIn" class="mt-3 text-[12px] text-subtle">
          <RouterLink :to="{ name: 'login', query: { redirect: route.fullPath } }" class="text-brand-600 hover:underline">登录</RouterLink>
          后即可预约或收藏该物品
        </p>
        <p v-else-if="isOwner" class="mt-3 text-[12px] text-subtle">这是你发布的物品</p>
      </div>
    </div>

    <PublishDialog v-if="showEdit && item" :item="item" @close="showEdit = false" @saved="showEdit = false; load()" />

    <!-- 举报弹窗 -->
    <transition name="fade">
      <div v-if="showReport" class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
           @click.self="showReport = false">
        <transition name="sheet" appear>
          <div class="w-full sm:max-w-md bg-elevated rounded-t-2xl sm:rounded-2xl shadow-lift" role="dialog" aria-modal="true" aria-label="举报违规物品">
            <div class="flex items-center justify-between px-5 py-4 border-b border-line">
              <h3 class="font-semibold text-ink">举报违规物品</h3>
              <button type="button" @click="showReport = false" aria-label="关闭"
                      class="grid place-items-center w-8 h-8 rounded-lg text-muted hover:text-ink hover:bg-canvas transition-colors"><Icon name="close" :size="18" /></button>
            </div>
            <div class="p-5">
              <p class="text-sm text-muted">举报对象：<b class="text-ink">{{ item.title }}</b></p>
              <label for="report-reason" class="block text-[13px] font-medium text-ink mt-4 mb-1.5">举报理由（2–200 字）</label>
              <textarea id="report-reason" v-model.trim="reportReason" rows="3" maxlength="200"
                        placeholder="请描述违规情况，例如：描述与实物不符、疑似违禁品…"
                        class="w-full px-3.5 py-2.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/40"></textarea>
              <p class="mt-1 text-right text-[11px] text-subtle tnum">{{ reportReason.length }}/200</p>
              <p v-if="reportErr" class="mt-1 text-[12px] text-rose-500">{{ reportErr }}</p>
            </div>
            <div class="flex justify-end gap-2 px-5 py-4 border-t border-line">
              <button type="button" @click="showReport = false"
                      class="h-10 px-4 rounded-xl text-sm font-medium text-muted hover:bg-canvas transition-colors">取消</button>
              <button type="button" @click="submitReport" :disabled="reporting"
                      class="h-10 px-5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-sm font-semibold disabled:opacity-50 transition-colors">
                {{ reporting ? '提交中…' : '提交举报' }}
              </button>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </div>
</template>
