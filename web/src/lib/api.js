/**
 * 统一的 API 客户端。
 * - 始终携带会话 Cookie（credentials: 'include'）
 * - 非 2xx 统一抛出带中文 detail 的 Error，便于上层直接提示
 * - 401 时抛出带 status 的错误，由路由守卫/调用方决定跳转登录
 */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, { method = 'GET', body, isForm } = {}) {
  const init = { method, credentials: 'include', headers: {} }
  if (body !== undefined) {
    if (isForm) {
      init.body = body
    } else {
      init.headers['Content-Type'] = 'application/json'
      init.body = JSON.stringify(body)
    }
  }
  let res
  try {
    res = await fetch(path, init)
  } catch {
    throw new ApiError('网络连接失败，请检查服务是否运行', 0)
  }
  let data = null
  const text = await res.text()
  if (text) {
    try { data = JSON.parse(text) } catch { data = text }
  }
  if (!res.ok) {
    if (res.status === 401 && !['/api/auth/login', '/api/auth/register'].includes(path)) {
      window.dispatchEvent(new Event('gc:session-expired'))
    }
    const msg = (data && data.detail) || `请求失败（${res.status}）`
    throw new ApiError(typeof msg === 'string' ? msg : '请求参数不合法', res.status)
  }
  return data
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: 'POST', body }),
  patch: (p, body) => request(p, { method: 'PATCH', body }),
  del: (p) => request(p, { method: 'DELETE' }),
}

/** 将图片文件等比压缩为 data URL，避免上传超大原图。 */
export function fileToCompressedDataURL(file, maxSize = 1280, quality = 0.85) {
  return new Promise((resolve, reject) => {
    if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(file.type)) {
      reject(new Error('请选择 PNG、JPG、WebP 或 GIF 图片'))
      return
    }
    if (file.size > 20 * 1024 * 1024) { reject(new Error('原图请小于 20MB')); return }
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('读取图片失败'))
    reader.onload = () => {
      const img = new Image()
      img.onerror = () => reject(new Error('图片解析失败'))
      img.onload = () => {
        let { width, height } = img
        const scale = Math.min(1, maxSize / Math.max(width, height))
        width = Math.round(width * scale)
        height = Math.round(height * scale)
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        canvas.getContext('2d').drawImage(img, 0, 0, width, height)
        const mime = file.type === 'image/png' ? 'image/png' : 'image/jpeg'
        const result = canvas.toDataURL(mime, quality)
        if (result.split(',')[1].length * 3 / 4 > 2 * 1024 * 1024) { reject(new Error('压缩后的图片仍超过 2MB，请选择较小的图片')); return }
        resolve(result)
      }
      img.src = reader.result
    }
    reader.readAsDataURL(file)
  })
}
