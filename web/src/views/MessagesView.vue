<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useMessagesStore } from '@/stores/messages'
import { statusLabel } from '@/lib/format'
import Icon from '@/components/Icon.vue'
import Avatar from '@/components/Avatar.vue'
const route = useRoute()
const auth = useAuthStore()
const inbox = useMessagesStore()
const orderId = computed(() => String(route.params.orderId || ''))
const selected = computed(() => inbox.list.find(c => String(c.order_id) === orderId.value))
const active = computed(() => selected.value && ['reserved', 'confirmed'].includes(selected.value.status))
const messages = ref([])
const drafts = reactive({})
const draft = computed({ get: () => drafts[orderId.value] || '', set: v => { drafts[orderId.value] = v } })
const pending = new Map()
const loading = ref(false), sending = ref(false), olderLoading = ref(false)
const error = ref(''), sendError = ref(''), listError = ref('')
const hasOlder = ref(false), stream = ref(null)
let generation = 0, timer, stopped = false
const readCursor = new Map()
const merge = list => { messages.value = [...new Map([...messages.value, ...list].map(m => [m.id, m])).values()].sort((a,b) => a.id-b.id) }
async function loadList() {
  try { await inbox.load(); listError.value = '' }
  catch (e) { listError.value = e.message }
}
async function markRead(id, last) {
  if (!last || document.hidden || (readCursor.get(id) || 0) >= last) return
  await api.post(`/api/orders/${id}/messages/read`, { last_message_id: last })
  readCursor.set(id, last)
  await loadList()
}
async function loadMessages(reset = false) {
  const id = orderId.value, version = generation
  if (!id) return
  if (reset) loading.value = true
  const nearBottom = !stream.value || stream.value.scrollHeight - stream.value.scrollTop - stream.value.clientHeight < 100
  const after = reset ? 0 : messages.value.at(-1)?.id || 0
  try {
    const data = await api.get(`/api/orders/${id}/messages?after=${after}`)
    if (version !== generation || stopped) return
    merge(data.messages)
    if (!after) hasOlder.value = data.has_more
    error.value = ''
    await nextTick()
    if (reset || nearBottom) {
      if (stream.value) stream.value.scrollTop = stream.value.scrollHeight
      await markRead(id, messages.value.at(-1)?.id)
    }
  } catch (e) { if (version === generation) error.value = e.message }
  finally { if (version === generation) loading.value = false }
}
async function older() {
  if (olderLoading.value || !messages.value.length) return
  const id = orderId.value, version = generation
  olderLoading.value = true
  const height = stream.value?.scrollHeight || 0, top = stream.value?.scrollTop || 0
  try {
    const data = await api.get(`/api/orders/${id}/messages?before=${messages.value[0].id}`)
    if (version !== generation) return
    merge(data.messages); hasOlder.value = data.has_more
    await nextTick()
    if (stream.value) stream.value.scrollTop = top + stream.value.scrollHeight - height
  } catch (e) { if (version === generation) error.value = e.message }
  finally { olderLoading.value = false }
}
async function send() {
  const id = orderId.value, content = draft.value.trim()
  if (!id || !content || sending.value || !active.value) return
  sending.value = true; sendError.value = ''
  const prior = pending.get(id)
  const payload = prior?.content === content ? prior : { content, client_nonce: crypto.randomUUID() }
  pending.set(id, payload)
  try {
    await api.post(`/api/orders/${id}/messages`, payload)
    pending.delete(id)
    if ((drafts[id] || '').trim() === content) drafts[id] = ''
    if (orderId.value === id) { await loadMessages(); await loadList() }
  } catch (e) { if (orderId.value === id) sendError.value = e.message }
  finally { sending.value = false }
}
async function refresh() {
  if (!document.hidden) { await loadList(); await loadMessages() }
  if (!stopped) timer = setTimeout(refresh, 3000)
}
function visible() { if (!document.hidden) { loadList(); loadMessages() } }
watch(orderId, () => {
  generation++; messages.value = []; error.value = ''; sendError.value = ''; hasOlder.value = false
  loadMessages(true)
})
onMounted(async () => {
  await loadList()
  if (stopped) return
  await loadMessages(true)
  if (stopped) return
  if (!stopped) timer = setTimeout(refresh, 3000)
  document.addEventListener('visibilitychange', visible)
})
onUnmounted(() => { stopped = true; generation++; clearTimeout(timer); document.removeEventListener('visibilitychange', visible) })
</script>
<template>
  <div>
    <div class="mb-5"><p class="section-eyebrow">CAMPUS CONVERSATIONS</p><h1 class="mt-1 text-2xl font-bold">站内消息</h1><p class="mt-2 text-sm text-muted">在平台内约定交接时间与地点，无需填写或交换第三方联系方式。</p></div>
    <div class="grid md:grid-cols-[280px_minmax(0,1fr)] rounded-xl2 border border-line bg-surface overflow-hidden shadow-card min-h-[580px]">
      <aside class="md:border-r border-line" :class="orderId ? 'hidden md:block' : ''" aria-label="订单会话列表">
        <div class="flex justify-between items-center p-4 border-b border-line"><h2 class="font-semibold text-sm">我的订单会话</h2><button type="button" @click="loadList" class="text-xs text-brand-700 dark:text-brand-300">刷新</button></div>
        <p v-if="listError" role="alert" class="p-4 text-xs text-rose-600">{{ listError }}</p>
        <div class="max-h-[65vh] overflow-y-auto">
          <RouterLink v-for="c in inbox.list" :key="c.order_id" :to="`/messages/${c.order_id}`" class="block p-4 border-b border-line transition-colors hover:bg-canvas" :class="String(c.order_id) === orderId ? 'bg-brand-50 dark:bg-brand-500/10' : ''" :aria-current="String(c.order_id) === orderId ? 'page' : undefined">
            <div class="flex gap-2 items-center"><Avatar :user="{name:c.peer_name,avatar:c.peer_avatar}" :size="32" /><span class="min-w-0 flex-1 text-sm font-semibold truncate">{{ c.peer_name }}</span><span v-if="c.unread_count" class="bg-rose-600 text-white px-1.5 rounded-full text-[10px]" :aria-label="`${c.unread_count} 条未读`">{{ c.unread_count }}</span></div>
            <p class="mt-2 text-xs text-ink truncate">{{ c.item_title }}</p><p class="mt-1 text-xs text-muted truncate">{{ c.last_message || '尚无消息，点击约定自提' }}</p><p class="mt-1 text-[10px] text-muted">订单 #{{ c.order_id }} · {{ statusLabel(c.status) }}</p>
          </RouterLink>
        </div>
        <p v-if="!inbox.list.length && !listError" class="p-6 text-sm text-muted leading-relaxed">暂无订单会话。预约物品后，可与交易对方在这里沟通。<RouterLink to="/" class="block mt-3 text-brand-700 dark:text-brand-300">去市集逛逛 →</RouterLink></p>
      </aside>
      <section v-if="orderId" class="flex flex-col min-w-0" aria-label="订单聊天">
        <header class="p-4 border-b border-line flex items-center gap-3"><RouterLink to="/messages" class="md:hidden text-muted p-2" aria-label="返回会话列表"><Icon name="arrowleft" :size="18" /></RouterLink><div class="min-w-0 flex-1"><h2 class="text-sm font-semibold truncate">{{ selected?.peer_name || '订单会话' }}</h2><p class="text-xs text-muted mt-1 truncate">{{ selected?.item_title || `订单 #${orderId}` }}</p></div><RouterLink :to="{name:'me',query:{tab:selected?.seller_id === auth.user?.id ? 'sell' : 'buy'}}" class="text-xs text-brand-700 dark:text-brand-300">查看订单</RouterLink></header>
        <p class="px-4 py-2 bg-canvas text-[11px] text-muted leading-relaxed">仅订单双方可访问。请勿在消息中发送密码、自提码或敏感资料；自提码在验货交接后当面出示。</p>
        <div v-if="error" role="alert" class="px-4 py-3 text-xs text-rose-600 flex justify-between gap-2">{{ error }}<button type="button" @click="loadMessages(true)" class="underline shrink-0">重试</button></div>
        <div ref="stream" class="flex-1 overflow-y-auto p-4 space-y-4 h-[360px] max-h-[52vh]" role="log" aria-label="消息记录" aria-live="polite" @scroll.passive="() => { if (stream && stream.scrollHeight-stream.scrollTop-stream.clientHeight < 30) markRead(orderId,messages.at(-1)?.id).catch(() => {}) }">
          <div v-if="hasOlder" class="text-center"><button type="button" @click="older" :disabled="olderLoading" class="text-xs text-brand-700 dark:text-brand-300">{{ olderLoading ? '加载中…' : '加载更早消息' }}</button></div>
          <p v-if="loading" role="status" class="py-10 text-center text-xs text-muted">正在读取会话…</p>
          <p v-else-if="!messages.length && !error" class="py-14 text-center text-sm text-muted">还没有消息，先和对方打个招呼吧。</p>
          <div v-for="m in messages" :key="m.id" class="flex" :class="m.sender_id === auth.user?.id ? 'justify-end' : 'justify-start'"><div class="max-w-[85%] min-w-0"><p class="text-[10px] text-muted mb-1" :class="m.sender_id === auth.user?.id ? 'text-right' : ''">{{ m.sender_id === auth.user?.id ? '我' : selected?.peer_name }} · {{ m.created_at }}</p><p class="rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap break-words [overflow-wrap:anywhere]" :class="m.sender_id === auth.user?.id ? 'bg-brand-700 text-white rounded-tr-sm' : 'bg-canvas border border-line text-ink rounded-tl-sm'">{{ m.content }}</p></div></div>
        </div>
        <form @submit.prevent="send" class="p-4 border-t border-line">
          <p v-if="selected && !active" class="mb-3 text-xs text-muted">订单已结束，会话仅可查看历史消息。</p>
          <label for="chat-message" class="sr-only">发送站内消息</label><textarea id="chat-message" v-model="draft" :disabled="!active || sending" maxlength="1000" rows="2" placeholder="约定自提时间、地点，或沟通物品情况…" class="w-full rounded-xl border border-line bg-canvas px-3 py-2 text-sm resize-none disabled:opacity-50" @keydown.ctrl.enter.prevent="send" @keydown.meta.enter.prevent="send"></textarea>
          <p v-if="sendError" role="alert" class="mt-2 text-xs text-rose-600">{{ sendError }}，内容已保留，可重试发送。</p>
          <div class="mt-2 flex items-center justify-between gap-2"><span class="text-[10px] text-muted">{{ draft.length }}/1000 · Ctrl / ⌘ + Enter 发送</span><button type="submit" :disabled="!active || !draft.trim() || sending" class="primary-action disabled:opacity-40">{{ sending ? '发送中…' : '发送消息' }}</button></div>
        </form>
      </section>
      <div v-else class="hidden md:grid place-items-center p-10 text-center"><div><Icon name="message" :size="40" class="mx-auto text-brand-700 dark:text-brand-300" /><h2 class="mt-4 font-semibold">让交接更简单</h2><p class="mt-2 text-sm text-muted">选择一个订单会话，直接与交易对方沟通。</p></div></div>
    </div>
  </div>
</template>
