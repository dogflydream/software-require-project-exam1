<script setup>
import { ref, computed, onMounted } from 'vue'
import Icon from '@/components/Icon.vue'
import { api, fileToCompressedDataURL } from '@/lib/api'
import { useUiStore } from '@/stores/ui'
import { useCategoryStore } from '@/stores/category'

const props = defineProps({ item: { type: Object, default: null } })
const emit = defineEmits(['close', 'saved'])
const ui = useUiStore()
const categories = useCategoryStore()

const isEdit = !!props.item
const form = ref({
  title: props.item?.title || '',
  category: props.item?.category || categories.defaultName,
  description: props.item?.description || '',
  price: props.item?.price ?? 0,
  image: null,   // 仅当用户重新选择图片时才有值
})
const preview = ref(props.item?.image || null)
const err = ref({})
const saving = ref(false)
const readingImage = ref(false)
const fileInput = ref(null)

const carbonHint = computed(() => categories.factorOf(form.value.category))

onMounted(async () => {
  // 弹层打开时锁定背景滚动
  document.body.style.overflow = 'hidden'
  await categories.load()
  if (!form.value.category) form.value.category = categories.defaultName
})
function close() {
  document.body.style.overflow = ''
  emit('close')
}

async function pickImage(e) {
  const file = e.target.files?.[0]
  if (!file) return
  err.value = { ...err.value, image: '' }
  readingImage.value = true
  try {
    const dataUrl = await fileToCompressedDataURL(file)
    form.value.image = dataUrl
    preview.value = dataUrl
  } catch (e2) {
    err.value = { ...err.value, image: e2.message }
  } finally {
    readingImage.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}
function clearImage() {
  preview.value = null
  form.value.image = null
}

async function submit() {
  const e = {}
  if (!form.value.title) e.title = '请填写物品名称'
  if (form.value.price == null || form.value.price < 0) e.price = '价格不能为负'
  err.value = e
  if (Object.keys(e).length) return

  saving.value = true
  try {
    const body = {
      title: form.value.title,
      category: form.value.category,
      description: form.value.description,
      price: form.value.price,
    }
    if (form.value.image) body.image = form.value.image
    if (isEdit) {
      await api.patch(`/api/items/${props.item.id}`, body)
      ui.toast('物品信息已更新')
    } else {
      await api.post('/api/items', body)
      ui.toast('发布成功！获得 10 碳积分')
    }
    document.body.style.overflow = ''
    emit('saved')
  } catch (e2) {
    err.value = { global: e2.message }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <transition name="fade" appear>
    <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4"
         @click.self="close">
      <transition name="sheet" appear>
        <div class="w-full sm:max-w-lg bg-elevated rounded-t-2xl sm:rounded-2xl shadow-lift max-h-[92vh] overflow-y-auto"
             role="dialog" aria-modal="true" :aria-label="isEdit ? '编辑闲置物品' : '发布闲置物品'">
          <div class="flex items-center justify-between px-5 py-4 border-b border-line sticky top-0 bg-elevated/95 backdrop-blur z-10">
            <h3 class="font-semibold text-ink">{{ isEdit ? '编辑闲置物品' : '发布闲置物品' }}</h3>
            <button type="button" @click="close" aria-label="关闭"
                    class="grid place-items-center w-8 h-8 rounded-lg text-muted hover:text-ink hover:bg-canvas transition-colors">
              <Icon name="close" :size="18" />
            </button>
          </div>

          <div class="p-5 space-y-4">
            <!-- 图片上传 -->
            <div>
              <label class="block text-[13px] font-medium text-ink mb-1.5">物品图片</label>
              <div class="flex gap-3">
                <div class="relative w-32 h-32 rounded-xl border border-line bg-canvas overflow-hidden grid place-items-center shrink-0">
                  <img v-if="preview" :src="preview" alt="物品图片预览" class="w-full h-full object-cover" />
                  <div v-else class="text-center text-subtle">
                    <Icon name="image" :size="26" class="mx-auto" />
                    <p class="mt-1 text-[11px]">暂无图片</p>
                  </div>
                  <div v-if="readingImage" class="absolute inset-0 grid place-items-center bg-black/40 text-white text-[11px]">
                    <span class="w-5 h-5 rounded-full border-2 border-white/40 border-t-white animate-spin"></span>
                  </div>
                </div>
                <div class="flex-1 flex flex-col justify-center gap-2">
                  <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp,image/gif" class="hidden" @change="pickImage" />
                  <button type="button" @click="fileInput.click()"
                          class="h-10 px-4 rounded-xl border border-line text-sm font-medium text-ink hover:bg-canvas inline-flex items-center justify-center gap-2 transition-colors">
                    <Icon name="camera" :size="16" /> 选择图片
                  </button>
                  <button v-if="preview" type="button" @click="clearImage"
                          class="h-9 px-4 rounded-xl text-xs text-muted hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 inline-flex items-center justify-center gap-1.5 transition-colors">
                    <Icon name="trash" :size="14" /> 移除图片
                  </button>
                  <p class="text-[11px] text-subtle leading-relaxed">支持 PNG/JPG/WebP/GIF，上传前自动等比压缩，最大 2MB</p>
                </div>
              </div>
              <p v-if="err.image" class="mt-1 text-[12px] text-rose-500">{{ err.image }}</p>
            </div>

            <div>
              <label for="p-title" class="block text-[13px] font-medium text-ink mb-1.5">物品名称 <span class="text-rose-500">*</span></label>
              <input id="p-title" v-model.trim="form.title" maxlength="100" placeholder="例如：《数据结构（C语言版）》严蔚敏"
                     class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
              <p v-if="err.title" class="mt-1 text-[12px] text-rose-500">{{ err.title }}</p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="block text-[13px] font-medium text-ink mb-1.5">分类</label>
                <!-- 分类由管理员维护，此处动态渲染，新增分类无需改前端 -->
                <div class="flex flex-wrap gap-1.5 p-1 rounded-xl bg-canvas border border-line">
                  <button v-for="c in categories.list" :key="c.id" type="button" @click="form.category = c.name"
                          class="px-3 py-2 rounded-lg text-[12px] font-medium transition-colors inline-flex items-center gap-1.5"
                          :class="form.category === c.name ? 'bg-brand-600 text-white' : 'text-muted hover:text-ink'">
                    <Icon :name="c.icon || 'box'" :size="13" />{{ c.name }}
                  </button>
                </div>
                <p class="mt-1.5 text-[11px] text-subtle inline-flex items-center gap-1">
                  <Icon name="leaf" :size="12" /> 单次流转约减碳 {{ carbonHint }} kg CO₂e
                </p>
              </div>
              <div>
                <label for="p-price" class="block text-[13px] font-medium text-ink mb-1.5">价格（元）</label>
                <input id="p-price" v-model.number="form.price" type="number" min="0" step="0.1"
                       class="w-full h-11 px-3.5 rounded-xl bg-canvas border border-line text-sm text-ink tnum focus:outline-none focus:ring-2 focus:ring-brand-500/40" />
                <p v-if="err.price" class="mt-1 text-[12px] text-rose-500">{{ err.price }}</p>
              </div>
            </div>

            <div>
              <label for="p-desc" class="block text-[13px] font-medium text-ink mb-1.5">描述</label>
              <textarea id="p-desc" v-model.trim="form.description" rows="3" maxlength="500" placeholder="成色、使用时长、自提地点…"
                        class="w-full px-3.5 py-2.5 rounded-xl bg-canvas border border-line text-sm text-ink placeholder:text-subtle resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/40"></textarea>
              <p class="mt-1 text-right text-[11px] text-subtle tnum">{{ form.description.length }}/500</p>
            </div>

            <div v-if="!isEdit" class="p-3 rounded-xl bg-brand-50 dark:bg-brand-500/10 flex items-center gap-2.5 text-[12px] text-brand-700 dark:text-brand-300">
              <Icon name="coin" :size="16" /> 发布成功后你将获得 <b>10 碳积分</b>
            </div>
            <div v-else class="p-3 rounded-xl bg-amber-50 dark:bg-amber-400/10 flex items-start gap-2.5 text-[12px] text-amber-700 dark:text-amber-300">
              <Icon name="info" :size="16" class="mt-px shrink-0" />
              <span>修改后物品需<b>重新提交审核</b>，审核通过前将暂时从市集下架。</span>
            </div>
            <p v-if="err.global" class="text-[13px] text-rose-500">{{ err.global }}</p>
          </div>

          <div class="flex justify-end gap-2 px-5 py-4 border-t border-line sticky bottom-0 bg-elevated/95 backdrop-blur">
            <button type="button" @click="close"
                    class="h-10 px-4 rounded-xl text-sm font-medium text-muted hover:bg-canvas transition-colors">取消</button>
            <button type="button" @click="submit" :disabled="saving || readingImage"
                    class="h-10 px-5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold disabled:opacity-50 inline-flex items-center gap-2 transition-colors">
              <span v-if="saving" class="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin"></span>
              {{ saving ? '提交中…' : (isEdit ? '保存修改' : '确认发布') }}
            </button>
          </div>
        </div>
      </transition>
    </div>
  </transition>
</template>
