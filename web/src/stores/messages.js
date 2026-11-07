import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/lib/api'
export const useMessagesStore = defineStore('messages', () => {
  const list = ref([])
  const unreadCount = computed(() => list.value.reduce((n, c) => n + c.unread_count, 0))
  let sequence = 0
  async function load() {
    const id = ++sequence
    const result = await api.get('/api/conversations')
    if (id === sequence) list.value = result
  }
  function reset() { sequence++; list.value = [] }
  return { list, unreadCount, load, reset }
})
