<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { inStock } from '@/lib/format'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

const products = ref([])
const loading = ref(true)
const busyId = ref(null)

async function load() {
  loading.value = true
  try { products.value = await api.get('/api/products') }
  catch (e) { ui.toast(e.message, 'error') }
  finally { loading.value = false }
}

const canRedeem = (p) => auth.isLoggedIn && inStock(p) && (auth.user?.points ?? 0) >= p.cost_points
function redeemLabel(p) {
  if (!inStock(p)) return '已兑完'
  if (!auth.isLoggedIn) return '登录后兑换'
  if ((auth.user?.points ?? 0) < p.cost_points) return '积分不足'
  return '兑换'
}

async function redeem(p) {
  if (!auth.isLoggedIn) { router.push({ name: 'login', query: { redirect: '/mall' } }); return }
  if (!(await ui.ask({ title: '兑换礼品', text: `确定使用 ${p.cost_points} 碳积分兑换「${p.name}」吗？`, ok: '确认兑换' }))) return
  busyId.value = p.id
  try {
    const r = await api.post('/api/redeem', { product_id: p.id })
    ui.toast(r.message)
    await auth.refresh()
    await load()
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="animate-rise">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-ink">碳积分商城</h1>
        <p class="mt-1 text-sm text-muted">用循环闲置赚来的碳积分，兑换校园绿色好礼</p>
      </div>
      <div class="flex items-center gap-2 px-4 py-2.5 rounded-xl2 bg-gradient-to-br from-amber-400 to-amber-600 text-white shadow-card">
        <Icon name="coin" :size="20" />
        <span class="leading-tight">
          <span class="block text-[11px] opacity-85">我的碳积分</span>
          <span class="block text-xl font-bold tnum">{{ auth.isLoggedIn ? auth.user.points : '—' }}</span>
        </span>
      </div>
    </div>

    <div v-if="loading" class="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="n in 5" :key="n" class="p-5 rounded-xl2 bg-surface border border-line">
        <div class="skel w-14 h-14"></div><div class="skel h-4 mt-3.5 w-2/3"></div><div class="skel h-3 mt-2 w-full"></div>
      </div>
    </div>

    <div v-else class="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <article v-for="p in products" :key="p.id"
               class="flex flex-col p-5 rounded-xl2 bg-surface border border-line shadow-card hover:shadow-lift transition-shadow">
        <div class="flex items-start justify-between">
          <span class="grid place-items-center w-14 h-14 rounded-2xl bg-canvas border border-line text-3xl select-none" aria-hidden="true">{{ p.emoji }}</span>
          <span class="px-2 py-0.5 rounded-full text-[11px] font-medium border"
                :class="inStock(p) ? 'bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300 border-brand-200/70 dark:border-brand-500/20' : 'bg-canvas text-subtle border-line'">
            库存 {{ p.stock }}
          </span>
        </div>
        <h3 class="mt-3.5 font-semibold text-ink">{{ p.name }}</h3>
        <p class="mt-1 text-[13px] text-muted flex-1">{{ p.description }}</p>
        <div class="mt-4 flex items-center justify-between gap-2">
          <span class="inline-flex items-center gap-1.5 font-bold text-amber-600 dark:text-amber-400">
            <Icon name="coin" :size="17" /><span class="tnum">{{ p.cost_points }}</span>
            <span class="text-[11px] font-medium opacity-70">积分</span>
          </span>
          <button type="button" @click="redeem(p)" :disabled="!inStock(p) || (auth.isLoggedIn && !canRedeem(p)) || busyId !== null"
                  class="h-9 px-4 rounded-xl text-[13px] font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                  :class="canRedeem(p) ? 'bg-amber-500 hover:bg-amber-600 text-white' : 'bg-canvas text-subtle border border-line'">
            <Icon name="gift" :size="15" /> {{ redeemLabel(p) }}
          </button>
        </div>
      </article>
    </div>

    <p v-if="!auth.isLoggedIn" class="mt-5 p-3.5 rounded-xl2 bg-surface border border-line text-[13px] text-muted inline-flex items-center gap-2">
      <Icon name="info" :size="16" class="text-brand-600" />
      <span><RouterLink :to="{ name: 'login' }" class="text-brand-600 hover:underline">登录</RouterLink> 后即可用碳积分兑换礼品</span>
    </p>
  </div>
</template>
