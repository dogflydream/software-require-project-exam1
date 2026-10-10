/** 展示层格式化与状态映射（与后端约定一致）。 */

export const AVATAR_COLORS = ['#059669','#0891b2','#7c3aed','#db2777','#ea580c','#2563eb','#0d9488','#ca8a04']

export function avatarColor(name) {
  if (!name) return AVATAR_COLORS[0]
  let h = 0
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 997
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}

/**
 * 分类配色：内置分类固定配色，管理员新增的分类按名称哈希稳定取色，
 * 保证同一分类在不同页面颜色一致。
 */
const CATEGORY_STYLE = {
  '教材':   { icon: 'book',   chip: 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-200/70 dark:border-blue-500/20', bg: 'bg-blue-50 dark:bg-blue-500/10', fg: 'text-blue-600', bar: 'bg-blue-500' },
  '考研':   { icon: 'pencil', chip: 'bg-violet-50 dark:bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-200/70 dark:border-violet-500/20', bg: 'bg-violet-50 dark:bg-violet-500/10', fg: 'text-violet-600', bar: 'bg-violet-500' },
  '生活品': { icon: 'sofa',   chip: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200/70 dark:border-amber-500/20', bg: 'bg-amber-50 dark:bg-amber-500/10', fg: 'text-amber-600', bar: 'bg-amber-500' },
  '其它':   { icon: 'box',    chip: 'bg-slate-100 dark:bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-200/70 dark:border-slate-500/20', bg: 'bg-slate-100 dark:bg-slate-500/10', fg: 'text-slate-500', bar: 'bg-slate-400' },
}

const PALETTE = [
  { chip: 'bg-teal-50 dark:bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-200/70 dark:border-teal-500/20', bg: 'bg-teal-50 dark:bg-teal-500/10', fg: 'text-teal-600', bar: 'bg-teal-500' },
  { chip: 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200/70 dark:border-rose-500/20', bg: 'bg-rose-50 dark:bg-rose-500/10', fg: 'text-rose-600', bar: 'bg-rose-500' },
  { chip: 'bg-cyan-50 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-200/70 dark:border-cyan-500/20', bg: 'bg-cyan-50 dark:bg-cyan-500/10', fg: 'text-cyan-600', bar: 'bg-cyan-500' },
  { chip: 'bg-lime-50 dark:bg-lime-500/10 text-lime-700 dark:text-lime-300 border-lime-200/70 dark:border-lime-500/20', bg: 'bg-lime-50 dark:bg-lime-500/10', fg: 'text-lime-600', bar: 'bg-lime-500' },
  { chip: 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border-indigo-200/70 dark:border-indigo-500/20', bg: 'bg-indigo-50 dark:bg-indigo-500/10', fg: 'text-indigo-600', bar: 'bg-indigo-500' },
  { chip: 'bg-fuchsia-50 dark:bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300 border-fuchsia-200/70 dark:border-fuchsia-500/20', bg: 'bg-fuchsia-50 dark:bg-fuchsia-500/10', fg: 'text-fuchsia-600', bar: 'bg-fuchsia-500' },
]

function hashIndex(str, mod) {
  let h = 0
  for (const ch of String(str)) h = (h * 31 + ch.charCodeAt(0)) % 997
  return h % mod
}

/** 由分类对象（含后端返回的 icon）解析出完整样式。 */
export function categoryStyle(cat) {
  const name = typeof cat === 'string' ? cat : cat?.name
  const builtin = CATEGORY_STYLE[name]
  if (builtin) return builtin
  const pal = PALETTE[hashIndex(name, PALETTE.length)]
  return { icon: (typeof cat === 'object' && cat?.icon) || 'box', ...pal }
}

export const catIcon = (c) => categoryStyle(c).icon
export const catChip = (c) => categoryStyle(c).chip
export const catBg = (c) => categoryStyle(c).bg
export const catFg = (c) => categoryStyle(c).fg
export const catBar = (c) => categoryStyle(c).bar

/** 物品分类配色：优先按分类表配置的图标。 */
export function itemCatIcon(item, categories = []) {
  const found = categories.find(c => c.name === item?.category)
  return found ? found.icon || 'box' : catIcon(item?.category)
}

export const carbonOf = (category, categories = []) => {
  const found = categories.find(c => c.name === category)
  return found ? found.carbon_factor : 2.0
}

const REVIEW_STATUS = {
  approved: { label: '已通过', cls: 'bg-brand-100 dark:bg-brand-400/15 text-brand-700 dark:text-brand-300' },
  pending:  { label: '待审核', cls: 'bg-amber-100 dark:bg-amber-400/15 text-amber-700 dark:text-amber-300' },
  rejected: { label: '已驳回', cls: 'bg-red-100 dark:bg-red-400/15 text-red-600' },
}
export const reviewLabel = (s) => (REVIEW_STATUS[s] || {}).label || s
export const reviewChip = (s) => (REVIEW_STATUS[s] || REVIEW_STATUS.approved).cls

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

