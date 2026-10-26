# 组件拆分设计 · 2026-10-26

## 目标
- App.vue 1086 行 → 6 个 .vue 组件 + composables/ 抽逻辑
- 每个文件 < 300 行
- 保留现有功能,零回归

## 目录结构

```
src/
├── App.vue              ← 组合层,只做 v-if/v-else + props 传递(~200行)
├── main.js              ← 入口(不动)
├── modules.js           ← 5 个模块配置(不动,148行)
├── api.js               ← 前端 fetch 封装(不动,142行)
├── style.css            ← 全局样式(不动,992行)
│
├── components/
│   ├── LoginView.vue        (~60行) 登录页
│   ├── MobileLayout.vue     (~280行) 移动端布局(tab bar + item 列表 + search bar)
│   ├── DesktopLayout.vue   (~280行) 桌面端布局(侧边栏 + topbar + item 列表)
│   ├── ItemDialog.vue       (~120行) 新增/编辑条目弹窗
│   ├── MemoDrawer.vue       (~120行) 备忘录抽屉
│   └── MigrateDialog.vue    (~40行) 浏览器数据迁移弹窗(一次性)
│
└── composables/
    ├── useAuth.js        (~120行)  鉴权:login/me/logout/currentUser/canEdit
    ├── useItems.js       (~180行)  Items: CRUD/dialog/activeKey/progress/goal
    ├── useMemos.js       (~120行)  Memos: CRUD/drawer/dialog/sorted/upcoming
    └── useBreakpoint.js  (~40行)   isMobile/matchMedia 监听
```

---

## 组件接口设计

### LoginView.vue
```vue
<script setup>
defineProps({ loading: Boolean })
defineEmits(['login', 'selectRole'])
</script>
```
Props: `loading` — 登录按钮 loading 状态
Emits: `login({ username, password })`
样式:从 App.vue template L664-687 搬过来,style.css 里的 .login-page 样式已经全局了

### MobileLayout.vue
```vue
<script setup>
const props = defineProps({
  activeKey: String,      // 当前模块 key
  filtered: Array,        // 过滤后的条目列表
  canEdit: Boolean,
  currentUser: Object,    // { username, role }
  dbConnected: Boolean,
  keyword: String,
  showProgress: Boolean   // 规划模块显示进度
})
const emit = defineEmits([
  'selectModule',          // (key)
  'search',                // (keyword)
  'openDialog',            // 新增条目
  'openEditDialog',        // (item)
  'removeItem',            // (item)
  'openMemoDrawer',
  'cycleStatus',           // (item)
  'doLogout',
  'adjustCurrent'          // goal 进度 + 当前值
])
</script>
```
模板边界:L689-799(mobile-tabs + mobile-content)

### DesktopLayout.vue
```vue
<script setup>
// Props/Emits 和 MobileLayout 几乎一样
// 额外:dbPathShort(路径显示)、progressPercent、daysToDeadline
</script>
```
模板边界:L801-934(desktop-root → el-container)

### ItemDialog.vue
```vue
<script setup>
const props = defineProps({
  visible: Boolean,
  editingItem: Object,    // null=新增,有值=编辑
  moduleName: String,     // 当前模块中文名(用于 title)
  currentKey: String,     // 模块 key(判断是否规划模块)
  canEdit: Boolean
})
const emit = defineEmits(['update:visible', 'submit'])
// emit('submit', formData) → App.vue 处理 saveItems
</script>
```
模板边界:L938-992

### MemoDrawer.vue
```vue
<script setup>
const props = defineProps({
  visible: Boolean,
  memos: Array,
  canEdit: Boolean
})
const emit = defineEmits([
  'update:visible',
  'openAddMemo', 'openEditMemo',
  'toggleDone', 'togglePin', 'removeMemo'
])
</script>
```
模板边界:L996-1028

### MigrateDialog.vue
```vue
<script setup>
const props = defineProps({ visible: Boolean, migrateState: Object })
const emit = defineEmits(['update:visible', 'migrate', 'skip'])
</script>
```
模板边界:L1061-1082(直接搬,简单)

---

## 关键注意事项

1. **v-if/v-else 必须相邻**:拆分后 App.vue 变成:
   ```vue
   <LoginView v-if="!currentUser" ... />
   <MobileLayout v-else-if="isMobile" ... />
   <DesktopLayout v-else ... />
   <ItemDialog ... />          ← 全局组件,放 v-if/v-else 外面
   <MemoDrawer ... />
   <MigrateDialog ... />
   ```
   中间不能有任何东西(包括空行)在 LoginView 和 MobileLayout 之间

2. **事件回传统一**:组件只 emit 事件,App.vue 持有所有状态
   - 子组件 emit → App.vue 处理 → 改 ref → props 自动下推
   - 不搞 provide/inject(过度工程化,就 3 层组件)

3. **composables 只导出 ref + 函数**:
   ```js
   // useItems.js
   export function useItems() {
     const items = ref({})           // itemsByModule
     const dialogVisible = ref(false)
     const editingId = ref(null)
     // ... 所有逻辑函数
     return { items, dialogVisible, editingId, openDialog, submit, ... }
   }
   ```

4. **每拆一个组件就 curl + 浏览器测**:不要一次性全拆,拆一个验证一个

5. **v-model 双向绑定**:dialog/drawer 用 `<Comp v-model:visible="xxx" />` 模式
