/** 展示层格式化与状态映射（与后端约定一致）。 */

export const AVATAR_COLORS = ['#059669','#0891b2','#7c3aed','#db2777','#ea580c','#2563eb','#0d9488','#ca8a04']

export function avatarColor(name) {
  if (!name) return AVATAR_COLORS[0]
  let h = 0
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 997
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}

const CATEGORY = {
  '教材':   { icon: 'book',   chip: 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-200/70 dark:border-blue-500/20', bg: 'bg-blue-50 dark:bg-blue-500/10', fg: 'text-blue-600', bar: 'bg-blue-500' },
  '考研':   { icon: 'pencil', chip: 'bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-200/70 dark:border-violet-500/20', bg: 'bg-violet-50 dark:bg-violet-500/10', fg: 'text-violet-600', bar: 'bg-violet-500' },
  '生活品': { icon: 'sofa',   chip: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200/70 dark:border-amber-500/20', bg: 'bg-amber-50 dark:bg-amber-500/10', fg: 'text-amber-600', bar: 'bg-amber-500' },
}
const CATEGORY_FALLBACK = { icon: 'box', chip: 'bg-canvas text-muted border-line', bg: 'bg-canvas', fg: 'text-muted', bar: 'bg-slate-400' }
const cat = (c) => CATEGORY[c] || CATEGORY_FALLBACK
export const catIcon = (c) => cat(c).icon
export const catChip = (c) => cat(c).chip
export const catBg = (c) => cat(c).bg
export const catFg = (c) => cat(c).fg
export const catBar = (c) => cat(c).bar

export const CARBON_FACTOR = { '教材': 2.5, '考研': 2.0, '生活品': 3.5 }
export const carbonOf = (c) => CARBON_FACTOR[c] || 2.0

const ORDER_STATUS = {
  reserved:  { label: '已预约', cls: 'bg-amber-100 dark:bg-amber-400/15 text-amber-700 dark:text-amber-300' },
  confirmed: { label: '待自提', cls: 'bg-blue-100 dark:bg-blue-400/15 text-blue-700 dark:text-blue-300' },
  completed: { label: '已完成', cls: 'bg-brand-100 dark:bg-brand-400/15 text-brand-700 dark:text-brand-300' },
  cancelled: { label: '已取消', cls: 'bg-canvas text-subtle border border-line' },
}
export const statusLabel = (s) => (ORDER_STATUS[s] || {}).label || s
export const statusChip = (s) => (ORDER_STATUS[s] || ORDER_STATUS.cancelled).cls

const ITEM_STATUS = {
  available: { label: '在售',   cls: 'bg-brand-100 dark:bg-brand-400/15 text-brand-700 dark:text-brand-300' },
  reserved:  { label: '已预约', cls: 'bg-amber-100 dark:bg-amber-400/15 text-amber-700 dark:text-amber-300' },
  completed: { label: '已流转', cls: 'bg-blue-100 dark:bg-blue-400/15 text-blue-700 dark:text-blue-300' },
  offshelf:  { label: '已下架', cls: 'bg-red-100 dark:bg-red-400/15 text-red-600' },
}
export const itemStatusLabel = (s) => (ITEM_STATUS[s] || {}).label || s
export const itemStatusChip = (s) => (ITEM_STATUS[s] || ITEM_STATUS.offshelf).cls

export const isGain = (log) => (log.delta ?? 0) >= 0
export const inStock = (p) => (p.stock ?? 0) > 0
