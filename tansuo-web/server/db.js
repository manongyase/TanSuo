// SQLite 数据库层 —— 纯 Node，无第三方依赖（better-sqlite3 只在初始化时被 require）
// 表结构定义在 init() 里，首次启动自动建表。

import path from 'node:path'
import fs from 'node:fs'
import os from 'node:os'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const require = createRequire(import.meta.url)

// 数据库文件路径：优先读 TANSUO_DB 环境变量，否则放 ~/.tansuo-web/tansuo.db
const dbDir = process.env.TANSUO_DB_DIR || path.join(os.homedir(), '.tansuo-web')
const dbFile = process.env.TANSUO_DB || path.join(dbDir, 'tansuo.db')

let _db = null

export function getDb() {
  if (_db) return _db
  fs.mkdirSync(dbDir, { recursive: true })
  const BetterSqlite3 = require('better-sqlite3')
  const db = new BetterSqlite3(dbFile)
  db.pragma('journal_mode = WAL')
  db.pragma('foreign_keys = ON')
  init(db)
  _db = db
  return db
}

function init(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS items (
      id TEXT PRIMARY KEY,
      module_key TEXT NOT NULL,
      title TEXT NOT NULL,
      tag TEXT,
      note TEXT,
      status TEXT,
      date TEXT,
      current REAL,
      target REAL,
      unit TEXT,
      deadline TEXT
    );

    CREATE TABLE IF NOT EXISTS memos (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      note TEXT,
      due TEXT,
      pinned INTEGER DEFAULT 0,
      done INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS users (
      username TEXT PRIMARY KEY,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'viewer',
      created_at TEXT DEFAULT (datetime('now'))
    );
  `)

  // 种子用户:首次启动自动创建
  seedUsers(db)
}

// ---------- 用户相关 ----------
function hashPassword(pw) {
  return crypto.createHash('sha256').update(pw).digest('hex')
}

function seedUsers(db) {
  const count = db.prepare('SELECT COUNT(*) AS c FROM users').get().c
  if (count > 0) return  // 已有用户,不再插入

  const insert = db.prepare(
    'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)'
  )
  const tx = db.transaction(() => {
    insert.run('admin',  hashPassword('宇宙之疯牛倜傥'), 'admin')
    insert.run('张文秀', hashPassword('张文秀'),        'viewer')
  })
  tx()
}

export function login(username, password) {
  const db = getDb()
  const row = db.prepare(
    'SELECT username, role FROM users WHERE username = ? AND password_hash = ?'
  ).get(username, hashPassword(password))
  return row || null
}

export function getUser(username) {
  const db = getDb()
  return db.prepare('SELECT username, role FROM users WHERE username = ?').get(username) || null
}

// ---------- Items ----------
export function listItems() {
  const db = getDb()
  return db.prepare('SELECT * FROM items').all()
}

export function listItemsByModule(moduleKey) {
  const db = getDb()
  return db.prepare('SELECT * FROM items WHERE module_key = ?').all(moduleKey)
}

export function upsertItem(item) {
  const db = getDb()
  const cols = [
    'id', 'module_key', 'title', 'tag', 'note', 'status', 'date',
    'current', 'target', 'unit', 'deadline'
  ]
  const placeholders = cols.map((c) => `@${c}`).join(', ')
  const updateCols = cols.filter((c) => c !== 'id').map((c) => `${c}=excluded.${c}`).join(', ')
  const sql = `
    INSERT INTO items (${cols.join(', ')}) VALUES (${placeholders})
    ON CONFLICT(id) DO UPDATE SET ${updateCols}
  `
  db.prepare(sql).run(normalizeItem(item))
}

export function upsertItems(items) {
  const db = getDb()
  const tx = db.transaction((rows) => {
    for (const row of rows) upsertItem(row)
  })
  tx(items)
}

export function deleteItem(id) {
  const db = getDb()
  db.prepare('DELETE FROM items WHERE id = ?').run(id)
}

// ---------- Memos ----------
export function listMemos() {
  const db = getDb()
  return db.prepare('SELECT * FROM memos').all()
}

export function upsertMemo(memo) {
  const db = getDb()
  const cols = ['id', 'title', 'note', 'due', 'pinned', 'done']
  const placeholders = cols.map((c) => `@${c}`).join(', ')
  const updateCols = cols.filter((c) => c !== 'id').map((c) => `${c}=excluded.${c}`).join(', ')
  const sql = `
    INSERT INTO memos (${cols.join(', ')}) VALUES (${placeholders})
    ON CONFLICT(id) DO UPDATE SET ${updateCols}
  `
  db.prepare(sql).run(normalizeMemo(memo))
}

export function upsertMemos(memos) {
  const db = getDb()
  const tx = db.transaction((rows) => {
    for (const row of rows) upsertMemo(row)
  })
  tx(memos)
}

export function deleteMemo(id) {
  const db = getDb()
  db.prepare('DELETE FROM memos WHERE id = ?').run(id)
}

export function clearMemos() {
  const db = getDb()
  db.prepare('DELETE FROM memos').run()
}

export function clearItems() {
  const db = getDb()
  db.prepare('DELETE FROM items').run()
}

// ---------- helpers ----------
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

export const DB_FILE = dbFile
