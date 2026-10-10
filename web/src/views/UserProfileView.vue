<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import Icon from '@/components/Icon.vue'
import Avatar from '@/components/Avatar.vue'
import ItemCard from '@/components/ItemCard.vue'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()

const profile = ref(null)
const loading = ref(true)
const notFound = ref(false)

const stats = () => {
  const s = profile.value?.stats || {}
  return [
    { label: '累计减碳（kg）', value: (s.carbon_kg ?? 0).toFixed(1) },
    { label: '循环流转（次）', value: s.cycles ?? 0 },
    { label: '发布物品（件）', value: s.published ?? 0 },
    { label: '在售物品（件）', value: s.on_sale ?? 0 },
  ]
}

async function load() {
  loading.value = true
  notFound.value = false
  try {
    profile.value = await api.get(`/api/users/${route.params.id}/profile`)
  } catch (e) {
    if (e.status === 404) notFound.value = true
    else ui.toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div class="animate-rise">
    <div v-if="loading" class="space-y-4">
      <div class="skel h-40 rounded-xl2"></div>
      <div class="skel h-56 rounded-xl2"></div>
    </div>

    <div v-else-if="notFound" class="grid place-items-center py-24 rounded-xl2 bg-surface border border-dashed border-line">
      <span class="grid place-items-center w-16 h-16 rounded-2xl bg-canvas text-subtle"><Icon name="user" :size="28" /></span>
      <p class="mt-4 font-semibold text-ink">用户不存在</p>
    </div>

    <template v-else-if="profile">
      <div class="p-6 rounded-xl2 bg-surface border border-line shadow-card">
        <div class="flex flex-wrap items-center gap-5">
          <Avatar :user="profile" :size="72" rounded="rounded-2xl" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <h1 class="text-xl font-bold text-ink">{{ profile.name }}</h1>
              <span v-if="profile.role === 'admin'" class="px-2 py-0.5 rounded-md bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-300 text-[11px] font-semibold">平台管理员</span>
            </div>
            <p class="mt-1 text-sm text-muted">{{ profile.college }}</p>
            <p v-if="profile.bio" class="mt-2 text-[13px] text-muted">{{ profile.bio }}</p>
            <p class="mt-1.5 text-[11px] text-subtle">加入于 {{ profile.created_at }} · 碳积分 {{ profile.points }}</p>
          </div>
        </div>
        <div class="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div v-for="s in stats()" :key="s.label" class="p-3 rounded-xl bg-canvas border border-line">
            <p class="text-lg font-bold text-ink tnum">{{ s.value }}</p>
            <p class="text-[11px] text-subtle">{{ s.label }}</p>
          </div>
        </div>
      </div>

      <div class="mt-4">
        <h2 class="font-semibold text-ink mb-3 inline-flex items-center gap-2">
          <Icon name="store" :size="17" class="text-brand-600" />TA 的在售物品
        </h2>
        <div v-if="profile.items.length === 0" class="grid place-items-center py-16 rounded-xl2 bg-surface border border-dashed border-line text-sm text-muted">
          暂无在售物品
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <ItemCard v-for="it in profile.items" :key="it.id" :item="it" :me="auth.user" :favorited="false" />
        </div>
      </div>
    </template>
  </div>
</template>
