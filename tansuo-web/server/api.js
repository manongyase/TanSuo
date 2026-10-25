// Vite dev server 里挂的 REST 接口。
// 跟前端同源（都在 5173），不用 CORS，直接 fetch('/api/...') 就行。

import {
  listItems,
  listItemsByModule,
  upsertItem,
  upsertItems,
  deleteItem,
  listMemos,
  upsertMemo,
  upsertMemos,
  deleteMemo,
  clearMemos,
  clearItems,
  DB_FILE,
  login as dbLogin,
  getUser
} from './db.js'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Credentials': 'true'
}

const SESSION_COOKIE = 'tansuo_session'
const SESSION_TTL_MS = 3 * 24 * 60 * 60 * 1000  // 3 天
const sessions = new Map()  // sessionId → { username, role, expireAt }

function makeSession(user) {
  const id = Math.random().toString(36).slice(2, 10) + Date.now().toString(36)
  sessions.set(id, { username: user.username, role: user.role, expireAt: Date.now() + SESSION_TTL_MS })
  return id
}

function checkSession(req) {
  const cookie = parseCookie(req.headers.cookie || '')
  const sess = sessions.get(cookie[SESSION_COOKIE])
  if (!sess) return null
  if (sess.expireAt < Date.now()) {
    sessions.delete(cookie[SESSION_COOKIE])
    return null
  }
  return { username: sess.username, role: sess.role }
}

function parseCookie(header) {
  const out = {}
  header.split(';').forEach(p => {
    const [k, v] = p.trim().split('=')
    if (k) out[k] = decodeURIComponent(v || '')
  })
  return out
}

function send(res, code, obj) {
  res.statusCode = code
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  Object.assign(res, CORS)
  res.end(JSON.stringify(obj))
}

function sendText(res, code, text) {
  res.statusCode = code
  res.setHeader('Content-Type', 'text/plain; charset=utf-8')
  Object.assign(res, CORS)
  res.end(text)
}

async function readBody(req) {
  const chunks = []
  for await (const c of req) chunks.push(c)
  const raw = Buffer.concat(chunks).toString('utf-8')
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch (e) {
    return null
  }
}

export async function registerApi(server) {
  server.middlewares.use(async (req, res, next) => {
    // CORS preflight
    if (req.method === 'OPTIONS') {
      send(res, 204, null)
      return
    }

    const url = new URL(req.url, 'http://localhost')
    const p = url.pathname

    // ---------- /api/health ----------
    if (p === '/api/health' && req.method === 'GET') {
      return send(res, 200, { ok: true, db: DB_FILE })
    }

    // ---------- /api/login ----------
    if (p === '/api/login' && req.method === 'POST') {
      try {
        const body = await readBody(req)
        if (!body) return send(res, 400, { error: 'invalid json' })
        const u = String(body.username || '').trim()
        const p = String(body.password || '')
        const user = dbLogin(u, p)
        if (!user) return send(res, 401, { error: '用户名或密码不对' })
        const sid = makeSession(user)
        setCookie(res, SESSION_COOKIE, sid, SESSION_TTL_MS)
        return send(res, 200, { ok: true, username: user.username, role: user.role })
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/me ----------
    if (p === '/api/me' && req.method === 'GET') {
      const user = checkSession(req)
      if (!user) return send(res, 401, { error: '未登录' })
      return send(res, 200, { ok: true, username: user.username, role: user.role })
    }

    // ---------- /api/logout ----------
    if (p === '/api/logout' && req.method === 'POST') {
      const cookie = parseCookie(req.headers.cookie || '')
      sessions.delete(cookie[SESSION_COOKIE])
      setCookie(res, SESSION_COOKIE, '', 0)
      return send(res, 200, { ok: true })
    }

    // ---------- 鉴权辅助:写操作需要 admin ----------
    function requireAdmin(req) {
      const u = checkSession(req)
      if (!u) return { ok: false, code: 401, msg: '未登录' }
      if (u.role !== 'admin') return { ok: false, code: 403, msg: '没有权限' }
      return { ok: true, user: u }
    }

    // ---------- /api/items/clear ----------
    if (p === '/api/items/clear' && req.method === 'POST') {
      try {
        clearItems()
        return send(res, 200, { ok: true })
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/items ----------
    if (p === '/api/items') {
      try {
        if (req.method === 'GET') {
          const rows = listItems()
          return send(res, 200, rows)
        }
        if (req.method === 'POST') {
          const body = await readBody(req)
          if (!body) return send(res, 400, { error: 'invalid json' })
          const rows = Array.isArray(body) ? body : [body]
          upsertItems(rows)
          return send(res, 200, { ok: true, count: rows.length })
        }
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/items/:id ----------
    let m = p.match(/^\/api\/items\/([^/]+)$/)
    if (m) {
      const id = decodeURIComponent(m[1])
      try {
        if (req.method === 'PUT' || req.method === 'POST') {
          const body = await readBody(req)
          if (!body) return send(res, 400, { error: 'invalid json' })
          body.id = id
          upsertItem(body)
          return send(res, 200, { ok: true })
        }
        if (req.method === 'DELETE') {
          deleteItem(id)
          return send(res, 200, { ok: true })
        }
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/items/module/:key ----------
    m = p.match(/^\/api\/items\/module\/([^/]+)$/)
    if (m && req.method === 'GET') {
      try {
        const rows = listItemsByModule(decodeURIComponent(m[1]))
        return send(res, 200, rows)
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/items/clear ----------
    if (p === '/api/items/clear' && req.method === 'POST') {
      try {
        clearItems()
        return send(res, 200, { ok: true })
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/memos/clear (必须在 /api/memos/:id 之前，否则 clear 会被当成 id) ----------
    if (p === '/api/memos/clear' && req.method === 'POST') {
      try {
        clearMemos()
        return send(res, 200, { ok: true })
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/memos ----------
    if (p === '/api/memos') {
      try {
        if (req.method === 'GET') {
          const rows = listMemos()
          return send(res, 200, rows.map(toMemoResp))
        }
        if (req.method === 'POST') {
          const body = await readBody(req)
          if (!body) return send(res, 400, { error: 'invalid json' })
          const rows = Array.isArray(body) ? body : [body]
          upsertMemos(rows)
          return send(res, 200, { ok: true, count: rows.length })
        }
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/memos/:id ----------
    m = p.match(/^\/api\/memos\/([^/]+)$/)
    if (m) {
      const id = decodeURIComponent(m[1])
      try {
        if (req.method === 'PUT' || req.method === 'POST') {
          const body = await readBody(req)
          if (!body) return send(res, 400, { error: 'invalid json' })
          body.id = id
          upsertMemo(body)
          return send(res, 200, { ok: true })
        }
        if (req.method === 'DELETE') {
          deleteMemo(id)
          return send(res, 200, { ok: true })
        }
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/migrate-from-storage ----------
    // 前端把 localStorage 的两个 key 直接 POST 过来，后端全量覆盖写入
    if (p === '/api/migrate' && req.method === 'POST') {
      try {
        const body = await readBody(req)
        if (!body) return send(res, 400, { error: 'invalid json' })
        const itemsByModule = body.itemsByModule || {}
        const memos = body.memos || []
        // 先清再写，保证幂等
        clearItems()
        clearMemos()
        const allItems = []
        for (const [key, list] of Object.entries(itemsByModule)) {
          for (const it of list) {
            allItems.push({ ...it, module_key: key })
          }
        }
        if (allItems.length) upsertItems(allItems)
        if (memos.length) upsertMemos(memos)
        return send(res, 200, {
          ok: true,
          items: allItems.length,
          memos: memos.length,
          db: DB_FILE
        })
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    // ---------- /api/import-append ----------
    // 追加导入（不覆盖已有）
    if (p === '/api/import-append' && req.method === 'POST') {
      try {
        const body = await readBody(req)
        if (!body) return send(res, 400, { error: 'invalid json' })
        const itemsByModule = body.itemsByModule || {}
        const memos = body.memos || []
        const allItems = []
        for (const [key, list] of Object.entries(itemsByModule)) {
          for (const it of list) {
            allItems.push({ ...it, module_key: key })
          }
        }
        if (allItems.length) upsertItems(allItems)
        if (memos.length) upsertMemos(memos)
        return send(res, 200, {
          ok: true,
          items: allItems.length,
          memos: memos.length,
          db: DB_FILE
        })
      } catch (e) {
        return send(res, 500, { error: String(e.message || e) })
      }
    }

    next()
  })
}

function toMemoResp(r) {
  return {
    ...r,
    pinned: !!r.pinned,
    done: !!r.done
  }
}

function setCookie(res, name, value, maxAgeMs) {
  const parts = [`${name}=${encodeURIComponent(value)}`]
  parts.push(`Path=/`)
  if (maxAgeMs > 0) parts.push(`Max-Age=${Math.floor(maxAgeMs / 1000)}`)
  else parts.push(`Max-Age=0`)
  res.setHeader('Set-Cookie', parts.join('; '))
}
