import { upsertMemo, deleteMemo } from '../../../lib/d1-client.js'

function json(res, status = 200) { return Response.json(res, { status }) }

export async function PUT(request, { params }) {
  try {
    const id = decodeURIComponent(params.id)
    const body = await request.json().catch(() => null)
    if (!body) return json({ error: 'invalid json' }, 400)
    body.id = id
    await upsertMemo(body)
    return json({ ok: true })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function DELETE(request, { params }) {
  try {
    await deleteMemo(decodeURIComponent(params.id))
    return json({ ok: true })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 204 })
}
