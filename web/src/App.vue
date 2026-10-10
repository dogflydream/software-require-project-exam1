<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from './components/AppShell.vue'
import ToastHost from './components/ToastHost.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'

const route = useRoute()
// 登录/注册使用独立整屏布局，不套用主框架（顶栏/页脚）
const bare = computed(() => !!route.meta.bare)
</script>

<template>
  <RouterView v-if="bare" v-slot="{ Component }">
    <transition name="page" mode="out-in"><component :is="Component" /></transition>
  </RouterView>

  <AppShell v-else>
    <RouterView v-slot="{ Component }">
      <transition name="page" mode="out-in"><component :is="Component" /></transition>
    </RouterView>
  </AppShell>

  <ToastHost />
  <ConfirmDialog />
</template>
