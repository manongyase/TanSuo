import { upsertItems, upsertMemos, clearItems, clearMemos } from '../../../lib/d1-client.js'

function json(res, status = 200) { return Response.json(res, { status }) }

export async function POST(request) {
  try {
    const body = await request.json().catch(() => null)
    if (!body) return json({ error: 'invalid json' }, 400)
    const itemsByModule = body.itemsByModule || {}
    const memos = body.memos || []
    // 先清再写（全量迁移）
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
    return json({
      ok: true,
      items: allItems.length,
      memos: memos.length
    })
  } catch (e) {
    return json({ error: String(e.message || e) }, 500)
  }
}

export async function OPTIONS() {
  return new Response(null, { status: 204 })
}
