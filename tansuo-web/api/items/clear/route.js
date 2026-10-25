import { clearItems } from '../../../lib/d1-client.js'

function json(res, status = 200) { return Response.json(res, { status }) }

export async function POST() {
  try {
    await clearItems()
    return json({ ok: true })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 204 })
}
