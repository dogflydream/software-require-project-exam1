import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/lib/api'

/**
 * 分类状态：分类由管理员在后台维护，前端所有视图共用同一份数据，
 * 避免各页面写死分类列表。变更后调用 load() 刷新即可全局生效。
 */
export const useCategoryStore = defineStore('category', () => {
  const list = ref([])
  const loaded = ref(false)

  /** 供筛选/发布使用的分类（按 sort_order 排序，后端已排序）。 */
  const names = computed(() => list.value.map(c => c.name))
  const defaultName = computed(() => list.value[0]?.name || '其它')

  async function load(force = false) {
    if (loaded.value && !force) return list.value
    try {
      list.value = await api.get('/api/categories')
      loaded.value = true
    } catch { /* 分类加载失败时保持上次结果，页面仍可用 */ }
    return list.value
  }

  function iconOf(name) {
    return list.value.find(c => c.name === name)?.icon || 'box'
  }
  function factorOf(name) {
    return list.value.find(c => c.name === name)?.carbon_factor ?? 2.0
  }

  return { list, loaded, names, defaultName, load, iconOf, factorOf }
})
