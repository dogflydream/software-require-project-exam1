<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Icon from '@/components/Icon.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const route = useRoute()

const form = ref({ login: '', password: '' })
const err = ref('')
const loading = ref(false)
const showPwd = ref(false)

async function submit() {
  err.value = ''
  if (!form.value.login) { err.value = '请输入学号或姓名'; return }
  if (!form.value.password) { err.value = '请输入密码'; return }
  loading.value = true
  try {
    const u = await auth.login(form.value.login, form.value.password)
    ui.toast(`欢迎回来，${u.name}`)
    router.replace(route.query.redirect || { name: 'market' })
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}

/** 演示账号一键填充：便于课堂演示多账号登录。 */
function useDemo(loginName) {
  form.value.login = loginName
  form.value.password = 'campus123'
  err.value = ''
}
const demoAccounts = [
  { login: '20230101', label: '张绿循', desc: '计算机学院 · 卖家' },
  { login: '20230205', label: '李循环', desc: '环境学院 · 买家' },
  { login: '20230312', label: '王低碳', desc: '经济管理学院 · 买家' },
  { login: '20230418', label: '赵再利用', desc: '外国语学院 · 买家' },
  { login: 'A000000', label: '管理员老师', desc: '信息学院 · 管理员' },
]
</script>

<template>
  <div class="min-h-screen grid lg:grid-cols-2">
    <!-- 品牌侧 -->
    <aside class="relative hidden lg:flex flex-col justify-between p-10 bg-gradient-to-br from-brand-600 via-brand-700 to-emerald-900 text-white overflow-hidden">
      <div class="absolute -right-20 -top-24 w-80 h-80 rounded-full bg-white/10 blur-2xl"></div>
      <div class="absolute right-16 -bottom-28 w-64 h-64 rounded-full bg-brand-300/20 blur-2xl"></div>
      <div class="relative flex items-center gap-2.5">
        <span class="grid place-items-center w-10 h-10 rounded-xl bg-white/15 backdrop-blur"><Icon name="leaf" :size="22" /></span>
        <span class="font-bold text-lg">绿循校园</span>
      </div>
      <div class="relative">
        <h1 class="text-3xl font-bold leading-snug">让每一本教材<br />多流转一次</h1>
        <p class="mt-4 text-white/80 text-sm leading-relaxed max-w-md">
          校园闲置教材与物品循环流转平台。发布闲置得碳积分，完成流转延长物品生命周期，
          用实时数据看板记录全校的减碳贡献。
        </p>
        <div class="mt-8 grid grid-cols-3 gap-4 max-w-md">
          <div class="p-3 rounded-xl bg-white/10 backdrop-blur">
            <p class="text-xl font-bold">循环度</p>
            <p class="text-[11px] text-white/70 mt-1">量化单件物品流转次数</p>
          </div>
          <div class="p-3 rounded-xl bg-white/10 backdrop-blur">
            <p class="text-xl font-bold">碳积分</p>
            <p class="text-[11px] text-white/70 mt-1">激励绿色行为</p>
          </div>
          <div class="p-3 rounded-xl bg-white/10 backdrop-blur">
            <p class="text-xl font-bold">减碳量</p>
            <p class="text-[11px] text-white/70 mt-1">按类别估算 CO₂e</p>
          </div>
        </div>
      </div>
      <p class="relative text-[11px] text-white/60">闲置循环 · 低碳校园</p>
    </aside>

    <!-- 表单侧 -->
    <section class="flex items-center justify-center p-6 bg-canvas">
      <div class="w-full max-w-sm">
        <div class="lg:hidden flex items-center gap-2.5 mb-6">
          <span class="grid place-items-center w-9 h-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 text-white">
            <Icon name="leaf" :size="20" />
          </span>
          <span class="font-bold text-ink">绿循校园</span>
        </div>

        <h2 class="text-2xl font-bold text-ink">登录</h2>
        <p class="mt-1.5 text-sm text-muted">使用学号或姓名登录，开始你的循环之旅</p>

        <form class="mt-7 space-y-4" @submit.prevent="submit">
          <div>
            <label for="login-name" class="block text-[13px] font-medium text-ink mb-1.5">学号 / 姓名</label>
            <div class="relative">
              <Icon name="user" :size="17" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-subtle pointer-events-none" />
              <input id="login-name" v-model.trim="form.login" autocomplete="username" placeholder="例如：20230101"
                     class="w-full h-11 pl-10 pr-3.5 rounded-xl bg-surface border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
            </div>
          </div>

          <div>
            <label for="login-pwd" class="block text-[13px] font-medium text-ink mb-1.5">密码</label>
            <div class="relative">
              <Icon name="lock" :size="17" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-subtle pointer-events-none" />
              <input id="login-pwd" v-model="form.password" :type="showPwd ? 'text' : 'password'" autocomplete="current-password" placeholder="请输入密码"
                     class="w-full h-11 pl-10 pr-10 rounded-xl bg-surface border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
              <button type="button" @click="showPwd = !showPwd" :aria-label="showPwd ? '隐藏密码' : '显示密码'"
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-subtle hover:text-ink transition-colors">
                <Icon name="eye" :size="17" />
              </button>
            </div>
          </div>

          <p v-if="err" class="text-[13px] text-rose-500">{{ err }}</p>

          <button type="submit" :disabled="loading"
                  class="w-full h-11 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50 inline-flex items-center justify-center gap-2 transition-colors">
            <span v-if="loading" class="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin"></span>
            {{ loading ? '登录中…' : '登录' }}
          </button>
        </form>

        <p class="mt-5 text-center text-sm text-muted">
          还没有账号？
          <RouterLink :to="{ name: 'register' }" class="text-brand-700 dark:text-brand-400 font-medium hover:underline">立即注册</RouterLink>
        </p>

        <!-- 演示账号：便于课堂用多个浏览器窗口登录不同身份 -->
        <div class="mt-7 p-3.5 rounded-xl2 bg-surface border border-line">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-subtle flex items-center gap-1.5">
            <Icon name="info" :size="13" /> 演示账号（点击填充，密码 campus123）
          </p>
          <div class="mt-2.5 grid grid-cols-1 gap-1">
            <button v-for="d in demoAccounts" :key="d.login" type="button" @click="useDemo(d.login)"
                    class="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg text-left hover:bg-canvas transition-colors">
              <span class="text-[13px] text-ink">{{ d.label }} <span class="text-subtle font-mono text-[11px]">{{ d.login }}</span></span>
              <span class="text-[11px] text-subtle">{{ d.desc }}</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
