import { defineStore } from 'pinia'
import { ref } from 'vue'

/** 全局 UI 状态：主题、Toast 提示、确认对话框。 */
export const useUiStore = defineStore('ui', () => {
  const theme = ref(localStorage.getItem('gc_theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))
  const toasts = ref([])
  const confirm = ref(null)
  let tid = 0

  function applyTheme() {
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
    const meta = document.querySelector('meta[name=theme-color]')
    if (meta) meta.setAttribute('content', theme.value === 'dark' ? '#0a1310' : '#059669')
  }
  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem('gc_theme', theme.value)
    applyTheme()
  }

  function toast(text, type = 'ok') {
    const id = ++tid
    toasts.value.push({ id, text, type })
    setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, type === 'error' ? 4200 : 2800)
  }

  /** 返回 Promise，确认时 resolve(true)，取消 resolve(false)。 */
  function ask({ title, text, ok = '确认', danger = false }) {
    if (confirm.value) resolveConfirm(false)
    return new Promise((resolve) => {
      confirm.value = { title, text, ok, danger, resolve }
    })
  }
  function resolveConfirm(value) {
    const c = confirm.value
    confirm.value = null
    if (c) c.resolve(value)
  }

  applyTheme()
  return { theme, toggleTheme, applyTheme, toasts, toast, confirm, ask, resolveConfirm }
})
