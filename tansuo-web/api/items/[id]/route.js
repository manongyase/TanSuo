import { listItems, listItemsByModule, upsertItems, upsertItem, deleteItem, clearItems } from '../../../lib/d1-client.js'

function json(res, status = 200) {
  return Response.json(res, { status })
}

// /api/items/[id] 动态路由（Vercel Route Handlers 用 [param] 语法）
export async function PUT(request, { params }) {
  try {
    const id = decodeURIComponent(params.id)
    const body = await request.json().catch(() => null)
    if (!body) return json({ error: 'invalid json' }, 400)
    body.id = id
    await upsertItem(body)
    return json({ ok: true })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function DELETE(request, { params }) {
  try {
    await deleteItem(decodeURIComponent(params.id))
    return json({ ok: true })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 204 })
}
