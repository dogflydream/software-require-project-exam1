<script setup>
import { ref } from 'vue'
import DialogBoundary from './DialogBoundary.vue'
import Icon from './Icon.vue'
import { api } from '@/lib/api'
import { useUiStore } from '@/stores/ui'
const props = defineProps({ order: { type: Object, required: true } })
const emit = defineEmits(['close', 'saved'])
const code = ref('')
const checked = ref(false)
const error = ref('')
const saving = ref(false)
const ui = useUiStore()
function close() { if (!saving.value) emit('close') }
async function submit() {
  if (saving.value) return
  error.value = ''
  if (!checked.value) { error.value = '请先确认已经线下验货并完成自提'; return }
  if (!code.value.trim()) { error.value = '请输入订单自提码'; return }
  saving.value = true
  try {
    await api.post(`/api/orders/${props.order.id}/complete`, { pickup_code: code.value.trim().toUpperCase() })
    ui.toast('流转完成！循环度 +1，卖家获得 20 碳积分')
    emit('saved')
  } catch (e) { error.value = e.message }
  finally { saving.value = false }
}
</script>
<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4" @click.self="close">
      <DialogBoundary @close="close" role="dialog" aria-modal="true" aria-labelledby="fulfill-title" class="w-full max-w-md p-6 rounded-2xl border border-line bg-elevated shadow-lift">
        <div class="flex items-center justify-between"><h2 id="fulfill-title" class="font-semibold text-lg">确认线下自提</h2><button type="button" @click="close" :disabled="saving" aria-label="关闭自提确认" class="p-2 rounded-lg text-muted hover:bg-canvas"><Icon name="close" :size="18" /></button></div>
        <p class="mt-3 text-sm text-ink">{{ order.item_title }}</p>
        <p class="mt-2 text-xs text-muted leading-relaxed">请与交易对方核对物品，完成线下交接后再确认。完成后订单不可取消，系统将记录本次循环和减碳贡献。</p>
        <form @submit.prevent="submit" class="mt-5 space-y-4">
          <div><label for="fulfill-code" class="block text-sm font-medium mb-2">订单自提码</label><input id="fulfill-code" v-model="code" data-initial-focus maxlength="30" autocomplete="off" autocapitalize="characters" placeholder="例如 GC-ABC123" :aria-invalid="!!error" aria-describedby="fulfill-error" class="h-11 w-full rounded-xl border border-line bg-canvas px-3 text-sm font-mono uppercase" /></div>
          <label class="flex items-start gap-2 text-xs text-muted leading-relaxed"><input v-model="checked" type="checkbox" class="mt-0.5 accent-emerald-700" />我已线下验货、完成自提，并与对方确认本次流转。</label>
          <p v-if="error" id="fulfill-error" role="alert" class="text-xs text-rose-600 dark:text-rose-300">{{ error }}</p>
          <div class="flex justify-end gap-2"><button type="button" @click="close" :disabled="saving" class="secondary-action">暂不确认</button><button type="submit" :disabled="saving" class="primary-action disabled:opacity-50">{{ saving ? '确认中…' : '确认完成流转' }}</button></div>
        </form>
      </DialogBoundary>
    </div>
  </Teleport>
</template>
