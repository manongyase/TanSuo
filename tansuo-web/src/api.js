// 后端 API 封装。同源 fetch('/api/...')，Vite dev server 和 preview server 都挂载。

async function req(path, { method = 'GET', body } = {}) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(path, opts)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`HTTP ${res.status}: ${text}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export async function pingDb() {
  try {
    const data = await req('/api/health')
    return !!data.ok
  } catch {
    return false
  }
}

export async function fetchAllItems() {
  const rows = await req('/api/items')
  // 后端扁平存了 module_key，前端要按模块分桶
  const grouped = {}
  for (const r of rows) {
    const k = r.module_key
    if (!k) continue
    grouped[k] = grouped[k] || []
    grouped[k].push(stripDbItem(r))
  }
  return grouped
}

export async function fetchAllMemos() {
  const rows = await req('/api/memos')
  return rows.map(stripDbMemo)
}

export async function saveItem(item) {
  const moduleKey = item._moduleKey || detectModuleKey(item)
  const payload = { ...item, module_key: moduleKey }
  delete payload._moduleKey
  await req(`/api/items/${encodeURIComponent(item.id)}`, { method: 'PUT', body: payload })
}

export async function saveItems(items, moduleKey) {
  const payload = items.map((it) => ({ ...it, module_key: moduleKey }))
  await req('/api/items', { method: 'POST', body: payload })
}

export async function removeItem(id) {
  await req(`/api/items/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export async function saveMemo(memo) {
  await req(`/api/memos/${encodeURIComponent(memo.id)}`, { method: 'PUT', body: memo })
}

export async function saveMemos(memos) {
  await req('/api/memos', { method: 'POST', body: memos })
}

export async function removeMemo(id) {
  await req(`/api/memos/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

// 全量迁移：把 localStorage 里的两个 key 直接 POST 过去
export async function migrateFromLocalStorage({ itemsByModule, memos, mode = 'replace' }) {
  const url = mode === 'append' ? '/api/import-append' : '/api/migrate'
  return req(url, { method: 'POST', body: { itemsByModule, memos } })
}

function stripDbItem(r) {
  const o = {
    id: r.id,
    title: r.title,
    tag: r.tag,
    note: r.note,
    status: r.status || 'todo',
    date: r.date
  }
  if (typeof r.current === 'number') o.current = r.current
  if (typeof r.target === 'number') o.target = r.target
  if (r.unit) o.unit = r.unit
  if (r.deadline) o.deadline = r.deadline
  return o
}

function stripDbMemo(r) {
  return {
    id: r.id,
    title: r.title,
    note: r.note,
    due: r.due,
    pinned: !!r.pinned,
    done: !!r.done
  }
}

// 根据 item.id 的前缀推断模块 key（items 表里没 module_key 字段时兜底用）
function detectModuleKey(item) {
  const id = String(item.id || '')
  const m = id.match(/^([a-z]+)-/)
  return m ? m[1] : ''
}

export async function dbStats() {
  try {
    const items = await fetchAllItems()
    const memos = await fetchAllMemos()
    const health = await req('/api/health')
    return {
      ok: true,
      dbPath: health.db,
      totalItems: Object.values(items).reduce((a, b) => a + (b || []).length, 0),
      totalMemos: memos.length,
      items,
      memos
    }
  } catch (e) {
    return { ok: false, error: String(e.message || e) }
  }
}

export default {
  pingDb,
  fetchAllItems,
  fetchAllMemos,
  saveItem,
  saveItems,
  removeItem,
  saveMemo,
  saveMemos,
  removeMemo,
  migrateFromLocalStorage
}
