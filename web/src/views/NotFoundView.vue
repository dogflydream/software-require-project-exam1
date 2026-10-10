<script setup>
import Icon from '@/components/Icon.vue'
</script>

<template>
  <div class="grid place-items-center py-28 rounded-xl2 bg-surface border border-dashed border-line">
    <span class="grid place-items-center w-16 h-16 rounded-2xl bg-canvas text-subtle"><Icon name="search" :size="28" /></span>
    <p class="mt-4 text-2xl font-bold text-ink">404</p>
    <p class="mt-1 text-sm text-muted">你访问的页面不存在</p>
    <RouterLink :to="{ name: 'market' }"
                class="mt-5 h-10 px-5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold inline-flex items-center gap-2 transition-colors">
      <Icon name="arrowleft" :size="16" /> 返回市集
    </RouterLink>
  </div>
</template>
