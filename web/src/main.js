import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css'
import { useAuthStore } from './stores/auth'
import { useUiStore } from './stores/ui'

const pinia = createPinia()
const app = createApp(App).use(pinia).use(router)
window.addEventListener('gc:session-expired', () => {
  const auth = useAuthStore(pinia)
  if (!auth.isLoggedIn) return
  auth.setUser(null)
  useUiStore(pinia).toast('登录已过期，请重新登录', 'error')
  if (router.currentRoute.value.meta.requiresAuth) {
    router.replace({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  }
})
app.mount('#app')
