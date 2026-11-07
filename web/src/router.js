import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guestOnly: true, bare: true, title: '登录' } },
  { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { guestOnly: true, bare: true, title: '注册' } },
  { path: '/', name: 'market', component: () => import('@/views/MarketView.vue'), meta: { title: '绿色市集' } },
  { path: '/items/:id', name: 'item', component: () => import('@/views/ItemDetailView.vue'), meta: { title: '物品详情' } },
  { path: '/mall', name: 'mall', component: () => import('@/views/MallView.vue'), meta: { title: '积分商城' } },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '绿色大屏' } },
  { path: '/me', name: 'me', component: () => import('@/views/ProfileView.vue'), meta: { requiresAuth: true, title: '个人中心' } },
  { path: '/messages/:orderId?', name: 'messages', component: () => import('@/views/MessagesView.vue'), meta: { requiresAuth: true, title: '站内消息' } },
  { path: '/me/edit', name: 'profile-edit', component: () => import('@/views/ProfileEditView.vue'), meta: { requiresAuth: true, title: '编辑资料' } },
  { path: '/u/:id', name: 'user', component: () => import('@/views/UserProfileView.vue'), meta: { title: '用户主页' } },
  { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { requiresAuth: true, requiresAdmin: true, title: '后台管理' } },
  { path: '/:pathMatch(.*)*', name: 'notfound', component: () => import('@/views/NotFoundView.vue'), meta: { title: '页面不存在' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, savedPosition) => savedPosition || (to.path === from.path ? false : { top: 0 }),
})

/**
 * 路由守卫 —— 前端侧的第一道边界（真正的边界在服务端）。
 * - requiresAuth：未登录跳登录页，并记录来源以便登录后回跳
 * - requiresAdmin：非管理员跳 403 提示（服务端同样会拒绝，双保险）
 * - guestOnly：已登录用户不再看到登录/注册页
 */
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.bootstrap()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    const ui = useUiStore()
    ui.toast('该页面仅管理员可访问', 'error')
    return { name: 'market' }
  }
  if (to.meta.guestOnly && auth.isLoggedIn) {
    return { name: 'market' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 绿循校园` : '绿循校园'
})

export default router
