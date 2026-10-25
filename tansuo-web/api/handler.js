// Vercel Edge Functions - 统一 API Handler
// Vite 项目在 Vercel 上用 Edge Runtime，需要 export default 一个 fetch handler

export const config = { runtime: 'edge' }

// 惰性加载 D1 客户端（Edge Runtime 需要用 ESM，且 fetch 是全局的）
// 但 Cloudflare D1 用的是 fetch API，Edge Runtime 原生支持

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

// ---------- 鉴权相关 ----------
const SESSION_COOKIE = 'tansuo_session'
const SESSION_TTL_SEC = 3 * 24 * 60 * 60  // 3 天

// Edge Runtime 原生 crypto.subtle
async function hashPassword(pw) {
  const buf = new TextEncoder().encode(pw)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('')
}

// Edge Runtime 无状态:cookie 存 base64(JSON + 过期) + HMAC-SHA256 签名
// 用 CLOUDFLARE_API_TOKEN 当密钥(够长、够随机)
function getSessionSecret() {
  return process.env.SESSION_SECRET || process.env.CLOUDFLARE_API_TOKEN || 'dev-secret-change-me'
}

async function hmacSign(data) {
  const enc = new TextEncoder()
  const key = await crypto.subtle.importKey(
    'raw', enc.encode(getSessionSecret()),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  )
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(data))
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('')
}

async function hmacVerify(data, sig) {
  const expected = await hmacSign(data)
  const a = expected.toLowerCase(), b = sig.toLowerCase()
  if (a.length !== b.length) return false
  let v = 0
  for (let i = 0; i < a.length; i++) v |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return v === 0
}

async function signSession(username, role) {
  const expireAt = Math.floor(Date.now() / 1000) + SESSION_TTL_SEC
  const payload = JSON.stringify({ u: username, r: role, e: expireAt })
  const sig = await hmacSign(payload)
  return btoa(payload + '.' + sig)
}

async function verifySession(sid) {
  if (!sid) return null
  try {
    const decoded = atob(sid)
    const [payload, sig] = decoded.split('.')
    if (!payload || !sig) return null
    if (!await hmacVerify(payload, sig)) return null
    const obj = JSON.parse(payload)
    if (!obj.u || !obj.r || !obj.e) return null
    if (Math.floor(Date.now() / 1000) > obj.e) return null
    return { username: obj.u, role: obj.r }
  } catch { return null }
}

function parseCookie(header) {
  if (!header) return {}
  const out = {}
  header.split(';').forEach(p => {
    const eq = p.indexOf('=')
    if (eq < 1) return
    const k = p.slice(0, eq).trim()
    const v = p.slice(eq + 1).trim()
    // 浏览器发回的 Cookie 头已经自动 URL 解码过了,不要再 decode!
    if (k) out[k] = v
  })
  return out
}

function setSessionCookie(headers, sid, maxAgeSec) {
  const parts = [
    `${SESSION_COOKIE}=${encodeURIComponent(sid)}`,
    'Path=/',
    'SameSite=Lax'     // 同源登录场景 Lax 最稳,Chrome 不会拒存
  ]
  if (maxAgeSec > 0) parts.push(`Max-Age=${maxAgeSec}`)
  else parts.push('Max-Age=0')
  // Edge Response headers 用 append
  if (headers.append) headers.append('Set-Cookie', parts.join('; '))
  else headers['Set-Cookie'] = parts.join('; ')
}

// users 表是否已建 + 种子用户是否已插入
let usersInitialized = false
async function ensureUsersTable() {
  if (usersInitialized) return
  await d1Execute(`
    CREATE TABLE IF NOT EXISTS users (
      username TEXT PRIMARY KEY,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'viewer',
      created_at TEXT DEFAULT (datetime('now'))
    )
  `)
  // 只在 users 表完全空时插种子用户(幂等,只跑一次)
  const rows = await d1Query('SELECT COUNT(*) AS c FROM users')
  if (!rows.length || rows[0].c === 0) {
    const adminHash = await hashPassword('宇宙之疯牛倜傥')
    const xwHash = await hashPassword('张文秀')
    await d1Batch([
      { sql: 'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', params: ['admin', adminHash, 'admin'] },
      { sql: 'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', params: ['张文秀', xwHash, 'viewer'] }
    ])
  }
  usersInitialized = true
}

// 返回 D1 REST API 的完整原始响应（调试用）
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

// 查询单个标量值（如 SELECT COUNT(*)）
async function d1QueryScalar(sql, params = []) {
  const rows = await d1Query(sql, params)
  if (!rows.length) return null
  const first = rows[0]
  const keys = Object.keys(first)
  return keys.length ? first[keys[0]] : null
}

async function d1Execute(sql, params = []) {
  // Cloudflare D1 REST API 只有 /query 端点（不存在 /execute）
  await d1Fetch('/query', { sql, params })
}

async function d1Batch(commands) {
  // Cloudflare D1 REST API 批量格式: { batch: [{ sql, params }] }
  await d1Fetch('/query', {
    batch: commands.map(c => ({ sql: c.sql, params: c.params || [] }))
  })
}

// ---------- Items ----------
async function listItems() { return d1Query('SELECT * FROM items ORDER BY module_key, id') }
async function listItemsByModule(key) { return d1Query('SELECT * FROM items WHERE module_key = ? ORDER BY id', [key]) }

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

async function upsertItem(item) {
  const cols = ['id', 'module_key', 'title', 'tag', 'note', 'status', 'date', 'current', 'target', 'unit', 'deadline']
  const placeholders = cols.map(() => '?').join(', ')
  const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
  const sql = `INSERT INTO items (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
  const v = normalizeItem(item)
  return d1Execute(sql, cols.map(c => v[c]))
}

async function upsertItems(items) {
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

async function deleteItem(id) { return d1Execute('DELETE FROM items WHERE id = ?', [id]) }
async function clearItems() { return d1Execute('DELETE FROM items') }

// ---------- Memos ----------
async function listMemos() { return d1Query('SELECT * FROM memos ORDER BY pinned DESC, id') }

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

async function upsertMemo(memo) {
  const cols = ['id', 'title', 'note', 'due', 'pinned', 'done']
  const placeholders = cols.map(() => '?').join(', ')
  const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
  const sql = `INSERT INTO memos (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
  const v = normalizeMemo(memo)
  return d1Execute(sql, cols.map(c => v[c]))
}

async function upsertMemos(memos) {
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

async function deleteMemo(id) { return d1Execute('DELETE FROM memos WHERE id = ?', [id]) }
async function clearMemos() { return d1Execute('DELETE FROM memos') }

// ---------- Response helpers ----------
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  })
}

// ---------- Main handler ----------
export default async function handler(req) {
  const url = new URL(req.url)
  const pathname = url.pathname
  const method = req.method

  // CORS preflight
  if (method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }})
  }

  try {
    // /api/health — 真做一次 DB 查询测试
    if (pathname.endsWith('/api/health')) {
      if (method === 'GET') {
        const hasCreds = !!(process.env.CLOUDFLARE_ACCOUNT_ID && process.env.CLOUDFLARE_D1_DATABASE_ID && process.env.CLOUDFLARE_API_TOKEN)
        const info = {
          ok: true,
          db: hasCreds ? 'Cloudflare D1 (remote)' : 'missing env vars',
          env: process.env.NODE_ENV || 'development',
          runtime: 'edge',
          accountId: process.env.CLOUDFLARE_ACCOUNT_ID ? process.env.CLOUDFLARE_ACCOUNT_ID.slice(0, 4) + '...' : null,
          dbId: process.env.CLOUDFLARE_D1_DATABASE_ID ? process.env.CLOUDFLARE_D1_DATABASE_ID.slice(0, 8) + '...' : null,
          token: process.env.CLOUDFLARE_API_TOKEN ? 'present (' + process.env.CLOUDFLARE_API_TOKEN.length + ' chars)' : null
        }
        if (hasCreds) {
          try {
            await ensureUsersTable()
            info.usersInited = true
          } catch (e) {
            info.usersInited = false
            info.usersInitError = String(e.message || e)
          }
        }
        return new Response(JSON.stringify(info), { headers: { 'Content-Type': 'application/json' } })
      }
    }

    // /api/debug-users — 调试:把 cookie 解析全过程每一步都吐出来
    if (pathname.endsWith('/api/debug-users') && method === 'GET') {
      try {
        await ensureUsersTable()
        const allUsers = await d1Query('SELECT username, role FROM users ORDER BY username')
        const rawCookieHeader = req.headers.get('cookie')
        const cookie = parseCookie(rawCookieHeader)
        const sid = cookie[SESSION_COOKIE] || null

        const debug = {
          cookieHeaderRaw: rawCookieHeader,
          cookieParsedKeys: Object.keys(cookie),
          sidRaw: sid,
          secretLen: getSessionSecret().length,
          secretPrefix: getSessionSecret().slice(0, 4) + '...'
        }

        if (sid) {
          try {
            const decoded = atob(sid)
            const dotIdx = decoded.lastIndexOf('.')
            const payload = decoded.slice(0, dotIdx)
            const sig = decoded.slice(dotIdx + 1)
            debug.decoded = decoded
            debug.dotIdx = dotIdx
            debug.payload = payload
            debug.sig = sig
            debug.sigLen = sig.length
            debug.expectedSig = await hmacSign(payload)
            debug.sigsMatch = (await hmacSign(payload)) === sig
            debug.payloadParsed = JSON.parse(payload)
          } catch (e) {
            debug.decodeError = String(e.message || e)
          }
          debug.verifySessionResult = await verifySession(sid)
        }

        debug.usersInD1 = allUsers

        return new Response(JSON.stringify(debug, null, 2), { headers: { 'Content-Type': 'application/json' } })
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e.message || e), stack: e.stack }, null, 2), { status: 500, headers: { 'Content-Type': 'application/json' } })
      }
    }

    // /api/login — 登录(D1 查 users 表)
    if (pathname.endsWith('/api/login') && method === 'POST') {
      await ensureUsersTable()
      const body = await req.json()
      const u = String(body.username || '').trim()
      const p = String(body.password || '')
      const hash = await hashPassword(p)
      const rows = await d1Query(
        'SELECT username, role FROM users WHERE username = ? AND password_hash = ?',
        [u, hash]
      )
      if (!rows.length) {
        return new Response(JSON.stringify({ ok: false, error: '用户名或密码不对' }), { status: 401, headers: { 'Content-Type': 'application/json' } })
      }
      const user = rows[0]
      // Edge Runtime session 用 cookie,但没有内存存储(Vercel Edge 无状态)
      // 简化:cookie 里存直接用户信息 + 过期时间,用签名校验
      const sid = await signSession(user.username, user.role)
      const headers = new Headers({ 'Content-Type': 'application/json' })
      setSessionCookie(headers, sid, SESSION_TTL_SEC)
      return new Response(JSON.stringify({ ok: true, username: user.username, role: user.role }), { headers })
    }

    // /api/me — 验证登录状态
    if (pathname.endsWith('/api/me') && method === 'GET') {
      const cookie = parseCookie(req.headers.get('cookie'))
      const sess = verifySession(cookie[SESSION_COOKIE])
      if (!sess) {
        return new Response(JSON.stringify({ ok: false, error: '未登录' }), { status: 401, headers: { 'Content-Type': 'application/json' } })
      }
      return new Response(JSON.stringify({ ok: true, username: sess.username, role: sess.role }), { headers: { 'Content-Type': 'application/json' } })
    }

    // /api/logout — 登出
    if (pathname.endsWith('/api/logout') && method === 'POST') {
      const headers = new Headers({ 'Content-Type': 'application/json' })
      setSessionCookie(headers, '', 0)
      return new Response(JSON.stringify({ ok: true }), { headers })
    }

    // /api/items/raw — 返回 D1 REST API 原始响应（调试用）
    if (pathname.match(/^\/api\/items\/raw$/)) {
      if (method === 'GET') {
        try {
          const raw = await d1RawFetch('/query', { sql: 'SELECT * FROM items ORDER BY module_key, id', params: [] })
          return json(raw)
        } catch (e) {
          return json({ error: String(e.message || e) }, 500)
        }
      }
    }

    // /api/items
    if (pathname.match(/^\/api\/items\/?$/)) {
      if (method === 'GET') {
        const rows = await listItems()
        return json(rows)
      }
      if (method === 'POST') {
        const body = await req.json().catch(() => null)
        if (!body) return json({ error: 'invalid json' }, 400)
        const rows = Array.isArray(body) ? body : [body]
        await upsertItems(rows)
        return json({ ok: true, count: rows.length })
      }
    }

    // /api/items/module/:key
    const mModule = pathname.match(/^\/api\/items\/module\/(.+)$/)
    if (mModule && method === 'GET') {
      const rows = await listItemsByModule(decodeURIComponent(mModule[1]))
      return json(rows)
    }

    // /api/items/clear
    if (pathname.match(/^\/api\/items\/clear$/)) {
      if (method === 'POST') {
        await clearItems()
        return json({ ok: true })
      }
    }

    // /api/items/:id
    const mItemId = pathname.match(/^\/api\/items\/(.+)$/)
    if (mItemId) {
      const id = decodeURIComponent(mItemId[1])
      if (method === 'GET') {
        const rows = await listItems()
        const row = rows.find(r => r.id === id)
        return row ? json(row) : json({ error: 'not found' }, 404)
      }
      if (method === 'PUT') {
        const body = await req.json().catch(() => null)
        if (!body) return json({ error: 'invalid json' }, 400)
        body.id = id
        await upsertItem(body)
        return json({ ok: true })
      }
      if (method === 'DELETE') {
        await deleteItem(id)
        return json({ ok: true })
      }
    }

    // /api/memos
    if (pathname.match(/^\/api\/memos\/?$/)) {
      if (method === 'GET') {
        const rows = await listMemos()
        return json(rows.map(r => ({ ...r, pinned: !!r.pinned, done: !!r.done })))
      }
      if (method === 'POST') {
        const body = await req.json().catch(() => null)
        if (!body) return json({ error: 'invalid json' }, 400)
        const rows = Array.isArray(body) ? body : [body]
        await upsertMemos(rows)
        return json({ ok: true, count: rows.length })
      }
    }

    // /api/memos/clear
    if (pathname.match(/^\/api\/memos\/clear$/)) {
      if (method === 'POST') {
        await clearMemos()
        return json({ ok: true })
      }
    }

    // /api/memos/:id
    const mMemoId = pathname.match(/^\/api\/memos\/(.+)$/)
    if (mMemoId) {
      const id = decodeURIComponent(mMemoId[1])
      if (method === 'PUT') {
        const body = await req.json().catch(() => null)
        if (!body) return json({ error: 'invalid json' }, 400)
        body.id = id
        await upsertMemo(body)
        return json({ ok: true })
      }
      if (method === 'DELETE') {
        await deleteMemo(id)
        return json({ ok: true })
      }
    }

    // /api/migrate
    if (pathname.match(/^\/api\/migrate$/)) {
      if (method === 'POST') {
        const body = await req.json().catch(() => null)
        if (!body) return json({ error: 'invalid json' }, 400)
        const itemsByModule = body.itemsByModule || {}
        const memos = body.memos || []
        await clearItems()
        await clearMemos()
        const allItems = []
        for (const [key, list] of Object.entries(itemsByModule)) {
          for (const it of list) {
            allItems.push({ ...it, module_key: key })
          }
        }
        if (allItems.length) await upsertItems(allItems)
        if (memos.length) await upsertMemos(memos)
        return json({ ok: true, items: allItems.length, memos: memos.length })
      }
    }

    // /api/import-append
    if (pathname.match(/^\/api\/import-append$/)) {
      if (method === 'POST') {
        const body = await req.json().catch(() => null)
        if (!body) return json({ error: 'invalid json' }, 400)
        const itemsByModule = body.itemsByModule || {}
        const memos = body.memos || []
        const allItems = []
        for (const [key, list] of Object.entries(itemsByModule)) {
          for (const it of list) {
            allItems.push({ ...it, module_key: key })
          }
        }
        if (allItems.length) await upsertItems(allItems)
        if (memos.length) await upsertMemos(memos)
        return json({ ok: true, items: allItems.length, memos: memos.length })
      }
    }

    return json({ error: `no route for ${method} ${pathname}` }, 404)
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}
