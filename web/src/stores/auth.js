import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/lib/api'

/**
 * 认证状态：用户身份的唯一来源是服务端会话。
 * 前端不再持有可伪造的 user_id，所有受保护请求都依赖会话 Cookie。
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const ready = ref(false)   // 是否已完成首次会话探测

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  /** 首次进入应用时探测会话；401 视为未登录，不报错。 */
  async function bootstrap() {
    try {
      user.value = await api.get('/api/auth/me')
    } catch {
      user.value = null
    } finally {
      ready.value = true
    }
  }

  async function login(loginName, password) {
    user.value = await api.post('/api/auth/login', { login: loginName, password })
    return user.value
  }

  async function register(payload) {
    user.value = await api.post('/api/auth/register', payload)
    return user.value
  }

  async function logout() {
    try { await api.post('/api/auth/logout') } catch { /* 忽略网络异常，本地状态照常清理 */ }
    user.value = null
  }

  /** 资料或积分变动后同步最新用户对象。 */
  async function refresh() {
    try { user.value = await api.get('/api/auth/me') } catch { /* 会话失效时保持原状 */ }
  }

  function setUser(u) { user.value = u }

  return { user, ready, isLoggedIn, isAdmin, bootstrap, login, register, logout, refresh, setUser }
})
