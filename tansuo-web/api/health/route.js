function json(res, status = 200) { return Response.json(res, { status }) }

export async function GET() {
  const hasCreds = !!(process.env.CLOUDFLARE_ACCOUNT_ID && process.env.CLOUDFLARE_D1_DATABASE_ID && process.env.CLOUDFLARE_API_TOKEN)
  return json({
    ok: true,
    db: hasCreds ? 'Cloudflare D1 (remote)' : 'local dev (better-sqlite3)',
    env: process.env.NODE_ENV || 'development'
  })
}

export async function OPTIONS() {
  return new Response(null, { status: 204 })
}
