// D1 REST API 客户端 - Edge Runtime 原生 fetch 支持
const BASE = 'https://api.cloudflare.com/client/v4'

let _usersInited = false

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

async function d1Query(sql, params = []) {
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

async function d1RawFetch(path, body) {
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
  return await res.json().catch(() => ({ raw: 'parse failed', status: res.status, statusText: res.statusText }))
}

async function d1QueryScalar(sql, params = []) {
  const rows = await d1Query(sql, params)
  if (!rows.length) return null
  const first = rows[0]
  const keys = Object.keys(first)
  return keys.length ? first[keys[0]] : null
}

async function d1Execute(sql, params = []) {
  // Cloudflare D1 REST API 只有 /query 端点(不存在 /execute)
  await d1Fetch('/query', { sql, params })
}

async function d1Batch(commands) {
  // Cloudflare D1 REST API 批量格式: { batch: [{ sql, params }] }
  await d1Fetch('/query', {
    batch: commands.map(c => ({ sql: c.sql, params: c.params || [] }))
  })
}

async function ensureUsersTable() {
  if (_usersInited) return
  await d1Execute(`
    CREATE TABLE IF NOT EXISTS users (
      username TEXT PRIMARY KEY,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'viewer',
      created_at TEXT DEFAULT (datetime('now'))
    )
  `)
  // 只在 users 表完全空时插种子用户(幂等)
  const rows = await d1Query('SELECT COUNT(*) AS c FROM users')
  if (!rows.length || rows[0].c === 0) {
    const adminHash = await import('./auth.js').then(m => m.hashPassword('宇宙之疯牛倜傥'))
    const xwHash = await import('./auth.js').then(m => m.hashPassword('张文秀'))
    await d1Batch([
      { sql: 'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', params: ['admin', adminHash, 'admin'] },
      { sql: 'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', params: ['张文秀', xwHash, 'viewer'] }
    ])
  }
  _usersInited = true
}

export {
  getCreds, d1Fetch, d1Query, d1RawFetch, d1QueryScalar, d1Execute, d1Batch, ensureUsersTable
}
