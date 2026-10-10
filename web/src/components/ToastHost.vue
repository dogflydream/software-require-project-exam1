<script setup>
import { useUiStore } from '@/stores/ui'
import Icon from './Icon.vue'
const ui = useUiStore()
const styleFor = (type) => type === 'error'
  ? 'bg-red-600 border-red-700 text-white'
  : type === 'warn' ? 'bg-amber-500 border-amber-600 text-white' : 'bg-brand-600 border-brand-700 text-white'
</script>

<template>
  <div class="fixed bottom-5 right-5 z-[70] flex flex-col gap-2 items-end pointer-events-none" role="status" aria-live="polite">
    <transition-group name="toast">
      <div v-for="t in ui.toasts" :key="t.id"
           class="pointer-events-auto flex items-start gap-2.5 pl-3.5 pr-4 py-3 rounded-xl shadow-lift border max-w-sm"
           :class="styleFor(t.type)">
        <Icon :name="t.type === 'ok' ? 'check' : 'alert'" :size="18" class="shrink-0 mt-px" />
        <span class="text-[13px] leading-snug">{{ t.text }}</span>
      </div>
    </transition-group>
  </div>
</template>
