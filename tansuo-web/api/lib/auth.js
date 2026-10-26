// 鉴权模块 - Edge Runtime 无状态 HMAC cookie session
const SESSION_COOKIE = 'tansuo_session'
const SESSION_TTL_SEC = 3 * 24 * 60 * 60  // 3 天

async function hashPassword(pw) {
  const buf = new TextEncoder().encode(pw)
  const hash = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('')
}

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
    // 浏览器发回的 Cookie 头已经自动 URL 解码过了
    if (k) out[k] = v
  })
  return out
}

function setSessionCookie(headers, sid, maxAgeSec) {
  // base64 字符集本身就是 cookie-safe,不要 encodeURIComponent
  const parts = [
    `${SESSION_COOKIE}=${sid}`,
    'Path=/',
    'SameSite=Lax'
  ]
  if (maxAgeSec > 0) parts.push(`Max-Age=${maxAgeSec}`)
  else parts.push('Max-Age=0')
  const cookieValue = parts.join('; ')
  if (headers.append) headers.append('Set-Cookie', cookieValue)
  else if (headers instanceof Headers) headers.append('Set-Cookie', cookieValue)
  else headers['Set-Cookie'] = cookieValue
}

export {
  SESSION_COOKIE, SESSION_TTL_SEC,
  hashPassword, getSessionSecret, hmacSign, hmacVerify,
  signSession, verifySession, parseCookie, setSessionCookie
}
