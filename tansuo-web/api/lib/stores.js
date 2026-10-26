// Items + Memos 数据层 - 依赖 d1.js 的查询/执行函数
import { d1Query, d1Execute, d1Batch } from './d1.js'

// ---------- Items ----------

async function listItems() {
  return d1Query('SELECT * FROM items ORDER BY module_key, id')
}

async function listItemsByModule(key) {
  return d1Query('SELECT * FROM items WHERE module_key = ? ORDER BY id', [key])
}

const ITEM_COLS = ['id', 'module_key', 'title', 'tag', 'note', 'status', 'date', 'current', 'target', 'unit', 'deadline']

function normalizeItem(it) {
  return {
    id: String(it.id),
    module_key: String(it.module_key || ''),
    title: String(it.title || ''),
    tag: it.tag == null ? null : String(it.tag),
    note: it.note == null ? null : String(it.note),
    status: it.status == null ? 'todo' : String(it.status),
    date: it.date == null ? null : String(it.date),
    current: typeof it.current === 'number' ? it.current : null,
    target: typeof it.target === 'number' ? it.target : null,
    unit: it.unit == null ? null : String(it.unit),
    deadline: it.deadline == null ? null : String(it.deadline)
  }
}

function _upsertSql(cols) {
  const placeholders = cols.map(() => '?').join(', ')
  const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
  return `INSERT INTO items (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
}

async function upsertItem(item) {
  const v = normalizeItem(item)
  return d1Execute(_upsertSql(ITEM_COLS), ITEM_COLS.map(c => v[c]))
}

async function upsertItems(items) {
  const cmds = items.map(it => {
    const v = normalizeItem(it)
    return { sql: _upsertSql(ITEM_COLS), params: ITEM_COLS.map(c => v[c]) }
  })
  return d1Batch(cmds)
}

async function deleteItem(id) { return d1Execute('DELETE FROM items WHERE id = ?', [id]) }
async function clearItems() { return d1Execute('DELETE FROM items') }

// ---------- Memos ----------

async function listMemos() {
  return d1Query('SELECT * FROM memos ORDER BY pinned DESC, id')
}

function normalizeMemo(m) {
  return {
    id: String(m.id),
    title: String(m.title || ''),
    note: m.note == null ? null : String(m.note),
    due: m.due == null ? null : String(m.due),
    pinned: m.pinned ? 1 : 0,
    done: m.done ? 1 : 0
  }
}

const MEMO_COLS = ['id', 'title', 'note', 'due', 'pinned', 'done']

function _upsertMemoSql(cols) {
  const placeholders = cols.map(() => '?').join(', ')
  const updateCols = cols.filter(c => c !== 'id').map(c => `${c}=excluded.${c}`).join(', ')
  return `INSERT INTO memos (${cols.join(', ')}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updateCols}`
}

async function upsertMemo(memo) {
  const v = normalizeMemo(memo)
  return d1Execute(_upsertMemoSql(MEMO_COLS), MEMO_COLS.map(c => v[c]))
}

async function upsertMemos(memos) {
  const cmds = memos.map(m => {
    const v = normalizeMemo(m)
    return { sql: _upsertMemoSql(MEMO_COLS), params: MEMO_COLS.map(c => v[c]) }
  })
  return d1Batch(cmds)
}

async function deleteMemo(id) { return d1Execute('DELETE FROM memos WHERE id = ?', [id]) }
async function clearMemos() { return d1Execute('DELETE FROM memos') }

export {
  listItems, listItemsByModule, upsertItem, upsertItems, deleteItem, clearItems,
  listMemos, upsertMemo, upsertMemos, deleteMemo, clearMemos
}
