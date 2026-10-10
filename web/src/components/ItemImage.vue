<script setup>
import Icon from './Icon.vue'
import { catBg, catFg, itemCatIcon } from '@/lib/format'
import { useCategoryStore } from '@/stores/category'

defineProps({
  item: { type: Object, required: true },
  ratio: { type: String, default: 'aspect-[4/3]' },
})

const categories = useCategoryStore()
</script>

<template>
  <!-- 有图显示图片，无图回落到按分类着色的占位块，保证卡片视觉高度一致 -->
  <div :class="ratio" class="w-full overflow-hidden rounded-xl bg-canvas relative">
    <img v-if="item.image" :src="item.image" :alt="item.title" loading="lazy"
         class="w-full h-full object-cover" />
    <div v-else class="w-full h-full grid place-items-center" :class="catBg(item.category)">
      <Icon :name="itemCatIcon(item, categories.list)" :size="34" :class="catFg(item.category)" />
    </div>
  </div>
</template>
