export const STORAGE_KEY = 'tansuo-web-data-v1'
export const MEMO_STORAGE_KEY = 'tansuo-web-memo-v1'

export const DEFAULT_MEMOS = [
  {
    id: 'memo-1',
    title: '给家里打钱（过冬费）',
    note: '2026 年冬天的过冬钱，按时打回去。',
    due: '2026-11-15',
    pinned: true,
    done: false
  }
]

export const STATUS_MAP = {
  todo: { label: '待开始', type: 'info' },
  doing: { label: '进行中', type: 'warning' },
  done: { label: '已完成', type: 'success' }
}

export const MODULES = [
  {
    key: 'life',
    name: '生活',
    subtitle: '日常的秩序与松弛',
    desc: '记录饮食、天气、习惯，以及那些值得留住的琐碎。',
    icon: 'Coffee',
    color: '#ff8a65',
    items: [
      {
        id: 'life-1',
        title: '丹竹头实惠饭馆清单',
        tag: '饮食',
        note: '把高德搜到的平价小店整理成清单，按人均价格排序。',
        date: '2026-10-24',
        status: 'doing'
      },
      {
        id: 'life-2',
        title: '一周三餐记录',
        tag: '习惯',
        note: '每天记一顿自己做的饭，周末复盘一次。',
        date: '2026-10-25',
        status: 'todo'
      }
    ]
  },
  {
    key: 'explore',
    name: '探索',
    subtitle: '走出门，去发现',
    desc: '地图上的收藏点、城市里的路线，还有没去过的角落。',
    icon: 'Compass',
    color: '#4dabf7',
    items: [
      {
        id: 'explore-1',
        title: '深圳周边徒步路线',
        tag: '户外',
        note: '先收三条低难度路线，周末挑一条走完。',
        date: '2026-10-20',
        status: 'doing'
      },
      {
        id: 'explore-2',
        title: '高德地图收藏夹整理',
        tag: '地图',
        note: '把收藏夹按「吃 / 逛 / 走」三类重新分组。',
        date: '2026-10-22',
        status: 'todo'
      }
    ]
  },
  {
    key: 'work',
    name: '工作',
    subtitle: '把事做完，也把事做对',
    desc: '项目、任务与复盘，让每一件事都有落点。',
    icon: 'Briefcase',
    color: '#5c7cfa',
    items: [
      {
        id: 'work-1',
        title: '前端页面原型',
        tag: '项目',
        note: '先搭四个模块的骨架，再逐步填充真实数据。',
        date: '2026-10-25',
        status: 'doing'
      },
      {
        id: 'work-2',
        title: '本周复盘',
        tag: '复盘',
        note: '记录做成了什么、卡在哪里、下周先做什么。',
        date: '2026-10-25',
        status: 'todo'
      }
    ]
  },
  {
    key: 'curiosity',
    name: '好奇心',
    subtitle: '持续提问，持续靠近答案',
    desc: '想读的书、想弄懂的问题、突然冒出来的灵感。',
    icon: 'MagicStick',
    color: '#9775fa',
    items: [
      {
        id: 'curiosity-1',
        title: '2D 游戏开发入门',
        tag: '学习',
        note: '先选一个引擎，做出一款能玩的小 demo。',
        date: '2026-10-18',
        status: 'doing'
      },
      {
        id: 'curiosity-2',
        title: '书单：城市与食物',
        tag: '阅读',
        note: '收集五本关于城市饮食文化的书，读完写短评。',
        date: '2026-10-21',
        status: 'todo'
      }
    ]
  },
  {
    key: 'plan',
    name: '规划',
    subtitle: '长线目标，一步步靠近',
    desc: '有截止日、有目标值的事，让进度看得见、时间也看得见。',
    icon: 'Aim',
    color: '#51cf66',
    items: [
      {
        id: 'plan-1',
        title: '开春前减到 160 斤',
        tag: '体重',
        note: '2027 年开春前，当前体重 180 斤 → 目标 160 斤。每周记录一次，控制饮食 + 保持运动。',
        date: '2026-10-25',
        status: 'doing',
        current: 180,
        target: 160,
        unit: '斤',
        deadline: '2027-03-31'
      }
    ]
  }
]
