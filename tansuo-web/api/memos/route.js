import { listMemos, upsertMemos, upsertMemo, deleteMemo, clearMemos } from '../../lib/d1-client.js'

function json(res, status = 200) { return Response.json(res, { status }) }

export async function GET() {
  try {
    const rows = await listMemos()
    return json(rows.map(toMemoResp))
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function POST(request) {
  try {
    const body = await request.json().catch(() => null)
    if (!body) return json({ error: 'invalid json' }, 400)
    const rows = Array.isArray(body) ? body : [body]
    await upsertMemos(rows)
    return json({ ok: true, count: rows.length })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 204 })
}

function toMemoResp(r) {
  return { ...r, pinned: !!r.pinned, done: !!r.done }
}
