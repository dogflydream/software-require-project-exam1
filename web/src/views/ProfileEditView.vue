<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import Avatar from '@/components/Avatar.vue'
import { api, fileToCompressedDataURL } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

const form = ref({
  name: auth.user?.name || '',
  college: auth.user?.college || '',
  bio: auth.user?.bio || '',
  contact: auth.user?.contact || '',
})
const avatarPreview = ref(auth.user?.avatar || null)
const pendingAvatar = ref(null)
const err = ref({})
const saving = ref(false)
const uploadingAvatar = ref(false)
const fileInput = ref(null)

const pwd = ref({ old_password: '', new_password: '', confirm: '' })
const pwdErr = ref('')
const savingPwd = ref(false)

const colleges = ['计算机学院', '环境学院', '经济管理学院', '外国语学院', '信息学院', '机械工程学院', '文学院', '数学学院']
const initials = computed(() => (form.value.name || '?').slice(0, 1))

async function pickAvatar(e) {
  const file = e.target.files?.[0]
  if (!file) return
  err.value = { ...err.value, avatar: '' }
  try {
    const dataUrl = await fileToCompressedDataURL(file, 512, 0.9)
    pendingAvatar.value = dataUrl
    avatarPreview.value = dataUrl
  } catch (e2) {
    err.value = { ...err.value, avatar: e2.message }
  } finally {
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function saveProfile() {
  const e = {}
  if (!form.value.name) e.name = '请填写姓名'
  err.value = e
  if (Object.keys(e).length) return
  saving.value = true
  try {
    if (pendingAvatar.value) {
      uploadingAvatar.value = true
      auth.setUser(await api.post('/api/users/me/avatar', { image: pendingAvatar.value }))
      uploadingAvatar.value = false
      pendingAvatar.value = null
    }
    const updated = await api.patch('/api/users/me', {
      name: form.value.name, college: form.value.college,
      bio: form.value.bio, contact: form.value.contact,
    })
    auth.setUser(updated)
    ui.toast('资料已保存')
    router.push({ name: 'me' })
  } catch (e2) {
    err.value = { global: e2.message }
  } finally {
    saving.value = false
    uploadingAvatar.value = false
  }
}

async function changePassword() {
  pwdErr.value = ''
  if (!pwd.value.old_password) { pwdErr.value = '请输入原密码'; return }
  if (pwd.value.new_password.length < 6) { pwdErr.value = '新密码至少 6 位'; return }
  if (pwd.value.new_password !== pwd.value.confirm) { pwdErr.value = '两次输入的新密码不一致'; return }
  savingPwd.value = true
  try {
    await api.post('/api/auth/password', { old_password: pwd.value.old_password, new_password: pwd.value.new_password })
    ui.toast('密码已更新，请重新登录')
    await auth.logout()
    router.push({ name: 'login' })
  } catch (e) {
    pwdErr.value = e.message
  } finally {
    savingPwd.value = false
  }
}
</script>

<template>
  <div class="animate-rise max-w-3xl mx-auto">
    <RouterLink :to="{ name: 'me' }" class="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink transition-colors">
      <Icon name="arrowleft" :size="16" /> 返回个人中心
    </RouterLink>

    <h1 class="mt-4 text-xl font-bold text-ink">编辑资料</h1>
    <p class="mt-1 text-sm text-muted">修改头像与个人信息，学号与角色不可自行变更</p>

    <div class="mt-5 p-6 rounded-xl2 bg-surface border border-line shadow-card">
      <h2 class="font-semibold text-ink inline-flex items-center gap-2"><Icon name="user" :size="17" class="text-brand-600" />头像与基本信息</h2>

      <!-- 头像 -->
      <div class="mt-5 flex flex-wrap items-center gap-5">
        <div class="relative">
          <img v-if="avatarPreview" :src="avatarPreview" alt="头像预览" class="w-24 h-24 rounded-2xl object-cover border border-line" />
          <span v-else class="grid place-items-center w-24 h-24 rounded-2xl bg-brand-600 text-white text-3xl font-bold select-none">{{ initials }}</span>
          <button type="button" @click="fileInput.click()" aria-label="更换头像"
                  class="absolute -right-1.5 -bottom-1.5 grid place-items-center w-8 h-8 rounded-xl bg-brand-600 text-white shadow-lift hover:bg-brand-700 transition-colors">
            <Icon name="camera" :size="16" />
          </button>
        </div>
        <div class="flex-1 min-w-[200px]">
          <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" class="hidden" @change="pickAvatar" />
          <div class="flex flex-wrap gap-2">
            <button type="button" @click="fileInput.click()"
                    class="h-10 px-4 rounded-xl border border-line text-sm font-medium text-ink hover:bg-canvas inline-flex items-center gap-2 transition-colors">
              <Icon name="image" :size="16" /> 选择图片
            </button>
            <button v-if="avatarPreview" type="button" @click="avatarPreview = null; pendingAvatar = 'data:,'"
                    class="h-10 px-4 rounded-xl text-sm text-muted hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 inline-flex items-center gap-2 transition-colors">
              <Icon name="trash" :size="15" /> 移除头像
            </button>
          </div>
          <p class="mt-2 text-[11px] text-subtle leading-relaxed">支持 PNG/JPG/WebP/GIF，会自动等比压缩为方形以内尺寸，最大 2MB</p>
          <p v-if="err.avatar" class="mt-1 text-[12px] text-rose-500">{{ err.avatar }}</p>
        </div>
      </div>

      <!-- 表单 -->
      <div class="mt-6 space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label for="pf-name" class="block text-[13px] font-medium text-ink mb-1.5">姓名 <span class="text-rose-500">*</span></label>
            <input id="pf-name" v-model.trim="form.name" maxlength="20"
                   class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
            <p v-if="err.name" class="mt-1 text-[12px] text-rose-500">{{ err.name }}</p>
          </div>
          <div>
            <label for="pf-college" class="block text-[13px] font-medium text-ink mb-1.5">学院</label>
            <input id="pf-college" v-model.trim="form.college" maxlength="30" list="pf-colleges"
                   class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
            <datalist id="pf-colleges"><option v-for="c in colleges" :key="c" :value="c" /></datalist>
          </div>
        </div>

        <div>
          <label for="pf-bio" class="block text-[13px] font-medium text-ink mb-1.5">个人简介</label>
          <textarea id="pf-bio" v-model.trim="form.bio" rows="2" maxlength="200" placeholder="一句话介绍自己，例如：计算机学院大三，常出闲置教材"
                    class="w-full px-3.5 py-2.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/40"></textarea>
          <p class="mt-1 text-right text-[11px] text-subtle tnum">{{ form.bio.length }}/200</p>
        </div>

        <div>
          <label for="pf-contact" class="block text-[13px] font-medium text-ink mb-1.5">联系方式（仅本人可见）</label>
          <div class="relative">
            <Icon name="phone" :size="16" class="absolute left-3.5 top-1/2 -translate-y-1/2 text-subtle pointer-events-none" />
            <input id="pf-contact" v-model.trim="form.contact" maxlength="100" placeholder="微信 / QQ / 手机号，便于买家线下联系"
                   class="w-full h-11 pl-10 pr-3.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          </div>
          <p class="mt-1 text-[11px] text-subtle">该信息不会展示在公开主页上</p>
        </div>

        <p v-if="err.global" class="text-[13px] text-rose-500">{{ err.global }}</p>

        <div class="flex justify-end gap-2 pt-1">
          <RouterLink :to="{ name: 'me' }"
                      class="h-10 px-4 rounded-xl text-sm font-medium text-muted hover:bg-canvas inline-flex items-center transition-colors">取消</RouterLink>
          <button type="button" @click="saveProfile" :disabled="saving"
                  class="h-10 px-5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50 inline-flex items-center gap-2 transition-colors">
            <span v-if="saving" class="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin"></span>
            {{ uploadingAvatar ? '上传头像中…' : saving ? '保存中…' : '保存修改' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 修改密码 -->
    <div class="mt-4 p-6 rounded-xl2 bg-surface border border-line shadow-card">
      <h2 class="font-semibold text-ink inline-flex items-center gap-2"><Icon name="lock" :size="17" class="text-brand-600" />修改密码</h2>
      <p class="mt-1 text-[12px] text-subtle">修改成功后所有会话将失效，需重新登录</p>
      <div class="mt-5 space-y-4">
        <div>
          <label for="pw-old" class="block text-[13px] font-medium text-ink mb-1.5">原密码</label>
          <input id="pw-old" v-model="pwd.old_password" type="password" autocomplete="current-password"
                 class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label for="pw-new" class="block text-[13px] font-medium text-ink mb-1.5">新密码</label>
            <input id="pw-new" v-model="pwd.new_password" type="password" autocomplete="new-password" placeholder="至少 6 位"
                   class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          </div>
          <div>
            <label for="pw-confirm" class="block text-[13px] font-medium text-ink mb-1.5">确认新密码</label>
            <input id="pw-confirm" v-model="pwd.confirm" type="password" autocomplete="new-password"
                   class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
          </div>
        </div>
        <p v-if="pwdErr" class="text-[13px] text-rose-500">{{ pwdErr }}</p>
        <div class="flex justify-end">
          <button type="button" @click="changePassword" :disabled="savingPwd"
                  class="h-10 px-5 rounded-xl border border-line text-sm font-semibold text-ink hover:bg-canvas disabled:opacity-50 transition-colors">
            {{ savingPwd ? '提交中…' : '更新密码' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
