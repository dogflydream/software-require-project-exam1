<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import Icon from './Icon.vue'
import { useMessagesStore } from '@/stores/messages'
import Avatar from './Avatar.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const auth = useAuthStore()
const ui = useUiStore()
const route = useRoute()
const router = useRouter()
const messages = useMessagesStore()
let messageTimer
async function refreshUnread() {
  if (auth.isLoggedIn && !document.hidden) { try { await messages.load() } catch { /* retry on next poll */ } }
}
watch(() => auth.user?.id, () => { messages.reset(); refreshUnread() }, { immediate: true })
onMounted(() => { messageTimer = setInterval(refreshUnread, 15000) })
onUnmounted(() => clearInterval(messageTimer))
const menuOpen = ref(false)
const menuEl = ref(null)
watch(() => route.fullPath, () => { menuOpen.value = false })
const activeTab = computed(() => ['profile-edit', 'user'].includes(route.name) ? 'me' : route.name === 'item' ? 'market' : route.name)

const tabs = computed(() => {
  const t = [
    { name: 'market', label: '市集', icon: 'cart' },
    { name: 'mall', label: '积分商城', icon: 'gift' },
    { name: 'dashboard', label: '绿色大屏', icon: 'chart' },
    { name: 'messages', label: '站内消息', icon: 'message' },
    { name: 'me', label: '个人中心', icon: 'user' },
  ]
  if (auth.isAdmin) t.push({ name: 'admin', label: '后台管理', icon: 'shield' })
  return t
})

async function doLogout() {
  menuOpen.value = false
  if (await ui.ask({ title: '退出登录', text: '确定要退出当前账号吗？', ok: '退出', danger: true })) {
    await auth.logout()
    ui.toast('已退出登录')
    router.push({ name: 'login' })
  }
}
function closeMenu(e) {
  if (menuEl.value && !menuEl.value.contains(e.target)) menuOpen.value = false
}
</script>

<template>
  <div class="min-h-screen flex flex-col" @keydown.esc="menuOpen = false" @click="closeMenu">
    <a href="#main-content" class="skip-link">跳转到主要内容</a>
    <header class="sticky top-0 z-40 bg-surface/85 backdrop-blur-xl border-b border-line">
      <div class="mx-auto max-w-7xl px-4">
        <div class="h-16 flex items-center gap-3">
          <RouterLink :to="{ name: 'market' }" class="flex items-center gap-2.5 shrink-0" aria-label="绿循校园首页">
            <span class="grid place-items-center w-9 h-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 text-white shadow-card">
              <Icon name="leaf" :size="20" />
            </span>
            <span class="block leading-tight">
              <span class="block font-bold text-[15px] tracking-tight text-ink">绿循校园</span>
              <span class="hidden sm:block text-[11px] text-subtle">闲置循环 · 碳积分 · 绿色校园</span>
            </span>
          </RouterLink>

          <nav class="hidden sm:block flex-1 min-w-0 overflow-x-auto no-bar" aria-label="主导航">
            <div class="flex items-center gap-1">
              <RouterLink v-for="t in tabs" :key="t.name" :to="{ name: t.name }"
                          class="group flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors"
                          :class="activeTab === t.name ? 'bg-brand-50 dark:bg-brand-500/15 text-brand-700 dark:text-brand-300' : 'text-muted hover:text-ink hover:bg-canvas'"
                          :aria-current="activeTab === t.name ? 'page' : undefined">
                <Icon :name="t.icon" :size="18" />
                <span class="hidden md:inline">{{ t.label }}</span><span v-if="t.name === 'messages' && messages.unreadCount" class="rounded-full bg-rose-600 text-white px-1.5 text-[10px]" :aria-label="`${messages.unreadCount} 条未读消息`">{{ messages.unreadCount > 99 ? '99+' : messages.unreadCount }}</span>
              </RouterLink>
            </div>
          </nav>

          <div class="ml-auto flex items-center gap-2 shrink-0">
            <button type="button" @click="ui.toggleTheme()"
                    class="grid place-items-center w-9 h-9 rounded-xl border border-line text-muted hover:text-ink hover:bg-canvas transition-colors"
                    :aria-label="ui.theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'">
              <Icon :name="ui.theme === 'dark' ? 'sun' : 'moon'" :size="18" />
            </button>

            <div v-if="auth.isLoggedIn" class="hidden sm:flex items-center gap-1.5 h-9 pl-1.5 pr-3 rounded-xl bg-amber-50 dark:bg-amber-400/10 border border-amber-200/70 dark:border-amber-400/20">
              <Icon name="coin" :size="16" class="text-amber-500" />
              <span class="text-sm font-bold text-amber-700 dark:text-amber-300 tnum">{{ auth.user.points }}</span>
            </div>

            <!-- 已登录：账号菜单 -->
            <div v-if="auth.isLoggedIn" class="relative" ref="menuEl">
              <button type="button" @click.stop="menuOpen = !menuOpen"
                      class="flex items-center gap-2 h-9 pl-1 pr-2.5 rounded-xl border border-line hover:bg-canvas transition-colors"
                      aria-label="账号菜单" aria-haspopup="menu" :aria-expanded="menuOpen ? 'true' : 'false'">
                <Avatar :user="auth.user" :size="28" rounded="rounded-lg" />
                <span class="hidden sm:block max-w-[92px] truncate text-sm text-ink">{{ auth.user.name }}</span>
                <Icon name="chevron" :size="14" class="text-subtle" />
              </button>
              <transition name="fade">
                <div v-if="menuOpen" class="absolute right-0 mt-2 w-60 p-1.5 rounded-2xl bg-elevated border border-line shadow-lift z-50" role="menu">
                  <div class="flex items-center gap-2.5 px-2.5 py-2">
                    <Avatar :user="auth.user" :size="36" />
                    <span class="min-w-0">
                      <span class="flex items-center gap-1.5">
                        <span class="text-sm font-semibold text-ink truncate">{{ auth.user.name }}</span>
                        <span v-if="auth.isAdmin" class="px-1.5 py-px rounded-md bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-300 text-[10px] font-semibold">管理员</span>
                      </span>
                      <span class="block text-[11px] text-subtle truncate">{{ auth.user.college }}</span>
                    </span>
                  </div>
                  <div class="my-1 border-t border-line"></div>
                  <RouterLink :to="{ name: 'me' }" @click="menuOpen = false" role="menuitem"
                              class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-left text-sm text-ink hover:bg-canvas transition-colors">
                    <Icon name="user" :size="16" /> 个人中心
                  </RouterLink>
                  <RouterLink :to="{ name: 'profile-edit' }" @click="menuOpen = false" role="menuitem"
                              class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-left text-sm text-ink hover:bg-canvas transition-colors">
                    <Icon name="edit" :size="16" /> 编辑资料
                  </RouterLink>
                  <button type="button" @click="doLogout" role="menuitem"
                          class="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-left text-sm text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors">
                    <Icon name="logout" :size="16" /> 退出登录
                  </button>
                </div>
              </transition>
            </div>

            <!-- 未登录：登录/注册入口 -->
            <div v-else class="flex items-center gap-2">
              <RouterLink :to="{ name: 'login' }"
                          class="h-9 px-3.5 rounded-xl text-sm font-medium text-muted hover:text-ink hover:bg-canvas inline-flex items-center transition-colors">登录</RouterLink>
              <RouterLink :to="{ name: 'register' }"
                          class="h-9 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold inline-flex items-center transition-colors">注册</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </header>

    <main id="main-content" tabindex="-1" class="app-main flex-1 mx-auto w-full max-w-7xl px-4 py-6">
      <slot />
    </main>

    <nav class="mobile-nav fixed bottom-0 inset-x-0 z-40 sm:hidden bg-surface border-t border-line flex" aria-label="移动端主导航">
      <RouterLink v-for="t in tabs" :key="t.name" :to="{ name: t.name }" class="flex-1 flex flex-col items-center justify-center gap-1 min-h-[64px] text-[10px] font-medium" :class="activeTab === t.name ? 'text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-500/10' : 'text-muted'" :aria-current="activeTab === t.name ? 'page' : undefined"><Icon :name="t.icon" :size="21" />{{ t.label }}<span v-if="t.name === 'messages' && messages.unreadCount" class="text-rose-600 dark:text-rose-300 text-[10px]">{{ messages.unreadCount }} 未读</span></RouterLink>
    </nav>
    <footer class="border-t border-line mt-auto mb-16 sm:mb-0">
      <div class="mx-auto max-w-7xl px-4 py-6 flex flex-wrap items-center justify-between gap-2 text-xs text-subtle">
        <p>绿循校园 GreenCampus · 校园闲置教材与物品循环流转系统</p>
        <p>校园闲置循环 · 碳积分激励</p>
      </div>
    </footer>
  </div>
</template>
