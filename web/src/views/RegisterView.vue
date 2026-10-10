<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

const form = ref({ name: '', student_no: '', college: '', password: '', confirm: '' })
const err = ref('')
const loading = ref(false)
const showPwd = ref(false)

const colleges = ['计算机学院', '环境学院', '经济管理学院', '外国语学院', '信息学院', '机械工程学院', '文学院', '数学学院']

const pwdScore = computed(() => {
  const p = form.value.password
  let s = 0
  if (p.length >= 6) s++
  if (p.length >= 10) s++
  if (/[A-Za-z]/.test(p) && /\d/.test(p)) s++
  if (/[^A-Za-z0-9]/.test(p)) s++
  return Math.min(s, 4)
})
const pwdHint = ['', '较弱', '一般', '较强', '很强'][pwdScore.value]
const pwdColor = ['', 'bg-rose-400', 'bg-amber-400', 'bg-brand-400', 'bg-brand-600'][pwdScore.value]

async function submit() {
  err.value = ''
  if (!form.value.name) { err.value = '请输入姓名'; return }
  if (form.value.student_no.length < 3) { err.value = '学号至少 3 位'; return }
  if (form.value.password.length < 6) { err.value = '密码至少 6 位'; return }
  if (form.value.password !== form.value.confirm) { err.value = '两次输入的密码不一致'; return }
  loading.value = true
  try {
    const u = await auth.register({
      name: form.value.name,
      student_no: form.value.student_no,
      college: form.value.college || '未填写学院',
      password: form.value.password,
    })
    ui.toast(`注册成功，欢迎加入 ${u.name}`)
    router.replace({ name: 'market' })
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen grid lg:grid-cols-2">
    <aside class="relative hidden lg:flex flex-col justify-between p-10 bg-gradient-to-br from-emerald-900 via-brand-700 to-brand-600 text-white overflow-hidden">
      <div class="absolute -left-20 -top-24 w-80 h-80 rounded-full bg-white/10 blur-2xl"></div>
      <div class="absolute left-16 -bottom-28 w-64 h-64 rounded-full bg-brand-300/20 blur-2xl"></div>
      <div class="relative flex items-center gap-2.5">
        <span class="grid place-items-center w-10 h-10 rounded-xl bg-white/15 backdrop-blur"><Icon name="leaf" :size="22" /></span>
        <span class="font-bold text-lg">绿循校园</span>
      </div>
      <div class="relative">
        <h1 class="text-3xl font-bold leading-snug">加入绿色循环<br />从一次发布开始</h1>
        <ul class="mt-6 space-y-3 text-sm text-white/85">
          <li class="flex items-start gap-2.5"><Icon name="check" :size="17" class="mt-0.5 shrink-0" /> 发布闲置物品，立即获得 10 碳积分</li>
          <li class="flex items-start gap-2.5"><Icon name="check" :size="17" class="mt-0.5 shrink-0" /> 完成一次流转，卖家再得 20 碳积分</li>
          <li class="flex items-start gap-2.5"><Icon name="check" :size="17" class="mt-0.5 shrink-0" /> 积分可在商城兑换校园绿色好礼</li>
          <li class="flex items-start gap-2.5"><Icon name="check" :size="17" class="mt-0.5 shrink-0" /> 个人减碳数据实时汇入学院排行</li>
        </ul>
      </div>
      <p class="relative text-[11px] text-white/60">软件工程实验项目 · 增量模型开发</p>
    </aside>

    <section class="flex items-center justify-center p-6 bg-canvas">
      <div class="w-full max-w-sm">
        <div class="lg:hidden flex items-center gap-2.5 mb-6">
          <span class="grid place-items-center w-9 h-9 rounded-xl bg-gradient-to-br from-brand-400 to-brand-700 text-white">
            <Icon name="leaf" :size="20" />
          </span>
          <span class="font-bold text-ink">绿循校园</span>
        </div>

        <h2 class="text-2xl font-bold text-ink">注册新账号</h2>
        <p class="mt-1.5 text-sm text-muted">填写基本信息即可开始，注册后自动登录</p>

        <form class="mt-7 space-y-4" @submit.prevent="submit">
          <div>
            <label for="rg-name" class="block text-[13px] font-medium text-ink mb-1.5">姓名 <span class="text-rose-500">*</span></label>
            <input id="rg-name" v-model.trim="form.name" maxlength="20" autocomplete="name" placeholder="请输入真实姓名"
                   class="w-full h-11 px-3.5 rounded-xl bg-surface border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          </div>

          <div>
            <label for="rg-no" class="block text-[13px] font-medium text-ink mb-1.5">学号 <span class="text-rose-500">*</span></label>
            <input id="rg-no" v-model.trim="form.student_no" maxlength="20" placeholder="学号将作为登录账号"
                   class="w-full h-11 px-3.5 rounded-xl bg-surface border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          </div>

          <div>
            <label for="rg-college" class="block text-[13px] font-medium text-ink mb-1.5">学院</label>
            <div class="relative">
              <input id="rg-college" v-model.trim="form.college" maxlength="30" list="college-list" placeholder="选择或输入学院名称"
                     class="w-full h-11 px-3.5 rounded-xl bg-surface border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
              <datalist id="college-list"><option v-for="c in colleges" :key="c" :value="c" /></datalist>
            </div>
          </div>

          <div>
            <label for="rg-pwd" class="block text-[13px] font-medium text-ink mb-1.5">密码 <span class="text-rose-500">*</span></label>
            <div class="relative">
              <input id="rg-pwd" v-model="form.password" :type="showPwd ? 'text' : 'password'" autocomplete="new-password" placeholder="至少 6 位"
                     class="w-full h-11 pl-3.5 pr-10 rounded-xl bg-surface border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
              <button type="button" @click="showPwd = !showPwd" :aria-label="showPwd ? '隐藏密码' : '显示密码'"
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-subtle hover:text-ink transition-colors">
                <Icon name="eye" :size="17" />
              </button>
            </div>
            <div v-if="form.password" class="mt-1.5 flex items-center gap-2">
              <div class="flex-1 h-1.5 rounded-full bg-canvas overflow-hidden">
                <div class="h-full rounded-full transition-all duration-300" :class="pwdColor" :style="{ width: (pwdScore / 4 * 100) + '%' }"></div>
              </div>
              <span class="text-[11px] text-subtle">强度：{{ pwdHint }}</span>
            </div>
          </div>

          <div>
            <label for="rg-confirm" class="block text-[13px] font-medium text-ink mb-1.5">确认密码 <span class="text-rose-500">*</span></label>
            <input id="rg-confirm" v-model="form.confirm" :type="showPwd ? 'text' : 'password'" autocomplete="new-password" placeholder="再次输入密码"
                   class="w-full h-11 px-3.5 rounded-xl bg-surface border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          </div>

          <p v-if="err" class="text-[13px] text-rose-500">{{ err }}</p>

          <button type="submit" :disabled="loading"
                  class="w-full h-11 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50 inline-flex items-center justify-center gap-2 transition-colors">
            <span v-if="loading" class="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin"></span>
            {{ loading ? '注册中…' : '注册并登录' }}
          </button>
        </form>

        <p class="mt-5 text-center text-sm text-muted">
          已有账号？
          <RouterLink :to="{ name: 'login' }" class="text-brand-700 dark:text-brand-400 font-medium hover:underline">返回登录</RouterLink>
        </p>
      </div>
    </section>
  </div>
</template>
