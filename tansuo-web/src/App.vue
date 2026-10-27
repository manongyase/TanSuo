<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshRight, Plus, Delete, Calendar, Bell, Star, Edit, WarningFilled, User, Lock, SwitchButton, Sunny, Moon, Setting, Expand, Fold } from '@element-plus/icons-vue'
import { MODULES, STATUS_MAP, STORAGE_KEY, MEMO_STORAGE_KEY, DEFAULT_MEMOS } from './modules'
import api, { pingDb, fetchAllItems, fetchAllMemos, saveItems, saveMemos, removeItem as removeItemFromApi, removeMemo as removeMemoFromApi, migrateFromLocalStorage, dbStats } from './api.js'

const NEXT_STATUS = { todo: 'doing', doing: 'done', done: 'todo' }

// ---------- 鉴权系统(纯前端 localStorage + 后端 login API) ----------
const AUTH_KEY = 'tansuo_auth'
const AUTH_TTL = 3 * 24 * 60 * 60 * 1000  // 3 天(ms)

const currentUser = ref(null)   // { username, role }
const authChecking = ref(true)

// 登录表单
const loginForm = ref({ username: '', password: '' })
const loginLoading = ref(false)

function checkAuth() {
  try {
    const raw = localStorage.getItem(AUTH_KEY)
    if (raw) {
      const obj = JSON.parse(raw)
      if (obj.username && obj.role && obj.expireAt && obj.expireAt > Date.now()) {
        currentUser.value = { username: obj.username, role: obj.role }
        authChecking.value = false
        return true
      }
    }
  } catch {}
  currentUser.value = null
  authChecking.value = false
  return false
}

async function doLogin() {
  loginLoading.value = true
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: loginForm.value.username.trim(), password: loginForm.value.password })
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      ElMessage.error(err.error || '登录失败')
      return
    }
    const data = await res.json()
    currentUser.value = { username: data.username, role: data.role }
    localStorage.setItem(AUTH_KEY, JSON.stringify({
      username: data.username, role: data.role,
      expireAt: Date.now() + AUTH_TTL
    }))
    ElMessage.success('登录成功')
    await initializeFromBackend()
    await refreshDbBar()
  } finally {
    loginLoading.value = false
  }
}

function doLogout() {
  localStorage.removeItem(AUTH_KEY)
  currentUser.value = null
  dbConnected.value = false
}

const canEdit = computed(() => currentUser.value?.role === 'admin')

function createInitial() {
  return Object.fromEntries(MODULES.map((m) => [m.key, m.items.map((i) => ({ ...i }))]))
}

// ---------- 初始化：先给默认值，再异步从后端拉 ----------
const store = ref(createInitial())
const memos = ref(DEFAULT_MEMOS.map((m) => ({ ...m })))
const dbConnected = ref(false)
const dbEmpty = ref(false)   // 后端有连接但 DB 是空的 → 可能需要从 localStorage 迁移

// UI 状态
const activeKey = ref(localStorage.getItem('tansuo_active') || MODULES[0].key)
const keyword = ref(localStorage.getItem('tansuo_keyword') || '')
const dialogVisible = ref(false)


const editingId = ref(null)
const form = ref({ title: '', tag: '', note: '', status: 'todo' })
const memoDrawer = ref(false)
const memoForm = ref({ title: '', note: '', due: null })

// 底栏状态
const checkingDb = ref(false)
const syncingDb = ref(false)
const totalItemsInDB = ref(0)
const totalMemosInDB = ref(0)
const dbPathShort = ref('')

// 迁移弹窗状态
const migrateDialog = ref(false)
const migrateState = ref({ itemsByModule: null, memos: null })

// ---------- 响应式：判断是否移动端 ----------
const isMobile = ref(false)
function setupBreakpoint() {
  const mql = window.matchMedia('(max-width: 860px)')
  const apply = () => { isMobile.value = mql.matches }
  apply()
  mql.addEventListener('change', apply)
  window.addEventListener('resize', apply)
}

// ---------- 明暗主题 ----------
const THEME_KEY = 'tansuo_theme'
const isDark = ref(localStorage.getItem(THEME_KEY) === 'dark')
const isDebugDrag = ref(false)
const toolbarOpen = ref(false) // 胶囊工具栏展开/收起,默认收起
function toggleDebugDrag() {
  isDebugDrag.value = !isDebugDrag.value
  document.body.classList.toggle('debug-drag', isDebugDrag.value)
  ElMessage({ message: isDebugDrag.value ? '🎨 调试拖拽 ON — 拖拽任意元素' : '调试拖拽 OFF', type: isDebugDrag.value ? 'info' : 'success' })
}
function applyTheme() {
  if (isDark.value) document.documentElement.classList.add('dark')
  else document.documentElement.classList.remove('dark')
}
function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light')
  applyTheme()
}
applyTheme()
watch(isDark, applyTheme)

onMounted(async () => {
  setupBreakpoint()
  enableDebugDrag() // Alt+D 切换调试拖拽模式
  // 鉴权:没登录或已过期,跳过数据初始化
  if (!checkAuth()) return
  await initializeFromBackend()
  await refreshDbBar()
})

// ---------- 调试拖拽模式 ----------
function enableDebugDrag() {
  let dragging = null
  let startX = 0, startY = 0, originLeft = 0, originTop = 0
  let tipEl = null

  function makeTip(x, y, text) {
    const d = document.createElement('div')
    d.className = 'dd-tip'
    d.style.cssText = `position:fixed;left:${x}px;top:${y}px;background:#333;color:#fff;padding:6px 10px;border-radius:6px;font:12px/1.4 -apple-system,sans-serif;z-index:99999;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,.3)`
    d.textContent = text
    document.body.appendChild(d)
    return d
  }

  function showResult(el, originL, originT) {
    const parent = el.parentElement
    const cs = getComputedStyle(parent)
    const flexDir = cs.flexDirection || 'row'
    const gap = parseInt(cs.gap) || 0
    const elRect = el.getBoundingClientRect()
    const prevSib = el.previousElementSibling
    const nextSib = el.nextElementSibling
    const dx = parseFloat(el.style.left) || 0
    const dy = parseFloat(el.style.top) || 0
    const info = {
      element: el.tagName + (el.className ? '.' + el.className.split(' ')[0] : ''),
      parent: parent.tagName + '.' + (parent.className || '').split(' ')[0],
      flexDirection: flexDir,
      gapHint: gap ? gap + 'px' : '0 (没设 gap)',
      self: {
        marginLeft: getComputedStyle(el).marginLeft,
        marginTop: getComputedStyle(el).marginTop,
        marginRight: getComputedStyle(el).marginRight,
        marginBottom: getComputedStyle(el).marginBottom,
        width: Math.round(elRect.width) + 'px',
        height: Math.round(elRect.height) + 'px',
      },
      prevGap: prevSib
        ? Math.round(elRect.left - prevSib.getBoundingClientRect().right) + 'px'
        : '(first)',
      nextGap: nextSib
        ? Math.round(nextSib.getBoundingClientRect().left - elRect.right) + 'px'
        : '(last)',
    }
    console.log('🎨 DebugDrag 结果:', info)
    ElMessageBox.confirm(
      `<pre style="font-size:12px;line-height:1.5;margin:0">📦 元素: <b>${info.element}</b>\n👨‍👩‍👧 父级: ${info.parent}\n🧭 排列: ${flexDir === 'row' ? '水平 ↔' : flexDir === 'column' ? '垂直 ↕' : flexDir}\n📏 父 gap: ${info.gapHint}\n⬅️ 左侧距前元素: ${info.prevGap}\n➡️ 右侧距后元素: ${info.nextGap}\n\n↔ 水平位移: <b>${dx}px</b> (改 left/margin-left)\n↕ 垂直位移: <b>${dy}px</b> (改 top/margin-top)\n\n📐 自身 CSS:\n  margin: ${info.self.marginTop} ${info.self.marginRight} ${info.self.marginBottom} ${info.self.marginLeft}\n  width:  ${info.self.width}\n  height: ${info.self.height}\n\n💡 建议:\n  如果多个元素要一起移 → 改 parent 的 gap/justify-content\n  如果只这个元素移 → 改它的 margin-left/top/bottom/right\n  对齐问题 → justify-content / align-items</pre>`,
      '🎯 拖拽完成 — 布局诊断',
      {
        dangerouslyUseHTMLString: true,
        confirmButtonText: '✅ 保持这个位置',
        cancelButtonText: '↩️ 还原回去',
        distinguishCancelAndClose: true,
        customClass: 'dd-result'
      }
    ).then(() => {
      // 用户选"保持" —— 不动元素,给个提示
      ElMessage.success('元素已停留在当前位置,看效果满意就去改 CSS 吧')
    }).catch((action) => {
      if (action === 'cancel') {
        // 用户点"还原" —— 恢复初始位置,清掉临时样式
        el.style.left = originL ? originL + 'px' : ''
        el.style.top = originT ? originT + 'px' : ''
        if (el.style.position === 'relative' && !originL && !originT) el.style.position = ''
        ElMessage.info('已还原到初始位置')
      }
    })
  }

  // Alt+D 快捷键
  document.addEventListener('keydown', (e) => {
    if (e.altKey && (e.key === 'd' || e.key === 'D')) {
      e.preventDefault()
      isDebugDrag.value = !isDebugDrag.value
      document.body.classList.toggle('debug-drag', isDebugDrag.value)
      ElMessage({
        message: isDebugDrag.value
          ? '🎨 调试拖拽 ON — 拖拽任意元素,松开会显示 gap/margin'
          : '调试拖拽 OFF',
        type: isDebugDrag.value ? 'info' : 'success',
        duration: 2500
      })
    }
  })

  // ✅ 核心修复:用 pointerdown + setPointerCapture 替代 mousedown
  // setPointerCapture 强制把所有后续 pointermove/up 事件都发给 target 元素,
  // 完全绕过 Element Plus 组件的事件拦截、文本选择、滚动等干扰
  document.addEventListener('pointerdown', (e) => {
    if (!document.body.classList.contains('debug-drag')) return
    if (e.button !== 0) return // 只处理左键

    const target = e.target.closest(
      'button, [class*="el-"], [class*="head-"], [class*="item-"], [class*="plan-"], [class*="mod-"], .toolbar, .stat, .db-dot, .mobile-tabs, .mtab, .topbar-user, .hero, .memo-drawer'
    )
    if (!target) return

    e.preventDefault()
    e.stopPropagation()

    dragging = target
    // 确保元素可以绝对定位
    const curPos = getComputedStyle(target).position
    if (curPos === 'static') target.style.position = 'relative'

    originLeft = parseFloat(target.style.left || target.offsetLeft) || 0
    originTop = parseFloat(target.style.top || target.offsetTop) || 0
    startX = e.clientX
    startY = e.clientY

    target.classList.add('dd-dragging')

    // 🎯 关键:捕获指针,后续所有 move/up 都定向到 target
    if (target.setPointerCapture) {
      target.setPointerCapture(e.pointerId)
    }
  }, true) // capture: true, 在 Element Plus 之前拦截

  // pointermove 绑定在 document 上,但因为 setPointerCapture,
  // 事件会被强制 dispatch 到 target 上(冒泡到 document 也能收到)
  document.addEventListener('pointermove', (e) => {
    if (!dragging) return
    const dx = e.clientX - startX
    const dy = e.clientY - startY
    dragging.style.left = (originLeft + dx) + 'px'
    dragging.style.top = (originTop + dy) + 'px'
    if (tipEl) tipEl.remove()
    tipEl = makeTip(e.clientX + 12, e.clientY + 12,
      `↔ ${Math.round(dx)}px  ↕ ${Math.round(dy)}px`)
  })

  // pointerup — 松手后元素停留在新位置(不再清空 left/top)
  document.addEventListener('pointerup', (e) => {
    if (!dragging) return
    const el = dragging
    el.classList.remove('dd-dragging')
    try { el.releasePointerCapture(e.pointerId) } catch(_) {}

    const dx = parseFloat(el.style.left) - originLeft
    const dy = parseFloat(el.style.top) - originTop
    dragging = null
    if (tipEl) tipEl.remove()
    tipEl = null
    // 位移 > 2px 才算真拖拽,否则算点选(不弹窗,也不清空样式)
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
      showResult(el, originLeft, originTop)
    } else {
      // 只是点选,没真拖 → 清空临时 left/top
      el.style.left = ''
      el.style.top = ''
      if (el.style.position === 'relative') el.style.position = ''
    }
  })

  // pointercancel 兜底(指针丢失/窗口失焦等)
  document.addEventListener('pointercancel', () => {
    if (!dragging) return
    dragging.classList.remove('dd-dragging')
    dragging.style.left = ''
    dragging.style.top = ''
    dragging = null
    if (tipEl) tipEl.remove()
    tipEl = null
  })
}

async function refreshDbBar() {
  if (!dbConnected.value) return
  const s = await dbStats()
  if (s.ok) {
    totalItemsInDB.value = s.totalItems
    totalMemosInDB.value = s.totalMemos
    dbPathShort.value = shortPath(s.dbPath)
  }
}

function shortPath(p) {
  if (!p) return ''
  const idx = p.lastIndexOf('/')
  return idx >= 0 ? p.substring(idx + 1) : p
}

async function checkDbIntegrity() {
  if (!dbConnected.value) {
    ElMessage.warning('后端离线，暂时无法检查')
    return
  }
  checkingDb.value = true
  try {
    const s = await dbStats()
    if (!s.ok) { ElMessage.error('检查失败：' + s.error); return }
    refreshDbBar()
    // 前端的真实条目数（跨所有模块）
    const frontItems = Object.values(store.value).reduce((a, b) => a + (b || []).length, 0)
    const frontMemos = memos.value.length
    const dbItems = s.totalItems
    const dbMemos = s.totalMemos
    let parts = []
    parts.push(`前端 ${frontItems} 条条目 · DB ${dbItems} 条`)
    if (frontItems !== dbItems) parts.push('⚠️ 不一致')
    parts.push(`前端 ${frontMemos} 条备忘 · DB ${dbMemos} 条`)
    if (frontMemos !== dbMemos) parts.push('⚠️ 不一致')
    parts.push(`DB 文件：${s.dbPath}`)
    ElMessageBox.alert(parts.join('\n'), '数据一致性检查', {
      confirmButtonText: '好',
      dangerouslyUseHTMLString: false
    })
  } finally {
    checkingDb.value = false
  }
}

async function manualSyncToDb() {
  if (!dbConnected.value) {
    ElMessage.warning('后端离线，暂时无法同步')
    return
  }
  syncingDb.value = true
  try {
    // 把前端 store 里所有模块的条目批量 upsert 到后端
    for (const m of MODULES) {
      await saveItems(store.value[m.key] || [], m.key)
    }
    await saveMemos(memos.value)
    await refreshDbBar()
    ElMessage.success(`已手动同步：${totalItemsInDB.value} 条条目 + ${totalMemosInDB.value} 条备忘`)
  } catch (e) {
    ElMessage.error('同步失败：' + e.message)
  } finally {
    syncingDb.value = false
  }
}

async function initializeFromBackend() {
  const ok = await pingDb()
  if (!ok) {
    dbConnected.value = false
    ElMessage.warning('后端数据库连不上，暂时用浏览器默认数据（记得重启 dev server）')
    return
  }
  dbConnected.value = true
  try {
    const [itemsMap, memoList] = await Promise.all([fetchAllItems(), fetchAllMemos()])
    const itemCount = Object.values(itemsMap).reduce((a, b) => a + (b || []).length, 0)
    const memoCount = memoList.length

    if (itemCount === 0 && memoCount === 0) {
      dbEmpty.value = true
      // 后端空 → 检查 localStorage 有没有真实数据，有的话提示迁移
      const lsData = peekLocalStorage()
      const lsItems = Object.values(lsData.itemsByModule).reduce((a, b) => a + (b || []).length, 0)
      const lsMemos = lsData.memos.length
      if (lsItems > 0 || lsMemos > 0) {
        // 有真实 localStorage 数据 → 迁移弹窗
        migrateState.value = lsData
        migrateDialog.value = true
        store.value = mergeWithDefaultModules(lsData.itemsByModule)
        memos.value = lsData.memos
      } else {
        // 两边都空 → 前端用默认数据，并且立即同步到 DB
        store.value = createInitial()
        memos.value = DEFAULT_MEMOS.map((m) => ({ ...m }))
        // 显式写入空 DB（不依赖 watch 的 debounce，启动期不可靠）
        try {
          for (const m of MODULES) {
            await saveItems(store.value[m.key] || [], m.key)
          }
          await saveMemos(memos.value)
          await refreshDbBar()
          console.info('已将默认数据同步到空数据库')
        } catch (e) {
          console.warn('默认数据同步失败，不影响前端使用', e)
        }
      }
      return
    }

    // 后端有数据 → 全量替换
    // 后端只存了 module_key 映射到 key，没存 MODULES 里的 icon/color/name，所以只替换 items 数组
    for (const m of MODULES) {
      store.value[m.key] = itemsMap[m.key] || []
    }
    memos.value = memoList
  } catch (e) {
    console.warn('从后端拉数据失败，使用默认数据', e)
  }
}

function mergeWithDefaultModules(itemsByModule) {
  // 保证所有模块 key 都存在，缺的用 MODULES 默认值
  const merged = createInitial()
  for (const m of MODULES) {
    if (itemsByModule[m.key] && Array.isArray(itemsByModule[m.key])) {
      merged[m.key] = itemsByModule[m.key]
    }
  }
  return merged
}

function peekLocalStorage() {
  let itemsByModule = {}
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      for (const m of MODULES) {
        if (Array.isArray(parsed[m.key])) itemsByModule[m.key] = parsed[m.key]
      }
    }
  } catch {}
  let memos = []
  try {
    const raw = localStorage.getItem(MEMO_STORAGE_KEY)
    if (raw) memos = JSON.parse(raw)
    if (!Array.isArray(memos)) memos = []
  } catch {}
  return { itemsByModule, memos }
}

async function doMigrate(mode) {
  if (!dbConnected.value) {
    ElMessage.error('后端还没连上，重启 dev server 再试')
    return
  }
  const payload = migrateState.value
  const countBefore = Object.values(peekLocalStorage().itemsByModule).reduce((a, b) => a + (b || []).length, 0)
  const memoBefore = peekLocalStorage().memos.length
  const res = await migrateFromLocalStorage({ itemsByModule: payload.itemsByModule, memos: payload.memos, mode })
  if (res.ok) {
    dbEmpty.value = false
    store.value = payload.itemsByModule
    memos.value = payload.memos
    migrateDialog.value = false
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(MEMO_STORAGE_KEY)
    ElMessage.success(`已迁移：${res.items} 条条目 + ${res.memos} 条备忘（来自 localStorage：${countBefore} + ${memoBefore}）`)
  } else {
    ElMessage.error('迁移失败，请查看控制台')
  }
}

// ---------- 异步保存（debounce，500ms） ----------
let saveStoreTimer = null
let saveMemosTimer = null

watch(
  store,
  (value) => {
    if (!dbConnected.value) return
    if (saveStoreTimer) clearTimeout(saveStoreTimer)
    saveStoreTimer = setTimeout(() => {
      for (const m of MODULES) {
        saveItems(value[m.key] || [], m.key).catch((e) => console.warn('保存 items 失败', m.key, e))
      }
    }, 500)
  },
  { deep: true }
)

watch(
  memos,
  (value) => {
    if (!dbConnected.value) return
    if (saveMemosTimer) clearTimeout(saveMemosTimer)
    saveMemosTimer = setTimeout(() => {
      saveMemos(value).catch((e) => console.warn('保存 memos 失败', e))
    }, 500)
  },
  { deep: true }
)

// UI 状态持久化
watch(activeKey, (v) => localStorage.setItem('tansuo_active', v))
watch(keyword, (v) => localStorage.setItem('tansuo_keyword', v))

function pad(n) {
  return String(n).padStart(2, '0')
}

function normalizeDateStr(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  if (Number.isNaN(d.getTime())) return dateStr
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function daysUntil(dateStr) {
  if (!dateStr) return Infinity
  const normalized = normalizeDateStr(dateStr)
  const target = new Date(normalized + 'T00:00:00')
  if (Number.isNaN(target.getTime())) return Infinity
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((target - today) / 86400000)
}

const sortedMemos = computed(() => {
  const list = [...memos.value]
  list.sort((a, b) => {
    if (a.done !== b.done) return a.done ? 1 : -1
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1
    const da = daysUntil(a.due)
    const db = daysUntil(b.due)
    if (Number.isFinite(da) && Number.isFinite(db)) return da - db
    if (Number.isFinite(da)) return -1
    if (Number.isFinite(db)) return 1
    return 0
  })
  return list
})

const upcomingCount = computed(
  () => memos.value.filter((m) => !m.done && Number.isFinite(daysUntil(m.due))).length
)

const current = computed(() => MODULES.find((m) => m.key === activeKey.value))
const items = computed(() => store.value[activeKey.value])
const doneCount = computed(() => items.value.filter((i) => i.status === 'done').length)
const progress = computed(() =>
  items.value.length ? Math.round((doneCount.value / items.value.length) * 100) : 0
)
const filtered = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter((item) =>
    [item.title, item.tag, item.note].some((text) => (text || '').toLowerCase().includes(q))
  )
})

function handleSelect(key) {
  activeKey.value = key
  keyword.value = ''
}

function isGoalItem(item) {
  return item && typeof item.target === 'number' && typeof item.current === 'number'
}

function openDialog() {
  editingId.value = null
  if (current.value.key === 'plan') {
    form.value = {
      title: '',
      tag: '目标',
      note: '',
      status: 'todo',
      current: null,
      target: null,
      unit: '',
      deadline: null
    }
  } else {
    form.value = { title: '', tag: '', note: '', status: 'todo' }
  }
  dialogVisible.value = true
}

function openEditDialog(item) {
  editingId.value = item.id
  if (current.value.key === 'plan') {
    form.value = {
      title: item.title,
      tag: item.tag,
      note: item.note || '',
      status: item.status,
      current: item.current,
      target: item.target,
      unit: item.unit || '',
      deadline: item.deadline || null
    }
  } else {
    form.value = {
      title: item.title,
      tag: item.tag,
      note: item.note || '',
      status: item.status
    }
  }
  dialogVisible.value = true
}

function formatDate() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function submit() {
  const title = form.value.title.trim()
  if (!title) {
    ElMessage.warning('先写个标题')
    return
  }
  if (editingId.value) {
    const idx = items.value.findIndex((i) => i.id === editingId.value)
    if (idx < 0) return
    const updated = {
      ...items.value[idx],
      title,
      tag: form.value.tag.trim() || current.value.name,
      note: form.value.note.trim(),
      status: form.value.status
    }
    if (current.value.key === 'plan') {
      updated.current = Number(form.value.current)
      updated.target = Number(form.value.target)
      updated.unit = form.value.unit.trim()
      updated.deadline = normalizeDateStr(form.value.deadline)
    }
    items.value.splice(idx, 1, updated)
    dialogVisible.value = false
    editingId.value = null
    ElMessage.success('已更新')
    return
  }
  const payload = {
    id: `${activeKey.value}-${Date.now()}`,
    title,
    tag: form.value.tag.trim() || current.value.name,
    note: form.value.note.trim(),
    status: form.value.status,
    date: formatDate()
  }
  if (current.value.key === 'plan') {
    payload.current = Number(form.value.current)
    payload.target = Number(form.value.target)
    payload.unit = form.value.unit.trim()
    payload.deadline = normalizeDateStr(form.value.deadline)
  }
  items.value.unshift(payload)
  dialogVisible.value = false
  ElMessage.success('已添加')
}

function cycleStatus(item) {
  item.status = NEXT_STATUS[item.status] || 'todo'
}

// 规划模块：更新目标当前值（每点一次 ±1 单位）
function adjustCurrent(item, delta) {
  if (!isGoalItem(item)) return
  item.current = Math.round((item.current + delta) * 100) / 100
}

function goalProgressPercent(item) {
  if (!isGoalItem(item)) return 0
  const diff = item.target - item.current
  if (diff === 0) return 100
  // 假设起点：用 current + abs(target - current) 反推
  // 更好：让进度 = current 到 target 的接近程度
  // direction < 0 表示 current > target（要减）；> 0 表示要增
  const direction = Math.sign(item.target - item.current)
  // 简化：假设起点是 current + (target - current) * sign... 太绕
  // 换做法：进度条按 0~max(current,target) 映射
  const max = Math.max(item.current, item.target)
  if (max === 0) return 0
  // 让进度直观：减到 0 → 0%；达到 target → 100%
  if (direction < 0) {
    // 要减：起点 current，终点 target。总距离 = current - target
    const total = item.current - item.target
    const done = item.current - item.current // 已经在起点了=0
    // 我们想要：当 current 下降到 target 时显示 100%
    // 进度 = 已减少的量 / 需减少的总量
    return Math.max(0, Math.min(100, Math.round((1 - (item.current - item.target) / total) * 100)))
  } else {
    // 要增：进度 = current / target
    return Math.max(0, Math.min(100, Math.round((item.current / item.target) * 100)))
  }
}

function daysToDeadline(deadline) {
  if (!deadline) return null
  return daysUntil(deadline)
}

async function removeItem(item) {
  try {
    await ElMessageBox.confirm(`删除「${item.title}」？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    if (dbConnected.value) {
      removeItemFromApi(item.id).catch((e) => console.warn('删除 API 失败', e))
    }
    const index = items.value.findIndex((i) => i.id === item.id)
    if (index > -1) items.value.splice(index, 1)
    ElMessage.success('已删除')
  } catch (err) {
    // 用户取消
  }
}

// ---------- 备忘录操作 ----------
const memoDialog = ref(false)
const memoEditingId = ref(null)

function openMemoDrawer() {
  memoDrawer.value = !memoDrawer.value
}

function openAddMemoDialog() {
  memoEditingId.value = null
  memoForm.value = { title: '', note: '', due: null }
  memoDialog.value = true
}

function openEditMemo(memo) {
  memoEditingId.value = memo.id
  memoForm.value = {
    title: memo.title,
    note: memo.note || '',
    due: memo.due || null
  }
  memoDialog.value = true
}

function formatDatePickerValue(val) {
  if (!val) return ''
  if (val instanceof Date) {
    return `${val.getFullYear()}-${pad(val.getMonth() + 1)}-${pad(val.getDate())}`
  }
  if (typeof val === 'string') return normalizeDateStr(val)
  return ''
}

function submitMemo() {
  const title = memoForm.value.title.trim()
  if (!title) {
    ElMessage.warning('先写一个标题')
    return
  }
  const payload = {
    title,
    note: memoForm.value.note.trim(),
    due: formatDatePickerValue(memoForm.value.due)
  }
  if (memoEditingId.value) {
    const idx = memos.value.findIndex((m) => m.id === memoEditingId.value)
    if (idx >= 0) {
      memos.value[idx] = { ...memos.value[idx], ...payload }
    }
    memoEditingId.value = null
    ElMessage.success('已更新备忘')
  } else {
    memos.value.unshift({
      id: `memo-${Date.now()}`,
      ...payload,
      pinned: false,
      done: false
    })
    ElMessage.success('已添加备忘')
  }
  memoForm.value = { title: '', note: '', due: null }
  memoDialog.value = false
}

// 启动时把 localStorage 里已有的日期统一规整一下（补零等）
memos.value = memos.value.map((m) => ({ ...m, due: normalizeDateStr(m.due) }))

function toggleMemoDone(memo) {
  memo.done = !memo.done
}

function toggleMemoPin(memo) {
  memo.pinned = !memo.pinned
}

async function removeMemo(memo) {
  try {
    await ElMessageBox.confirm(`删除备忘「${memo.title}」？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    if (dbConnected.value) {
      removeMemoFromApi(memo.id).catch((e) => console.warn('删除备忘 API 失败', e))
    }
    const index = memos.value.findIndex((m) => m.id === memo.id)
    if (index > -1) memos.value.splice(index, 1)
    ElMessage.success('已删除')
  } catch (err) {
    // 用户取消
  }
}

function formatDue(memo) {
  if (!memo.due) return '无截止日'
  const n = daysUntil(memo.due)
  if (memo.done) return memo.due
  if (n < 0) return `${memo.due} · 已逾期 ${-n} 天`
  if (n === 0) return `${memo.due} · 今天`
  if (n === 1) return `${memo.due} · 明天`
  return `${memo.due} · 还有 ${n} 天`
}

function dueType(memo) {
  if (memo.done || !memo.due) return 'info'
  const n = daysUntil(memo.due)
  if (n < 0) return 'danger'
  if (n <= 3) return 'warning'
  return 'success'
}
</script>

<template>
  <!-- ===== 未登录:登录页面 ===== -->
  <div v-if="!currentUser" class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-mark">T</div>
        <div>
          <strong>TanSuo</strong>
          <span>探索空间 · 请先登录</span>
        </div>
      </div>
      <h2 class="login-title">欢迎回来</h2>
      <p class="login-sub">输入用户名和密码进入</p>
      <el-form :model="loginForm" label-position="top" @submit.prevent="doLogin">
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" :prefix-icon="User" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" :prefix-icon="Lock" type="password" show-password placeholder="请输入密码" autocomplete="current-password" @keyup.enter="doLogin" />
        </el-form-item>
        <el-button type="primary" :loading="loginLoading" class="login-btn" @click="doLogin">登 录</el-button>
      </el-form>
    </div>
  </div>

  <!-- ===== 已登录:主应用 ===== -->
  <template v-else>
  <div v-if="isMobile" class="app mobile-app">
    <!-- 顶部 tab bar -->
    <nav class="mobile-tabs">
      <button
        v-for="m in MODULES"
        :key="m.key"
        :class="['mtab', { active: activeKey === m.key }]"
        :style="{ '--tab-accent': m.color }"
        @click="handleSelect(m.key)"
      >
        <el-icon><component :is="m.icon" /></el-icon>
        <span>{{ m.name }}</span>
      </button>
    </nav>

    <!-- 主区：纯 div，不再有 el-container 嵌套 -->
    <div class="topbar page-head" :style="{ '--accent': current.color }">
      <!-- 左：模块标题 + 副标题 + 备忘按钮(永不隐藏) -->
      <div class="head-left">
        <p class="head-kicker">MODULE · {{ current.key.toUpperCase() }}</p>
        <h1 class="head-title">
          {{ current.name }}
          <el-badge v-if="current.key === 'life'" :value="upcomingCount" :hidden="upcomingCount === 0" class="memo-badge">
            <el-tooltip content="备忘录" placement="top">
              <el-button size="small" circle :icon="Bell" @click="openMemoDrawer" class="title-bell" />
            </el-tooltip>
          </el-badge>
        </h1>
        <p class="head-sub">{{ current.subtitle }}</p>
      </div>
      <!-- 中：统计 + 迷你进度条 -->
      <div class="head-stats">
        <div class="stat">
          <span class="stat-value">{{ items.length }}</span>
          <span class="stat-label">条目</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ doneCount }}</span>
          <span class="stat-label">已完成</span>
        </div>
        <div class="mini-progress">
          <span class="mp-num">{{ progress }}</span><span class="mp-suffix">%</span>
          <el-progress :percentage="progress" :color="current.color" :stroke-width="5" :show-text="false" class="mini-bar" />
        </div>
      </div>
      <!-- 右：展开箭头(默认) / 胶囊工具栏(展开后) -->
      <div class="head-right">
        <!-- 收起态: 一个简洁的 Expand 箭头 -->
        <div v-if="!toolbarOpen" class="toolbar-toggle" @click="toolbarOpen = true">
          <el-icon :size="16"><Expand /></el-icon>
        </div>
        <!-- 展开态: 胶囊 -->
        <div v-else class="toolbar-pill">
          <el-tooltip :content="dbConnected ? 'DB 在线' : 'DB 离线'" placement="top">
            <span class="db-dot" :class="{ offline: !dbConnected }"></span>
          </el-tooltip>
          <span class="pill-sep"></span>
          <el-tooltip content="检查数据完整性" placement="top">
            <el-button size="small" circle :icon="Search" :loading="checkingDb" @click="checkDbIntegrity" />
          </el-tooltip>
          <el-tooltip content="手动同步到 DB" placement="top" v-if="canEdit">
            <el-button size="small" circle type="success" :icon="RefreshRight" :loading="syncingDb" @click="manualSyncToDb" />
          </el-tooltip>
          <span class="pill-sep"></span>
          <el-tooltip :content="isDark ? '切到亮色' : '切到暗色'" placement="top">
            <el-button size="small" circle :icon="isDark ? Sunny : Moon" @click="toggleTheme" />
          </el-tooltip>
          <el-tooltip content="🎨 调试拖拽 (Alt+D)" placement="top">
            <el-button size="small" circle :icon="Setting" :type="isDebugDrag ? 'primary' : 'default'" @click="toggleDebugDrag" />
          </el-tooltip>
          <span class="pill-sep"></span>
          <div class="topbar-user">
            <span class="user-badge" :class="currentUser?.role">{{ currentUser?.role === 'admin' ? '管' : '看' }}</span>
            <span class="user-name">{{ currentUser?.username }}</span>
            <el-icon class="user-logout" @click="doLogout" title="登出"><SwitchButton /></el-icon>
          </div>
          <span class="pill-sep"></span>
          <div class="toolbar-toggle fold" @click="toolbarOpen = false">
            <el-icon :size="14"><Fold /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <div class="content">
      <div class="toolbar">
        <el-input v-model="keyword" class="search" placeholder="搜索标题、标签或备注" clearable :prefix-icon="Search" />
        <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openDialog">新增条目</el-button>
      </div>

      <el-row v-if="filtered.length" :gutter="16">
        <el-col v-for="item in filtered" :key="item.id" :xs="24" :sm="12" :lg="8">
          <el-card v-if="isGoalItem(item)" class="item-card goal-card" shadow="hover">
            <div class="item-head">
              <el-tag size="small" effect="plain" :color="current.color">{{ item.tag }}</el-tag>
              <el-tag size="small" :type="STATUS_MAP[item.status].type" effect="light" class="status-tag" @click="canEdit && cycleStatus(item)">{{ STATUS_MAP[item.status].label }}</el-tag>
            </div>
            <h3>{{ item.title }}</h3>
            <p v-if="item.note" class="item-note">{{ item.note }}</p>
            <div class="goal-figures">
              <div class="goal-figure"><span class="gf-label">当前</span><span class="gf-value">{{ item.current }}<em>{{ item.unit }}</em></span></div>
              <span class="gf-arrow">→</span>
              <div class="goal-figure target"><span class="gf-label">目标</span><span class="gf-value">{{ item.target }}<em>{{ item.unit }}</em></span></div>
            </div>
            <div class="goal-progress-row">
              <el-progress :percentage="goalProgressPercent(item)" :color="current.color" :stroke-width="10" class="goal-progress" />
              <div class="goal-adjust">
                <el-button v-if="canEdit" size="small" @click="adjustCurrent(item, -1)">-1</el-button>
                <el-button v-if="canEdit" size="small" @click="adjustCurrent(item, 1)">+1</el-button>
              </div>
            </div>
            <div class="goal-deadline">
              <el-tag v-if="item.deadline" size="small" effect="light" :type="daysToDeadline(item.deadline) !== null && daysToDeadline(item.deadline) < 0 ? 'danger' : 'info'">
                <el-icon style="margin-right:4px"><Calendar /></el-icon>
                {{ item.deadline }} · {{ daysToDeadline(item.deadline) === null ? '无截止' : daysToDeadline(item.deadline) < 0 ? `已逾期 ${-daysToDeadline(item.deadline)} 天` : `还有 ${daysToDeadline(item.deadline)} 天` }}
              </el-tag>
            </div>
            <div class="item-foot">
              <span class="item-date"><el-icon><Calendar /></el-icon>创建 {{ item.date }}</span>
              <div class="foot-actions">
                <el-button type="primary" size="small" :icon="Edit" v-if="canEdit" @click="openEditDialog(item)">编辑</el-button>
                <el-button type="danger" size="small" :icon="Delete" v-if="canEdit" @click="removeItem(item)">删除</el-button>
              </div>
            </div>
          </el-card>
          <el-card v-else class="item-card" shadow="hover">
            <div class="item-head">
              <el-tag size="small" effect="plain">{{ item.tag }}</el-tag>
              <el-tag size="small" :type="STATUS_MAP[item.status].type" effect="light" class="status-tag" @click="canEdit && cycleStatus(item)">{{ STATUS_MAP[item.status].label }}</el-tag>
            </div>
            <h3>{{ item.title }}</h3>
            <p class="item-note">{{ item.note || '还没有备注' }}</p>
            <div class="item-foot">
              <span class="item-date"><el-icon><Calendar /></el-icon>{{ item.date }}</span>
              <div class="foot-actions">
                <el-button type="primary" size="small" :icon="Edit" v-if="canEdit" @click="openEditDialog(item)">编辑</el-button>
                <el-button type="danger" size="small" :icon="Delete" v-if="canEdit" @click="removeItem(item)">删除</el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-else :description="keyword ? '没有匹配的条目' : '这里还空着，先记一条吧'" />
    </div>
  </div>
  <div v-else class="app desktop-root">
    <el-container class="desktop-layout">
      <el-aside width="180px" class="sidebar">
        <div class="brand">
          <div class="brand-mark">T</div>
          <div class="brand-text">
            <strong>TanSuo</strong>
            <span>探索空间</span>
          </div>
        </div>

        <p class="nav-title">模块</p>
        <div class="nav">
          <button
            v-for="m in MODULES"
            :key="m.key"
            :class="['nav-item', { active: activeKey === m.key }]"
            :style="{ '--nav-accent': m.color }"
            @click="handleSelect(m.key)"
          >
            <el-icon><component :is="m.icon" /></el-icon>
            <span class="nav-name">{{ m.name }}</span>
            <span class="nav-count">{{ store[m.key].length }}</span>
          </button>
        </div>

        <div class="sidebar-foot">
          <div class="foot-status">
            <span class="foot-dot" :class="dbConnected ? 'ok' : 'offline'"></span>
            <span v-if="dbConnected">SQLite · {{ totalItemsInDB }}条</span>
            <span v-else>后端离线</span>
          </div>
          <div class="foot-actions">
            <el-button type="primary" size="small" :icon="Search" :loading="checkingDb" @click="checkDbIntegrity">检查</el-button>
            <el-button type="success" size="small" v-if="canEdit" :icon="RefreshRight" :loading="syncingDb" @click="manualSyncToDb">同步</el-button>
          </div>
        </div>
      </el-aside>

      <div class="main-wrap">
        <div class="topbar page-head" :style="{ '--accent': current.color }">
          <div class="head-left">
            <p class="head-kicker">MODULE · {{ current.key.toUpperCase() }}</p>
            <h1 class="head-title">{{ current.name }}</h1>
            <p class="head-sub">{{ current.subtitle }}</p>
          </div>
          <div class="head-stats">
            <div class="stat">
              <span class="stat-value">{{ items.length }}</span>
              <span class="stat-label">条目</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ doneCount }}</span>
              <span class="stat-label">已完成</span>
            </div>
            <el-progress type="dashboard" :percentage="progress" :color="current.color" :width="64" />
          </div>
          <div class="head-right">
            <el-tooltip :content="dbConnected ? '已连接 SQLite 数据库' : '数据库离线'" placement="bottom">
              <el-tag :type="dbConnected ? 'success' : 'info'" effect="dark" round class="db-tag">
                {{ dbConnected ? 'DB · 在线' : 'DB · 离线' }}
              </el-tag>
            </el-tooltip>
            <el-button :icon="Bell" @click="openMemoDrawer" plain size="small" title="备忘录">备忘</el-button>
            <el-tooltip :content="isDark ? '切到亮色' : '切到暗色'" placement="bottom">
              <el-button size="small" circle :icon="isDark ? Sunny : Moon" @click="toggleTheme" />
            </el-tooltip>
            <div class="topbar-user">
              <span class="user-badge" :class="currentUser?.role">{{ currentUser?.role === 'admin' ? '管' : '看' }}</span>
              <span class="user-name">{{ currentUser?.username }}</span>
              <el-icon class="user-logout" @click="doLogout" title="登出"><SwitchButton /></el-icon>
            </div>
          </div>
        </div>

        <div class="content">
        <div class="toolbar">
          <el-input v-model="keyword" class="search" placeholder="搜索标题、标签或备注" clearable :prefix-icon="Search" />
          <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openDialog">新增条目</el-button>
        </div>

        <el-row v-if="filtered.length" :gutter="16">
          <el-col v-for="item in filtered" :key="item.id" :xs="24" :sm="12" :lg="8">
            <el-card v-if="isGoalItem(item)" class="item-card goal-card" shadow="hover">
              <div class="item-head">
                <el-tag size="small" effect="plain" :color="current.color">{{ item.tag }}</el-tag>
                <el-tag size="small" :type="STATUS_MAP[item.status].type" effect="light" class="status-tag" @click="canEdit && cycleStatus(item)">{{ STATUS_MAP[item.status].label }}</el-tag>
              </div>
              <h3>{{ item.title }}</h3>
              <p v-if="item.note" class="item-note">{{ item.note }}</p>
              <div class="goal-figures">
                <div class="goal-figure"><span class="gf-label">当前</span><span class="gf-value">{{ item.current }}<em>{{ item.unit }}</em></span></div>
                <span class="gf-arrow">→</span>
                <div class="goal-figure target"><span class="gf-label">目标</span><span class="gf-value">{{ item.target }}<em>{{ item.unit }}</em></span></div>
              </div>
              <div class="goal-progress-row">
                <el-progress :percentage="goalProgressPercent(item)" :color="current.color" :stroke-width="10" class="goal-progress" />
                <div class="goal-adjust">
                  <el-button size="small" @click="adjustCurrent(item, -1)">-1</el-button>
                  <el-button size="small" @click="adjustCurrent(item, 1)">+1</el-button>
                </div>
              </div>
              <div class="goal-deadline">
                <el-tag v-if="item.deadline" size="small" effect="light" :type="daysToDeadline(item.deadline) !== null && daysToDeadline(item.deadline) < 0 ? 'danger' : 'info'">
                  <el-icon style="margin-right:4px"><Calendar /></el-icon>
                  {{ item.deadline }} · {{ daysToDeadline(item.deadline) === null ? '无截止' : daysToDeadline(item.deadline) < 0 ? `已逾期 ${-daysToDeadline(item.deadline)} 天` : `还有 ${daysToDeadline(item.deadline)} 天` }}
                </el-tag>
              </div>
              <div class="item-foot">
                <span class="item-date"><el-icon><Calendar /></el-icon>创建 {{ item.date }}</span>
                <div class="foot-actions">
                  <el-button type="primary" size="small" :icon="Edit" v-if="canEdit" @click="openEditDialog(item)">编辑</el-button>
                  <el-button type="danger" size="small" :icon="Delete" v-if="canEdit" @click="removeItem(item)">删除</el-button>
                </div>
              </div>
            </el-card>
            <el-card v-else class="item-card" shadow="hover">
              <div class="item-head">
                <el-tag size="small" effect="plain">{{ item.tag }}</el-tag>
                <el-tag size="small" :type="STATUS_MAP[item.status].type" effect="light" class="status-tag" @click="canEdit && cycleStatus(item)">{{ STATUS_MAP[item.status].label }}</el-tag>
              </div>
              <h3>{{ item.title }}</h3>
              <p class="item-note">{{ item.note || '还没有备注' }}</p>
              <div class="item-foot">
                <span class="item-date"><el-icon><Calendar /></el-icon>{{ item.date }}</span>
                <div class="foot-actions">
                  <el-button type="primary" size="small" :icon="Edit" v-if="canEdit" @click="openEditDialog(item)">编辑</el-button>
                  <el-button type="danger" size="small" :icon="Delete" v-if="canEdit" @click="removeItem(item)">删除</el-button>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
        <el-empty v-else :description="keyword ? '没有匹配的条目' : '这里还空着，先记一条吧'" />
        </div>  <!-- /content -->
      </div>  <!-- /main-wrap -->
    </el-container>  <!-- /desktop-layout -->
  </div>

  <!-- ===== 全局组件(dialog/drawer):两个布局分支都渲染 ===== -->
  <el-dialog v-model="dialogVisible" :title="editingId ? `编辑 · ${current.name}` : `新增 · ${current.name}`" width="min(520px, 92%)" top="5vh">
      <el-form :model="form" label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="要记下什么？" maxlength="40" show-word-limit />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tag" placeholder="例如：饮食 / 阅读 / 项目" maxlength="10" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="补充一点细节（可选）" />
        </el-form-item>

        <!-- 规划模块专属：目标字段 -->
        <template v-if="current.key === 'plan'">
          <el-divider content-position="left">目标参数</el-divider>
          <el-row :gutter="12">
            <el-col :span="10">
              <el-form-item label="当前值">
                <el-input-number v-model="form.current" style="width:100%" :step="1" :precision="1" />
              </el-form-item>
            </el-col>
            <el-col :span="10">
              <el-form-item label="目标值">
                <el-input-number v-model="form.target" style="width:100%" :step="1" :precision="1" />
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="单位">
                <el-input v-model="form.unit" placeholder="斤" maxlength="4" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="截止日期">
            <el-date-picker
              v-model="form.deadline"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="点击选择"
              style="width: 100%"
            />
          </el-form-item>
        </template>

        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio-button value="todo">待开始</el-radio-button>
            <el-radio-button value="doing">进行中</el-radio-button>
            <el-radio-button value="done">已完成</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 备忘录抽屉 -->
    <el-drawer v-model="memoDrawer" title="备忘录" size="min(320px, 80%)" :with-header="false" class="memo-drawer">
      <div class="memo-drawer-head">
        <div>
          <h2>备忘录</h2>
          <p>共 {{ memos.length }} 条 · 待办 {{ upcomingCount }} 条</p>
        </div>
        <el-button v-if="canEdit" type="primary" :icon="Plus" @click="openAddMemoDialog">新增备忘</el-button>
      </div>

      <div class="memo-list">
        <el-empty v-if="!sortedMemos.length" description="还没有备忘，点右上角加一条吧" />
        <div v-for="memo in sortedMemos" :key="memo.id" class="memo-card" :class="{ done: memo.done, pinned: memo.pinned }">
          <div class="memo-main">
            <el-checkbox :model-value="memo.done" @change="toggleMemoDone(memo)" />
            <div class="memo-body">
              <div class="memo-title-row">
                <span class="memo-title">{{ memo.title }}</span>
                <el-icon
                  class="memo-pin"
                  :class="{ active: memo.pinned }"
                  @click="toggleMemoPin(memo)"
                ><Star /></el-icon>
              </div>
              <p v-if="memo.note" class="memo-note">{{ memo.note }}</p>
              <div class="memo-meta">
                <el-tag size="small" :type="dueType(memo)" effect="light">
                  <el-icon style="margin-right:4px"><Calendar /></el-icon>{{ formatDue(memo) }}
                </el-tag>
              </div>
            </div>
          </div>
          <div class="memo-actions">
            <el-button v-if="canEdit" type="primary" size="small" :icon="Edit" @click="openEditMemo(memo)" title="编辑" />
            <el-button v-if="canEdit" type="danger" size="small" :icon="Delete" @click="removeMemo(memo)" title="删除" />
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 备忘新增/编辑弹窗 -->
    <el-dialog v-model="memoDialog" :title="memoEditingId ? '编辑备忘' : '新增备忘'" width="min(420px, 92%)" top="5vh">
      <el-form :model="memoForm" label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="memoForm.title" placeholder="给家里打钱" maxlength="60" show-word-limit />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker
            v-model="memoForm.due"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="点击选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="memoForm.note" type="textarea" :rows="3" placeholder="写点什么" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memoDialog = false">取消</el-button>
        <el-button type="primary" @click="submitMemo">保存</el-button>
      </template>
    </el-dialog>

    <!-- localStorage → SQLite 迁移提示 -->
    <el-dialog v-model="migrateDialog" title="把浏览器数据迁入数据库" width="min(480px, 92%)" top="5vh" :close-on-click-modal="false">
      <div class="migrate-notice">
        <el-alert :closable="false" type="warning" :title="'检测到浏览器里有旧数据'" show-icon>
          <template #default>
            SQLite 数据库目前是空的，但浏览器的 localStorage 里还存着：
            <strong>{{ Object.values(migrateState.itemsByModule || {}).reduce((a, b) => a + (b || []).length, 0) }}</strong> 条条目、
            <strong>{{ (migrateState.memos || []).length }}</strong> 条备忘。
          </template>
        </el-alert>
        <ul class="migrate-tips">
          <li><strong>全部替换</strong>：清掉数据库，把浏览器里的所有数据搬过去（推荐）</li>
          <li><strong>追加合并</strong>：保留数据库已有数据，按 id 做 upsert</li>
          <li><strong>跳过</strong>：就用默认数据，以后手动迁</li>
        </ul>
      </div>
      <template #footer>
        <el-button text @click="migrateDialog = false; localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(MEMO_STORAGE_KEY); location.reload()">跳过 & 清浏览器缓存</el-button>
        <el-button @click="migrateDialog = false">先不迁</el-button>
        <el-button type="warning" :icon="WarningFilled" @click="doMigrate('append')">追加合并</el-button>
        <el-button type="primary" @click="doMigrate('replace')">全部替换</el-button>
      </template>
    </el-dialog>

  </template>
</template>

