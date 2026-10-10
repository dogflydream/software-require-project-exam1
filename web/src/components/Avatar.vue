<script setup>
import { computed } from 'vue'
import { avatarColor } from '@/lib/format'

const props = defineProps({
  user: { type: Object, default: null },
  name: { type: String, default: '' },
  size: { type: [Number, String], default: 40 },
  rounded: { type: String, default: 'rounded-xl' },
})

const displayName = computed(() => props.user?.name || props.name || '?')
const src = computed(() => props.user?.avatar || null)
const initial = computed(() => displayName.value.slice(0, 1))
const px = computed(() => `${props.size}px`)
const fontSize = computed(() => `${Math.max(11, Math.round(Number(props.size) * 0.38))}px`)
</script>

<template>
  <img v-if="src" :src="src" :alt="`${displayName} 的头像`" :style="{ width: px, height: px }"
       class="object-cover shrink-0" :class="rounded" />
  <span v-else :style="{ width: px, height: px, background: avatarColor(displayName), fontSize }"
        class="grid place-items-center text-white font-bold shrink-0 select-none" :class="rounded"
        :aria-label="displayName">{{ initial }}</span>
</template>
