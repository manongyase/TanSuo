import { listItems, listItemsByModule, upsertItems, upsertItem, deleteItem, clearItems } from '../../lib/d1-client.js'

function json(res, status = 200) {
  return Response.json(res, { status })
}

export async function GET(request, { params }) {
  try {
    const url = new URL(request.url)
    // /api/items/module/:key
    const m = url.pathname.match(/\/api\/items\/module\/([^/]+)$/)
    if (m) {
      const rows = await listItemsByModule(decodeURIComponent(m[1]))
      return json(rows)
    }
    // /api/items/:id → 返回单条
    const m2 = url.pathname.match(/\/api\/items\/([^/]+)$/)
    if (m2 && !url.pathname.endsWith('/clear')) {
      const rows = await listItems()
      const row = rows.find(r => r.id === decodeURIComponent(m2[1]))
      return row ? json(row) : json({ error: 'not found' }, 404)
    }
    // /api/items → 全部
    const rows = await listItems()
    return json(rows)
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function POST(request) {
  try {
    const url = new URL(request.url)
    // /api/items/clear
    if (url.pathname.endsWith('/clear')) {
      await clearItems()
      return json({ ok: true })
    }
    // /api/items → 批量 upsert
    const body = await request.json().catch(() => null)
    if (!body) return json({ error: 'invalid json' }, 400)
    const rows = Array.isArray(body) ? body : [body]
    await upsertItems(rows)
    return json({ ok: true, count: rows.length })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function PUT(request, { params }) {
  try {
    const url = new URL(request.url)
    const m = url.pathname.match(/\/api\/items\/([^/]+)$/)
    if (!m) return json({ error: 'bad path' }, 404)
    const id = decodeURIComponent(m[1])
    const body = await request.json().catch(() => null)
    if (!body) return json({ error: 'invalid json' }, 400)
    body.id = id
    await upsertItem(body)
    return json({ ok: true })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function DELETE(request) {
  try {
    const url = new URL(request.url)
    const m = url.pathname.match(/\/api\/items\/([^/]+)$/)
    if (!m) return json({ error: 'bad path' }, 404)
    await deleteItem(decodeURIComponent(m[1]))
    return json({ ok: true })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 204, headers: {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  }})
}
