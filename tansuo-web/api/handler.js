// Vercel Edge Functions - 薄路由层(纯路径匹配)
// 业务逻辑在 api/lib/ 下各模块
export const config = { runtime: 'edge' }

import { d1Query, d1RawFetch, d1Execute, d1Batch, ensureUsersTable, getCreds } from './lib/d1.js'
import { hashPassword, signSession, verifySession, parseCookie, setSessionCookie, SESSION_COOKIE, SESSION_TTL_SEC, getSessionSecret, hmacSign } from './lib/auth.js'
import {
  listItems, listItemsByModule, upsertItem, upsertItems, deleteItem, clearItems,
  listMemos, upsertMemo, upsertMemos, deleteMemo, clearMemos
} from './lib/stores.js'

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

function corsOptions() {
  return new Response(null, { status: 204, headers: {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  }})
}

// ---------- Main handler ----------
export default async function handler(req) {
  const url = new URL(req.url)
  const pathname = url.pathname
  const method = req.method

  if (method === 'OPTIONS') return corsOptions()

  try {
    // /api/health
    if (pathname.endsWith('/api/health') && method === 'GET') {
      return handleHealth()
    }

    // /api/debug-users
    if (pathname.endsWith('/api/debug-users') && method === 'GET') {
      return handleDebugUsers(req)
    }

    // /api/login
    if (pathname.endsWith('/api/login') && method === 'POST') {
      return handleLogin(req)
    }

    // /api/me
    if (pathname.endsWith('/api/me') && method === 'GET') {
      return handleMe(req)
    }

    // /api/logout
    if (pathname.endsWith('/api/logout') && method === 'POST') {
      return handleLogout()
    }

    // /api/items/raw
    if (pathname.match(/^\/api\/items\/raw$/)) {
      return handleItemsRaw()
    }

    // /api/items/module/:key
    const mModule = pathname.match(/^\/api\/items\/module\/(.+)$/)
    if (mModule && method === 'GET') {
      return json(await listItemsByModule(decodeURIComponent(mModule[1])))
    }

    // /api/items/clear
    if (pathname.match(/^\/api\/items\/clear$/) && method === 'POST') {
      await clearItems()
      return json({ ok: true })
    }

    // /api/items(批量 GET/POST)
    if (pathname.match(/^\/api\/items\/?$/) && (method === 'GET' || method === 'POST')) {
      if (method === 'GET') return json(await listItems())
      const body = await req.json().catch(() => null)
      if (!body) return json({ error: 'invalid json' }, 400)
      const rows = Array.isArray(body) ? body : [body]
      await upsertItems(rows)
      return json({ ok: true, count: rows.length })
    }

    // /api/items/:id
    const mItemId = pathname.match(/^\/api\/items\/(.+)$/)
    if (mItemId) return handleItemById(req, method, decodeURIComponent(mItemId[1]))

    // /api/memos(批量 GET/POST)
    if (pathname.match(/^\/api\/memos\/?$/) && (method === 'GET' || method === 'POST')) {
      if (method === 'GET') {
        const rows = await listMemos()
        return json(rows.map(r => ({ ...r, pinned: !!r.pinned, done: !!r.done })))
      }
      const body = await req.json().catch(() => null)
      if (!body) return json({ error: 'invalid json' }, 400)
      const rows = Array.isArray(body) ? body : [body]
      await upsertMemos(rows)
      return json({ ok: true, count: rows.length })
    }

    // /api/memos/clear
    if (pathname.match(/^\/api\/memos\/clear$/) && method === 'POST') {
      await clearMemos()
      return json({ ok: true })
    }

    // /api/memos/:id
    const mMemoId = pathname.match(/^\/api\/memos\/(.+)$/)
    if (mMemoId) return handleMemoById(req, method, decodeURIComponent(mMemoId[1]))

    // /api/migrate
    if (pathname.match(/^\/api\/migrate$/) && method === 'POST') {
      return handleMigrate(req, false)
    }

    // /api/import-append
    if (pathname.match(/^\/api\/import-append$/) && method === 'POST') {
      return handleMigrate(req, true)
    }

    return json({ error: `no route for ${method} ${pathname}` }, 404)
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

// ---------- Route handlers ----------

async function handleHealth() {
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

async function handleDebugUsers(req) {
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
        debug.sigLen = sig.length
        debug.expectedSig = await hmacSign(payload)
        debug.payloadParsed = JSON.parse(payload)
      } catch (e) {
        debug.decodeError = String(e.message || e)
      }
      debug.verifySessionResult = await verifySession(sid)
    }

    debug.usersInD1 = allUsers
    return new Response(JSON.stringify(debug, null, 2), { headers: { 'Content-Type': 'application/json' } })
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e.message || e) }, null, 2), { status: 500, headers: { 'Content-Type': 'application/json' } })
  }
}

async function handleLogin(req) {
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
  const sid = await signSession(user.username, user.role)
  const headers = new Headers({ 'Content-Type': 'application/json' })
  setSessionCookie(headers, sid, SESSION_TTL_SEC)
  return new Response(JSON.stringify({ ok: true, username: user.username, role: user.role }), { headers })
}

async function handleMe(req) {
  const cookie = parseCookie(req.headers.get('cookie'))
  const sess = verifySession(cookie[SESSION_COOKIE])
  if (!sess) {
    return new Response(JSON.stringify({ ok: false, error: '未登录' }), { status: 401, headers: { 'Content-Type': 'application/json' } })
  }
  return new Response(JSON.stringify({ ok: true, username: sess.username, role: sess.role }), { headers: { 'Content-Type': 'application/json' } })
}

function handleLogout() {
  const headers = new Headers({ 'Content-Type': 'application/json' })
  setSessionCookie(headers, '', 0)
  return new Response(JSON.stringify({ ok: true }), { headers })
}

async function handleItemsRaw() {
  try {
    const raw = await d1RawFetch('/query', { sql: 'SELECT * FROM items ORDER BY module_key, id', params: [] })
    return json(raw)
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

async function handleItemById(req, method, id) {
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
  return json({ error: `method ${method} not allowed` }, 405)
}

async function handleMemoById(req, method, id) {
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
  return json({ error: `method ${method} not allowed` }, 405)
}

async function handleMigrate(req, isAppend) {
  const body = await req.json().catch(() => null)
  if (!body) return json({ error: 'invalid json' }, 400)

  if (!isAppend) {
    await clearItems()
    await clearMemos()
  }

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
