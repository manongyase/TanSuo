// Cloudflare D1 REST API 客户端
// Vercel Serverless 环境用 fetch 直接调 Cloudflare API
// 本地 dev 不走这个（用 server/db.js 的 better-sqlite3）

const BASE = 'https://api.cloudflare.com/client/v4'

function getCreds() {
  const accountId = process.env.CLOUDFLARE_ACCOUNT_ID
  const dbId = process.env.CLOUDFLARE_D1_DATABASE_ID
  const token = process.env.CLOUDFLARE_API_TOKEN
  if (!accountId || !dbId || !token) {
    throw new Error('缺少 Cloudflare 环境变量 (CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_D1_DATABASE_ID / CLOUDFLARE_API_TOKEN)')
  }
  return { accountId, dbId, token }
}

async function d1Fetch(path, body) {
  const { accountId, dbId, token } = getCreds()
  const url = `${BASE}/accounts/${accountId}/d1/database/${dbId}${path}`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || !json.success) {
    const msg = json?.errors?.[0]?.message || res.statusText || 'unknown'
    throw new Error(`D1 API error: ${msg}`)
  }
  return json.result
}

// 执行单条查询（SELECT），返回行数组
export async function d1Query(sql, params = []) {
  const result = await d1Fetch('/query', { sql, params })
  if (!result || !result.length) return []
  const first = result[0]
  // 新版格式: result[0].results 直接是对象数组
  if (first.results && Array.isArray(first.results)) {
    return first.results
  }
  // 旧版格式: result[0].columns + rows(二维数组)
  const { columns, rows } = first
  if (columns && rows) {
    return rows.map(row => {
      const obj = {}
      columns.forEach((col, i) => { obj[col] = row[i] })
      return obj
    })
  }
  return []
}

// 执行单条写操作（INSERT/UPDATE/DELETE）
export async function d1Execute(sql, params = []) {
  // Cloudflare D1 REST API 只有 /query 端点（不存在 /execute）
  await d1Fetch('/query', { sql, params })
}

// 批量执行多条命令
export async function d1Batch(commands) {
  // Cloudflare D1 REST API 批量格式: { batch: [{ sql, params }] }
  await d1Fetch('/query', {
    batch: commands.map(c => ({ sql: c.sql, params: c.params || [] }))
  })
}

// ---------- Items ----------
export async function listItems() {
  return d1Query('SELECT * FROM items ORDER BY module_key, id')
}

export async function listItemsByModule(moduleKey) {
  return d1Query('SELECT * FROM items WHERE module_key = ? ORDER BY id', [moduleKey])
}

export async function upsertItem(item) {
  const cols = ['id', 'module_key', 'title', 'tag', 'note', 'status', 'date', 'current', 'target', 'unit', 'deadline']
  const placeholders = cols.map(() => '?').join(', ')
  const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
  const sql = `INSERT INTO items (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
  const v = normalizeItem(item)
  return d1Execute(sql, cols.map(c => v[c]))
}

export async function upsertItems(items) {
  const cmds = items.map(it => {
    const cols = ['id', 'module_key', 'title', 'tag', 'note', 'status', 'date', 'current', 'target', 'unit', 'deadline']
    const placeholders = cols.map(() => '?').join(', ')
    const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
    const sql = `INSERT INTO items (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
    const v = normalizeItem(it)
    return { sql, params: cols.map(c => v[c]) }
  })
  return d1Batch(cmds)
}

export async function deleteItem(id) {
  return d1Execute('DELETE FROM items WHERE id = ?', [id])
}

export async function clearItems() {
  return d1Execute('DELETE FROM items')
}

// ---------- Memos ----------
export async function listMemos() {
  return d1Query('SELECT * FROM memos ORDER BY pinned DESC, id')
}

export async function upsertMemo(memo) {
  const cols = ['id', 'title', 'note', 'due', 'pinned', 'done']
  const placeholders = cols.map(() => '?').join(', ')
  const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
  const sql = `INSERT INTO memos (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
  const v = normalizeMemo(memo)
  return d1Execute(sql, cols.map(c => v[c]))
}

export async function upsertMemos(memos) {
  const cmds = memos.map(m => {
    const cols = ['id', 'title', 'note', 'due', 'pinned', 'done']
    const placeholders = cols.map(() => '?').join(', ')
    const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
    const sql = `INSERT INTO memos (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
    const v = normalizeMemo(m)
    return { sql, params: cols.map(c => v[c]) }
  })
  return d1Batch(cmds)
}

export async function deleteMemo(id) {
  return d1Execute('DELETE FROM memos WHERE id = ?', [id])
}

export async function clearMemos() {
  return d1Execute('DELETE FROM memos')
}

// ---------- helpers ----------
function normalizeItem(it) {
  return {
    id: String(it.id),
    module_key: String(it.module_key || ''),
    title: String(it.title || ''),
    tag: it.tag == null ? null : String(it.tag),
    note: it.note == null ? null : String(it.note),
    status: it.status == null ? 'todo' : String(it.status),
    date: it.date == null ? null : String(it.date),
    current: typeof it.current === 'number' ? it.current : null,
    target: typeof it.target === 'number' ? it.target : null,
    unit: it.unit == null ? null : String(it.unit),
    deadline: it.deadline == null ? null : String(it.deadline)
  }
}

function normalizeMemo(m) {
  return {
    id: String(m.id),
    title: String(m.title || ''),
    note: m.note == null ? null : String(m.note),
    due: m.due == null ? null : String(m.due),
    pinned: m.pinned ? 1 : 0,
    done: m.done ? 1 : 0
  }
}
