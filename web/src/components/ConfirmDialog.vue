<script setup>
import DialogBoundary from './DialogBoundary.vue'
import { useUiStore } from '@/stores/ui'
import Icon from './Icon.vue'
const ui = useUiStore()
</script>

<template>
  <Teleport to="body">
  <transition name="fade">
    <div v-if="ui.confirm" class="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
         @click.self="ui.resolveConfirm(false)">
      <transition name="sheet" appear>
        <DialogBoundary @close="ui.resolveConfirm(false)" class="w-full max-w-sm bg-elevated rounded-2xl shadow-lift p-5" role="alertdialog" aria-modal="true"
             :aria-label="ui.confirm.title">
          <span class="grid place-items-center w-11 h-11 rounded-xl"
                :class="ui.confirm.danger ? 'bg-red-50 dark:bg-red-500/10 text-red-600' : 'bg-brand-50 dark:bg-brand-500/10 text-brand-600'">
            <Icon :name="ui.confirm.danger ? 'alert' : 'info'" :size="22" />
          </span>
          <h3 class="mt-3 font-semibold text-ink">{{ ui.confirm.title }}</h3>
          <p class="mt-1.5 text-sm text-muted">{{ ui.confirm.text }}</p>
          <div class="mt-5 flex justify-end gap-2">
            <button data-initial-focus @click="ui.resolveConfirm(false)"
                    class="h-10 px-4 rounded-xl text-sm font-medium text-muted hover:bg-canvas transition-colors">取消</button>
            <button @click="ui.resolveConfirm(true)"
                    class="h-10 px-4 rounded-xl text-sm font-semibold text-white transition-colors"
                    :class="ui.confirm.danger ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-600 hover:bg-brand-700'">
              {{ ui.confirm.ok }}
            </button>
          </div>
        </DialogBoundary>
      </transition>
    </div>
  </transition>
  </Teleport>
</template>
