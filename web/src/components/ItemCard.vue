<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Icon from './Icon.vue'
import ItemImage from './ItemImage.vue'
import Avatar from './Avatar.vue'
import { catChip } from '@/lib/format'

const props = defineProps({
  item: { type: Object, required: true },
  me: { type: Object, default: null },
  favorited: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['reserve', 'favorite'])

const isOwner = computed(() => props.me && props.item.owner_id === props.me.id)
const canReserve = computed(() => props.me && !isOwner.value && props.item.status === 'available')
</script>

<template>
  <article class="group flex flex-col rounded-xl2 bg-surface border border-line shadow-card hover:shadow-lift hover:-translate-y-0.5 transition-all duration-200">
    <div class="relative p-3 pb-0">
      <RouterLink :to="`/items/${item.id}`" :aria-label="`查看 ${item.title} 详情`">
        <ItemImage :item="item" />
      </RouterLink>
      <div class="absolute top-5 right-5 flex items-center gap-1.5">
        <span v-if="item.status === 'reserved'"
              class="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-400/15 text-amber-700 dark:text-amber-300 text-[11px] font-semibold shadow-sm">已预约</span>
        <button v-if="me" type="button" @click.prevent="$emit('favorite', item)" :disabled="busy"
                :aria-label="favorited ? '取消收藏' : '收藏'"
                class="grid place-items-center w-8 h-8 rounded-lg backdrop-blur bg-white/80 dark:bg-black/40 transition-colors disabled:opacity-50"
                :class="favorited ? 'text-rose-500' : 'text-slate-400 hover:text-rose-500'">
          <Icon :name="favorited ? 'heartfill' : 'heart'" :size="17" />
        </button>
      </div>
    </div>

    <div class="flex flex-col flex-1 p-4 pt-3">
      <div class="flex items-center gap-2">
        <span class="px-2 py-0.5 rounded-md text-[11px] font-medium border" :class="catChip(item.category)">{{ item.category }}</span>
        <span class="inline-flex items-center gap-1 text-[11px] text-subtle"><Icon name="recycle" :size="12" />循环 {{ item.cycle_count }}</span>
      </div>

      <RouterLink :to="`/items/${item.id}`" class="mt-2">
        <h3 class="font-semibold text-ink leading-snug clamp-2 group-hover:text-brand-700 dark:group-hover:text-brand-400 transition-colors">{{ item.title }}</h3>
      </RouterLink>
      <p class="mt-1 text-[13px] text-muted clamp-2 flex-1">{{ item.description || '暂无描述' }}</p>

      <div class="mt-3 pt-3 border-t border-line flex items-end justify-between gap-2">
        <div class="min-w-0">
          <p class="text-lg font-bold text-brand-700 dark:text-brand-400 tnum leading-none">¥{{ item.price.toFixed(2) }}</p>
          <RouterLink :to="`/u/${item.owner_id}`" class="mt-1.5 flex items-center gap-1.5 min-w-0 hover:text-brand-700 dark:hover:text-brand-400 transition-colors">
            <Avatar :name="item.owner_name" :user="{ name: item.owner_name, avatar: item.owner_avatar }" :size="18" rounded="rounded-md" />
            <span class="text-[11px] text-subtle truncate">{{ item.owner_name }} · {{ item.owner_college }}</span>
          </RouterLink>
        </div>
        <button v-if="canReserve" type="button" @click="$emit('reserve', item)" :disabled="busy"
                class="shrink-0 h-9 px-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-[13px] font-semibold inline-flex items-center gap-1.5 transition-colors disabled:opacity-50">
          <Icon name="handshake" :size="15" /> 预约
        </button>
        <span v-else-if="isOwner" class="shrink-0 px-2.5 py-1.5 rounded-lg bg-canvas text-[11px] text-subtle border border-line">我发布的</span>
        <span v-else-if="item.status === 'reserved'" class="shrink-0 px-2.5 py-1.5 rounded-lg bg-canvas text-[11px] text-subtle border border-line">已被预约</span>
      </div>
    </div>
  </article>
</template>
