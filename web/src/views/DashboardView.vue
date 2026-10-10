<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import Icon from '@/components/Icon.vue'
import Avatar from '@/components/Avatar.vue'
import { api } from '@/lib/api'
import { useUiStore } from '@/stores/ui'
import { catBar, catFg, catIcon } from '@/lib/format'

const ui = useUiStore()
const summary = ref({})
const userRank = ref([])
const collegeRank = ref([])
const trend = ref([])
const byCategory = ref([])
const loading = ref(true)

const trendW = 700, trendH = 176, trendPad = 8
const trendStep = computed(() => trendW / Math.max(trend.value.length, 1))
const trendBarW = computed(() => Math.min(56, Math.max(6, trendStep.value * 0.5)))
const trendBarX = (i) => i * trendStep.value + trendPad + (trendStep.value - trendPad * 2 - trendBarW.value) / 2
const trendMax = computed(() => Math.max(1, ...trend.value.map(d => d.cycles)))
const trendBarH = (v) => v === 0 ? 2 : Math.round((v / trendMax.value) * (trendH - 44))
const trendBarY = (v) => trendH - 20 - trendBarH(v)
const trendGrid = computed(() => {
  const m = trendMax.value
  const step = m <= 4 ? 1 : Math.ceil(m / 4)
  const out = []
  for (let v = 0; v <= m; v += step) out.push({ v, y: trendH - 20 - Math.round((v / m) * (trendH - 44)) })
  return out
})
const catPercent = (c) => Math.round(c.cnt / Math.max(1, ...byCategory.value.map(x => x.cnt)) * 100)

const kpis = computed(() => [
  { label: '累计减碳（kg CO₂e）', value: summary.value.total_carbon_kg ?? 0, icon: 'leaf', bg: 'bg-brand-50 dark:bg-brand-500/10', fg: 'text-brand-600' },
  { label: '累计循环流转（次）', value: summary.value.total_cycles ?? 0, icon: 'recycle', bg: 'bg-blue-50 dark:bg-blue-500/10', fg: 'text-blue-600' },
  { label: '上线闲置物品（件）', value: summary.value.total_published ?? 0, icon: 'box', bg: 'bg-violet-50 dark:bg-violet-500/10', fg: 'text-violet-600' },
  { label: '参与师生（人）', value: summary.value.total_users ?? 0, icon: 'user', bg: 'bg-amber-50 dark:bg-amber-500/10', fg: 'text-amber-600' },
  { label: '相当于植树（棵/年）', value: summary.value.trees_equivalent ?? 0, icon: 'tree', bg: 'bg-emerald-50 dark:bg-emerald-500/10', fg: 'text-emerald-600' },
])

async function load() {
  loading.value = true
  try {
    const [s, ur, cr, tr] = await Promise.all([
      api.get('/api/stats/summary'), api.get('/api/rank/users'),
      api.get('/api/rank/colleges'), api.get('/api/stats/trends'),
    ])
    summary.value = s; userRank.value = ur; collegeRank.value = cr
    trend.value = tr.trend; byCategory.value = tr.by_category
  } catch (e) {
    ui.toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="animate-rise">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-xl font-bold text-ink">绿色循环大屏</h1>
        <p class="mt-1 text-sm text-muted">全校环保数据实时看板 · 数据来源为平台实时聚合</p>
      </div>
      <button type="button" @click="load"
              class="h-10 px-4 rounded-xl bg-surface border border-line text-sm font-medium text-ink hover:bg-canvas transition-colors inline-flex items-center gap-2">
        <Icon name="refresh" :size="16" /> 刷新
      </button>
    </div>

    <div class="mt-5 grid grid-cols-2 lg:grid-cols-5 gap-3">
      <div v-for="k in kpis" :key="k.label" class="p-4 rounded-xl2 bg-surface border border-line shadow-card">
        <span class="grid place-items-center w-9 h-9 rounded-xl" :class="k.bg"><Icon :name="k.icon" :size="18" :class="k.fg" /></span>
        <p class="mt-3 text-2xl font-bold text-ink tnum leading-none">{{ k.value }}</p>
        <p class="mt-1.5 text-[11px] text-muted">{{ k.label }}</p>
      </div>
    </div>

    <div class="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 p-5 rounded-xl2 bg-surface border border-line shadow-card">
        <div class="flex items-center justify-between">
          <h2 class="font-semibold text-ink inline-flex items-center gap-2"><Icon name="chart" :size="17" class="text-brand-600" />近 14 日流转趋势</h2>
          <span class="text-[11px] text-subtle">完成流转次数 / 日</span>
        </div>
        <div v-if="trend.length === 0" class="py-16 text-center text-sm text-subtle">暂无流转记录，完成一次流转后即可看到趋势</div>
        <div v-else class="mt-4">
          <svg :viewBox="`0 0 ${trendW} ${trendH}`" class="w-full h-44" role="img" aria-label="近 14 日流转趋势柱状图">
            <defs><linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#34d399" /><stop offset="1" stop-color="#059669" /></linearGradient></defs>
            <g v-for="(g, i) in trendGrid" :key="'g' + i">
              <line :x1="0" :y1="g.y" :x2="trendW" :y2="g.y" stroke="var(--c-border)" stroke-width="1" stroke-dasharray="4 4" />
              <text :x="0" :y="g.y - 4" fill="var(--c-subtle)" font-size="10">{{ g.v }}</text>
            </g>
            <g v-for="(d, i) in trend" :key="d.d">
              <rect :x="trendBarX(i)" :y="trendBarY(d.cycles)" :width="trendBarW" :height="trendBarH(d.cycles)" rx="4" fill="url(#barGrad)">
                <title>{{ d.d }}：{{ d.cycles }} 次流转 / {{ d.carbon }} kg</title>
              </rect>
              <text :x="trendBarX(i) + trendBarW / 2" :y="trendH - 4" text-anchor="middle" fill="var(--c-subtle)" font-size="9">{{ d.d.slice(5) }}</text>
            </g>
          </svg>
        </div>
      </div>

      <div class="p-5 rounded-xl2 bg-surface border border-line shadow-card">
        <h2 class="font-semibold text-ink inline-flex items-center gap-2"><Icon name="pie" :size="17" class="text-brand-600" />物品类别分布</h2>
        <div class="mt-4 space-y-4">
          <div v-for="c in byCategory" :key="c.category">
            <div class="flex items-center justify-between text-[13px] mb-1.5">
              <span class="inline-flex items-center gap-1.5 text-ink"><Icon :name="catIcon(c.category)" :size="14" :class="catFg(c.category)" />{{ c.category }}</span>
              <span class="text-muted tnum">{{ c.cnt }} 件 · {{ c.carbon.toFixed(1) }} kg</span>
            </div>
            <div class="h-2.5 rounded-full bg-canvas overflow-hidden">
              <div class="h-full rounded-full transition-all duration-700" :class="catBar(c.category)" :style="{ width: catPercent(c) + '%' }"></div>
            </div>
          </div>
          <p v-if="byCategory.length === 0" class="py-10 text-center text-sm text-subtle">暂无数据</p>
        </div>
      </div>
    </div>

    <div class="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="p-5 rounded-xl2 bg-surface border border-line shadow-card">
        <h2 class="font-semibold text-ink inline-flex items-center gap-2"><Icon name="trophy" :size="17" class="text-amber-500" />全校环保先锋榜</h2>
        <ol class="mt-4 space-y-1.5">
          <li v-for="(u, i) in userRank" :key="u.id" class="flex items-center gap-3 p-2.5 rounded-xl hover:bg-canvas transition-colors">
            <span class="grid place-items-center w-8 h-8 rounded-xl text-sm font-bold shrink-0"
                  :class="i === 0 ? 'bg-amber-400 text-white' : i === 1 ? 'bg-slate-300 text-white' : i === 2 ? 'bg-orange-400 text-white' : 'bg-canvas text-muted border border-line'">
              <span class="tnum">{{ i + 1 }}</span>
            </span>
            <RouterLink :to="`/u/${u.id}`" class="min-w-0 flex-1 flex items-center gap-2.5">
              <Avatar :user="u" :size="36" />
              <span class="min-w-0">
                <span class="block text-sm font-semibold text-ink truncate">{{ u.name }}</span>
                <span class="block text-[11px] text-subtle">循环 {{ u.cycles }} 次 · {{ u.points }} 积分 · {{ u.college }}</span>
              </span>
            </RouterLink>
            <span class="shrink-0 text-right">
              <span class="block text-sm font-bold text-brand-700 dark:text-brand-400 tnum">{{ u.carbon_kg.toFixed(1) }}</span>
              <span class="block text-[10px] text-subtle">kg CO₂e</span>
            </span>
          </li>
          <li v-if="userRank.length === 0" class="py-10 text-center text-sm text-subtle">暂无排行数据</li>
        </ol>
      </div>

      <div class="p-5 rounded-xl2 bg-surface border border-line shadow-card">
        <h2 class="font-semibold text-ink inline-flex items-center gap-2"><Icon name="building" :size="17" class="text-brand-600" />学院减碳排行</h2>
        <ul class="mt-4 space-y-4">
          <li v-for="(c, i) in collegeRank" :key="c.college">
            <div class="flex items-center justify-between text-[13px] mb-1.5">
              <span class="font-medium text-ink"><span class="text-subtle tnum mr-1.5">{{ i + 1 }}</span>{{ c.college }}</span>
              <span class="text-brand-700 dark:text-brand-400 font-bold tnum">{{ c.carbon_kg.toFixed(1) }} kg</span>
            </div>
            <div class="h-2.5 rounded-full bg-canvas overflow-hidden">
              <div class="h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600 transition-all duration-700" :style="{ width: c.percent + '%' }"></div>
            </div>
            <p class="mt-1 text-[11px] text-subtle">{{ c.members }} 名成员 · {{ c.cycles }} 次流转</p>
          </li>
          <li v-if="collegeRank.length === 0" class="py-10 text-center text-sm text-subtle">暂无排行数据</li>
        </ul>
      </div>
    </div>
  </div>
</template>
