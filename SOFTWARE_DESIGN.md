# 逆噪显影（Noise Archaeologist）软件设计文档

## 1. 项目概述

### 1.1 产品定位

`逆噪显影` 是一款将扩散模型（DDPM）去噪过程直接做成核心玩法的网页识别闯关游戏。玩家在一张从纯噪声逐步显形的图像中抢先识别隐藏目标，并通过引导卡、区域冻结等有限干预手段影响生成方向，在"看懂图像"和"操纵图像"之间做取舍。

### 1.2 技术栈

| 层次 | 技术选型 |
|------|----------|
| 前端框架 | React 18 + TypeScript |
| 构建工具 | Vite 5 |
| 绘图 | Canvas 2D |
| 后端框架 | FastAPI (Python 3.12) |
| 推理引擎 | PyTorch + Diffusers (Stable Diffusion v1.5) |
| 图像处理 | Pillow / NumPy |
| 数据持久化 | SQLite |
| 认证 | 自签 JWT (HS256) + scrypt 密码哈希 |
| 部署 | Nginx + systemd |

### 1.3 核心设计决策

- **预生成轨迹（路线 A）**：不走实时扩散推理，而是离线预先生成所有去噪帧序列（轨迹），游戏运行时只做帧播放与分支切换。这保证了低延迟、高稳定性，适合首版 MVP 验证玩法。
- **无状态后端 + 内存会话**：游戏会话存储在服务进程内存中（带 TTL 过期），不依赖 Redis 等外部缓存。登录用户的进度写入 SQLite。
- **轨迹分支系统**：玩家使用引导卡或冻结区域后，后端切换到不同的预生成轨迹变体（如 `focus_machine`、`corrupted`、`freeze_center`），实现"干预生效"的视觉反馈。
- **HMAC 帧令牌**：帧图片 URL 携带 HMAC 签名，防止玩家通过直接访问 URL 提前看到最终帧。

---

## 2. 系统架构

### 2.1 部署架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   浏览器      │────▶│    Nginx     │────▶│   FastAPI    │
│  (React SPA)  │◀────│  (静态文件   │◀────│  (游戏服务)   │
│               │     │   + 反向代理) │     │  :8000       │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                          ┌──────┴───────┐
                                          │    SQLite    │
                                          │  (~/noise-   │
                                          │  archaeologist│
                                          │  .db)        │
                                          └──────────────┘
```

同一域名下 `/api/` 反向代理到后端，避免跨域问题。生产构建的前端静态文件由 Nginx 直接 serve。

### 2.2 项目目录结构

```
game-demo/
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── App.tsx               # 根组件（三区块布局 + 页面路由）
│   │   ├── main.tsx              # 入口
│   │   ├── components/           # UI 组件
│   │   │   ├── GameCanvas.tsx    # 主画布（Canvas 2D 帧渲染）
│   │   │   ├── GuessPanel.tsx    # 候选答案面板
│   │   │   ├── ToolPanel.tsx     # 引导卡面板
│   │   │   ├── RulePanel.tsx     # 规则面板（冻结/家族判定/规则状态）
│   │   │   ├── ScorePanel.tsx    # 分数展示与结算
│   │   │   ├── StatusBar.tsx     # 顶部状态栏
│   │   │   ├── EventLog.tsx      # 信号日志
│   │   │   ├── LandingGuide.tsx  # 首页（登录/注册/关卡选择）
│   │   │   ├── LeaderboardPage.tsx # 排行榜页
│   │   │   ├── LevelTransitionCard.tsx # 关卡过渡动画
│   │   │   ├── HistoryDrawer.tsx  # 历史记录抽屉
│   │   │   ├── AuthPanel.tsx     # 认证面板
│   │   │   ├── SessionBrief.tsx  # 会话摘要
│   │   │   ├── LoadingRoundShell.tsx # 加载骨架屏
│   │   │   ├── InlineError.tsx   # 内联错误提示
│   │   │   ├── EmptyState.tsx    # 空状态
│   │   │   └── Drawer.tsx        # 通用抽屉
│   │   ├── game/
│   │   │   ├── useGameSession.ts # 核心游戏状态管理 Hook
│   │   │   ├── scorePresentation.ts # 分数格式化工具
│   │   │   └── types.ts          # TypeScript 类型定义
│   │   └── services/
│   │       ├── api.ts            # API 请求封装
│   │       └── authStorage.ts    # 认证持久化（localStorage）
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── backend/                      # Python 后端
│   ├── app/
│   │   ├── main.py               # FastAPI 应用入口 & 路由定义
│   │   ├── service.py            # 游戏服务核心逻辑
│   │   ├── schemas.py            # Pydantic 数据模型（请求/响应）
│   │   ├── auth.py               # 认证系统（JWT + scrypt + SQLite 存储）
│   │   ├── settings.py           # 配置管理（环境变量）
│   │   ├── game_data.py          # 静态游戏数据（目标定义、引导卡定义、冻结区域）
│   │   ├── gameplay_config.py    # 关卡定义 & 规则 & 计分逻辑
│   │   ├── trajectory_store.py   # 轨迹清单加载 & 帧文件读取
│   │   ├── frame_renderer.py     # 轨迹变体定义 & 帧输出参数
│   │   └── diffusion_trajectory.py # 真实扩散推理引擎（DDIM 逆推 + 正向去噪）
│   ├── scripts/
│   │   ├── generate_trajectory_assets.py  # 离线生成轨迹资源
│   │   └── download_seed_images.py        # 下载种子图片
│   ├── assets/
│   │   ├── trajectories/
│   │   │   └── manifest.json      # 轨迹清单（索引所有预生成帧）
│   │   └── source-images/         # 原始种子图片
│   ├── tests/                     # pytest 测试
│   │   ├── test_api.py
│   │   ├── test_auth.py
│   │   ├── test_game_service.py
│   │   ├── test_gameplay_config.py
│   │   ├── test_diffusion_trajectory.py
│   │   └── test_settings.py
│   └── requirements.txt
├── deploy/                        # 部署模板
│   ├── backend.env.example
│   ├── systemd/noise-archaeologist-backend.service
│   └── nginx/noise-archaeologist.conf.example
├── DDPM_WEB_GAME_MVP.md           # 产品设计文档
└── README.md
```

---

## 3. 后端设计

### 3.1 分层架构

```
┌─────────────────────────────────────────┐
│              FastAPI 路由层              │
│  (main.py: REST API endpoint handlers)  │
├─────────────────────────────────────────┤
│            游戏服务层 (Service)           │
│  (service.py: 会话管理、规则引擎、计分)    │
├─────────────────────────────────────────┤
│    数据访问层              │  认证层      │
│  trajectory_store.py     │  auth.py     │
│  (轨迹文件读取)           │  (SQLite)    │
├───────────────────────────┴─────────────┤
│           配置 & 数据定义层              │
│  settings.py / game_data.py /           │
│  gameplay_config.py / frame_renderer.py │
└─────────────────────────────────────────┘
```

### 3.2 核心模块

#### 3.2.1 应用入口（main.py）

- 工厂函数 `create_app(settings)` 完成依赖注入：创建 TrajectoryStore → AuthService → GameService
- 注册 CORS 中间件
- 定义全部 REST API 路由（见第 5 节）
- 玩家身份解析：支持匿名玩家（X-Player-Id 头）和登录玩家（Bearer JWT），统一转为 `actor_id`

#### 3.2.2 游戏服务（service.py）

核心类 `GameService`，管理所有游戏会话。关键职责：

- **会话生命周期**：创建、推进、结算、过期清理
- **规则引擎**：12 种关卡规则（`LevelRuleId`），每种规则的触发时机和效果各不相同
- **轨迹变体选择**：根据玩家使用的引导卡、冻结区域、污染度，动态选择轨迹变体
- **计分系统**：调用 `gameplay_config.py` 中的计分函数，汇总过程分和结算分
- **进度管理**：推进关卡、解锁新关卡、记录最高分

会话数据类 `Session` 以 dataclass 定义，包含 50+ 字段，覆盖帧状态、资源状态、规则状态、事件日志等。

#### 3.2.3 认证系统（auth.py）

- `AuthService`：注册、登录、JWT 签发与验证
- `SQLiteAuthStore`：用户表（users）+ 进度表（campaign_progress）的 CRUD
- 密码使用 scrypt 哈希（n=16384, r=8, p=1）
- JWT 使用 HMAC-SHA256 自签名（无外部依赖），过期时间可配置（默认 7 天）
- `PlayerCampaignProgress`：玩家的战役进度数据类

#### 3.2.4 轨迹存储（trajectory_store.py）

- `TrajectoryStore`：加载 `manifest.json`，提供按 target_label/sample_id/variant_key/frame_index 检索帧文件的能力
- 返回 `FrameAsset`（路径 + media_type），由路由层流式返回
- 清单版本检查（要求 version >= 2）

#### 3.2.5 扩散轨迹生成（diffusion_trajectory.py）

- `DiffusionTrajectoryGenerator`：离线生成入口，封装 DDIM 逆推 + 正向去噪流程
- `DiffusersDDIMBackend`：基于 Stable Diffusion v1.5 的真实推理实现
  - **DDIM 反演**：将真实照片逆推为噪声潜变量序列
  - **正向去噪**：从噪声潜变量逐步去噪还原，每步保存中间帧
  - **冻结区域**：通过 latent blending 将指定区域的潜变量偏向更晚帧
  - **污染效果**：在指定进度的步骤中注入随机噪声

#### 3.2.6 关卡配置（gameplay_config.py）

- 12 关定义（4 章 × 3 关），每关包含难度参数（稳定性初值、污染初值、风险倍率）、规则 ID、任务类型等
- 完整计分公式：`最终得分 = 过程分 + 结算分`
  - 结算分 = 基础通关分（120）+ 提前识别奖励（最高 70）+ 剩余时间奖励（最高 92）+ 稳定奖励 + 低污染奖励 + 任务奖励 - 卡牌惩罚
- 3 种任务类型：speed（快速识别）、stability（稳定回收）、precision（少用卡牌）
- 12 种关卡规则（见第 6 节）

#### 3.2.7 配置管理（settings.py）

通过环境变量注入配置，支持自定义：
- 允许的跨域来源列表和正则
- 轨迹清单路径
- 数据库路径
- JWT 密钥和过期时间

---

## 4. 前端设计

### 4.1 组件架构

```
App
├── StatusBar            # 顶部状态栏（关卡信息、分数、时间、操作按钮）
├── LevelTransitionCard  # 关卡过渡动画（懒加载）
├── InlineError          # 全局错误提示
│
├── [首页模式]
│   └── LandingGuide     # 登录/注册/关卡选择/排行榜入口（懒加载）
│
├── [排行榜模式]
│   └── LeaderboardPage  # 排行榜展示（懒加载）
│
├── [游戏中模式]
│   ├── ScorePanel       # 左栏：分数面板（事件日志、结算明细、历史记录）
│   ├── GuessPanel       # 中栏上：候选答案面板
│   ├── GameCanvas       # 中栏下：主画布（Canvas 2D 帧渲染）
│   ├── RulePanel        # 右栏上：规则面板（家族判定、冻结区域、规则状态）
│   ├── ToolPanel        # 右栏下：引导卡面板
│   └── HistoryDrawer    # 历史记录抽屉（懒加载）
```

### 4.2 核心状态管理（useGameSession Hook）

不使用外部状态管理库，所有游戏状态集中在一个自定义 Hook 中：

```typescript
useGameSession({ autoStepEnabled?: boolean })
```

**状态维度**：
| 状态 | 说明 |
|------|------|
| `session: SessionSnapshot` | 当前游戏会话的完整快照（帧索引、候选、分数、状态等） |
| `progression: ProgressSnapshot` | 全关卡的解锁和完成状态 |
| `authUser: AuthUser` | 当前登录用户（null 为匿名） |
| `history: ScoreHistoryEntry[]` | 本地历史记录（localStorage 持久化） |
| `leaderboard: LeaderboardEntry[]` | 排行榜数据 |
| `pendingAction / error` | 异步操作状态 |
| `selectedGuess / guessReminder` | 猜测 UI 状态 |

**核心交互流程**：
1. 组件挂载时 bootstrap：从 localStorage 恢复认证 → 请求 `/api/auth/me` 或 `/api/progression`
2. 每秒自动调用 `stepSession`（由 `autoStepEnabled` 控制），推进去噪帧
3. 玩家操作（猜测、用卡、冻结、家族判定）发起 POST 请求，返回完整 SessionSnapshot 更新状态
4. 结算时保存到 localStorage 历史

### 4.3 性能优化

- **代码分割**：`LandingGuide`、`LeaderboardPage`、`LevelTransitionCard`、`HistoryDrawer` 使用 `React.lazy` 懒加载
- **React 打包分离**：`react` / `react-dom` 独立 chunk
- **帧图片缓存**：后端返回 `Cache-Control: public, max-age=86400, immutable`
- **请求序列号**：每次异步操作递增 `requestSequenceRef`，过时响应被丢弃，避免竞态

### 4.4 UI 风格

- **玻璃态 + 辉光效果**：采用 glass morphism 风格，半透明面板、模糊背景、辉光边框
- **考古扫描仪主题**：深色背景、琥珀/青色点缀、科技感终端风格
- **低分辨率图像**：64×64 或 384×384，符合"仪器解译"世界观

---

## 5. API 设计

### 5.1 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/auth/register` | 注册，返回 JWT + 用户信息 + 进度 |
| `POST` | `/api/auth/login` | 登录，返回 JWT + 用户信息 + 进度 |
| `GET` | `/api/auth/me` | 获取当前用户信息（需 Bearer Token） |

### 5.2 游戏接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/session/start` | 开始当前关卡 |
| `POST` | `/api/session/start-current-level` | 同上 |
| `POST` | `/api/session/start-level/{level_id}` | 开始指定关卡（需已解锁） |
| `POST` | `/api/session/{id}/step` | 推进一帧（自动轮询） |
| `POST` | `/api/session/{id}/guess` | 提交猜测（body: `{label}`） |
| `POST` | `/api/session/{id}/use-card` | 使用引导卡（body: `{card_id}`） |
| `POST` | `/api/session/{id}/commit-family` | 提交目标家族判定（body: `{family}`） |
| `POST` | `/api/session/{id}/freeze` | 冻结区域（body: `{region}`） |
| `POST` | `/api/session/{id}/advance` | 通关后推进到下一关 |
| `GET` | `/api/session/{id}/frames/{index}` | 获取帧图片（需 HMAC token） |

### 5.3 数据接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/progression` | 获取关卡进度 |
| `GET` | `/api/leaderboard` | 获取排行榜 |
| `GET` | `/health` | 健康检查 |

### 5.4 帧图片安全

帧图片 URL 格式：`/api/session/{sid}/frames/{idx}?variant=base&token=hmac_hex`

Token 使用 HMAC-SHA256 签名，签名字段为 `session_id:sample_id:frame_index:variant_key`，密钥为会话创建时随机生成的 `frame_secret`。这防止玩家通过猜测 URL 提前访问去噪完成的帧。

### 5.5 SessionSnapshot 响应结构

核心响应是所有游戏接口返回的 `SessionSnapshot`（Pydantic 模型，50+ 字段）：

```
{
  session_id, level_id, rule_id,
  chapter, level, chapter_title, level_title,
  score, combo, status ("playing"|"won"|"lost"),
  frame_index, total_frames, progress,
  frames_remaining, seconds_remaining,
  stability, corruption,
  image_url,                    # 当前帧图片地址（含 HMAC token）
  candidate_labels,             # 候选答案列表
  remaining_guesses, max_guesses,
  cards_remaining, max_cards,
  card_options, disabled_card_ids, used_cards,
  hint, events[],               # 信号日志
  phase_label, threat_label,
  objective_phase, family_commit_required, committed_family,
  freeze_remaining, frozen_region,
  rule_status, rule_badges,
  mission_title, step_interval_ms,
  score_breakdown,              # 仅在结算时有值
  score_events[],               # 分数事件列表
  revealed_target,              # 仅在结算时有值
  loss_reason,                  # 仅在失败时有值
  awaiting_advancement, next_level_id,
  campaign_complete, level_best_score, level_best_improved
}
```

---

## 6. 游戏机制设计

### 6.1 核心循环

```
开局 → 去噪逐帧显示(自动) → 玩家观察 ─┬─ 提前猜中 → 结算胜利
                                     ├─ 使用引导卡 → 切换轨迹变体 → 继续观察
                                     ├─ 冻结区域 → 保留局部 → 继续观察
                                     └─ 耗尽资源/稳定归零/污染爆表 → 结算失败
```

### 6.2 资源系统

| 资源 | 初始值 | 说明 |
|------|--------|------|
| 稳定性 | 66-90（随关卡递减） | 玩家操作的'血量'，归零即失败 |
| 污染度 | 8-36（随关卡递增） | 达到 100 失败，高污染触发画面劣化 |
| 猜测次数 | 2-3 | 用尽即失败 |
| 引导卡 | 1-2 | 每关可用卡牌数 |
| 冻结次数 | 0-1（部分关卡） | 每局可冻结区域次数 |

### 6.3 引导卡（3 种）

| 卡牌 | 效果 | 匹配条件 |
|------|------|----------|
| 轮廓锐化 | 通用增强，稳定+5，污染-4 | 总是匹配 |
| 机械透镜 | 机械/建筑目标增强，稳定+7，污染-6 | 目标 family=machine/structure |
| 生物扫描 | 生物目标增强，稳定+7，污染-6 | 目标 family=living |

失配时：稳定-5，污染+8，并切换到误导轨迹变体。

### 6.4 关卡规则（12 种）

| 规则 ID | 说明 | 出现关卡 |
|---------|------|---------|
| `baseline` | 基础流程，无额外限制 | 1-1 |
| `family-commit` | 需先判断目标家族（生物/机械/建筑），错选导致家族卡失效 | 1-2 |
| `freeze-choice` | 可冻结 1 次画面区域 | 1-3 |
| `masked-candidates` | 开局隐藏 2 个候选，随推进逐步揭示 | 2-1 |
| `rotating-echo` | 阶段点替换 1 个诱饵候选 | 2-2 |
| `single-card-contract` | 首张卡锁定，其余卡禁用 | 2-3 |
| `dual-phase-identification` | 必须先判家族再猜目标 | 3-1 |
| `noise-budget` | 连续推进额外抬高污染 | 3-2 |
| `freeze-delay` | 冻结后下一步额外消耗解码窗口 | 3-3 |
| `corruption-reorder` | 污染过 50 后候选重排 + 禁用一张卡 | 4-1 |
| `evidence-debt` | 出卡累积分数债务，高污染结算时扣分 | 4-2 |
| `final-archive` | 综合规则（分类+冻结+隐藏候选） | 4-3 |

### 6.5 章节结构（4 章 × 3 关 = 12 关）

```
第一章：初步校准  → 入门节奏，类别差异大，引导明显
第二章：城市回声  → 候选变多，开始隐藏与变化
第三章：失稳边缘  → 资源收紧，连续推进有代价
第四章：最终归档  → 综合考验，高惩罚
```

### 6.6 计分公式

```
过程分 = 卡牌得分 + 猜测惩罚 + 规则事件分（每步累积）
结算分 = 120 (基础) + 提前识别奖励 + 剩余时间奖励 + 稳定奖励 + 低污染奖励 + 任务奖励 - 卡牌惩罚
最终分 = 过程分 + 结算分

其中：
  提前识别奖励 = (1 - 当前进度) × 70
  剩余时间奖励 = (剩余帧 / 总帧) × 92
  稳定奖励 = round(当前稳定度) / 2
  低污染奖励 = max(0, 32 - round(污染度) / 3)
  任务奖励 = speed: (1 - 进度) × 80 | stability: 稳定度 | precision: 剩余卡牌 × 30
  卡牌惩罚 = 已用卡牌数 × 8
```

---

## 7. 数据模型

### 7.1 SQLite 表结构

```sql
CREATE TABLE users (
    id            TEXT PRIMARY KEY,     -- UUID hex
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,        -- scrypt$n$r$p$salt$hash
    created_at    INTEGER NOT NULL
);

CREATE TABLE campaign_progress (
    user_id                   TEXT PRIMARY KEY REFERENCES users(id),
    current_level_id          TEXT NOT NULL,
    highest_unlocked_level_id TEXT NOT NULL,
    completed_level_ids       TEXT NOT NULL,    -- JSON array
    best_scores_by_level      TEXT NOT NULL,    -- JSON object
    streak                    INTEGER NOT NULL,
    campaign_complete         INTEGER NOT NULL,
    updated_at                INTEGER NOT NULL
);
```

### 7.2 轨迹清单结构（manifest.json）

```json
{
  "version": 2,
  "total_frames": 100,
  "variant_keys": ["base", "focus_generic", "focus_machine", "focus_living",
                   "misguided", "corrupted",
                   "freeze_upper_left", "freeze_center", "freeze_lower_right"],
  "generator": { "model_id": "runwayml/stable-diffusion-v1-5", ... },
  "targets": {
    "cat": {
      "samples": {
        "sample-01": {
          "variants": {
            "base": ["frames/cat/sample-01/base/0001.webp", ...],
            "focus_generic": [...],
            "corrupted": [...]
          }
        }
      }
    }
  }
}
```

### 7.3 轨迹变体（9 种）

| 变体 | 触发条件 |
|------|---------|
| `base` | 默认，无干预时的基础轨迹 |
| `focus_generic` | 使用"轮廓锐化"卡 |
| `focus_machine` | 使用"机械透镜"且目标为机械/建筑 |
| `focus_living` | 使用"生物扫描"且目标为生物 |
| `misguided` | 使用家族卡但未命中目标家族 |
| `corrupted` | 污染度 ≥ 70 |
| `freeze_upper_left` | 冻结左上区域 |
| `freeze_center` | 冻结中央区域 |
| `freeze_lower_right` | 冻结右下区域 |

---

## 8. 关键数据流

### 8.1 开局流程

```
前端                                 后端
 │  POST /api/session/start            │
 │  ─────────────────────────────────▶  │
 │                                     │ 1. 读取玩家进度，确定当前关卡
 │                                     │ 2. 从关卡目标池随机抽取目标
 │                                     │ 3. 生成候选列表（含正确答案）
 │                                     │ 4. 随机选择轨迹 sample_id
 │                                     │ 5. 初始化 Session（规则、资源、初值）
 │                                     │ 6. 生成 frame_secret（HMAC 密钥）
 │  ◀─────────────────────────────────  │
 │  SessionSnapshot (含 image_url)       │
 │                                     │
 │  GET /api/session/{id}/frames/0      │
 │  ─────────────────────────────────▶  │
 │                                     │ 验证 HMAC token → 返回帧文件
 │  ◀─────────────────────────────────  │
 │  第 0 帧 webp 图片                    │
```

### 8.2 帧推进流程

```
前端 (useEffect + setInterval)
 │  每 step_interval_ms 自动
 │  POST /api/session/{id}/step
 │  ─────────────────────────────────▶
 │                                     │  frame_index += 1
 │                                     │  stability -= step_delta
 │                                     │  corruption += step_delta
 │                                     │  检查规则触发点
 │                                     │  检查失败条件
 │  ◀─────────────────────────────────
 │  SessionSnapshot (更新后的完整状态)
 │
 │  GET 新帧图片（image_url 更新）
```

### 8.3 干预流程（以引导卡为例）

```
前端
 │  POST /api/session/{id}/use-card
 │  body: { card_id: "mechanical-lens" }
 │  ─────────────────────────────────▶
 │                                     │  判断目标家族是否匹配 card
 │                                     │  → 匹配: 选择 focus_machine 变体
 │                                     │  → 失配: 选择 misguided 变体
 │                                     │  更新 stability / corruption
 │                                     │  记录分数事件
 │                                     │  触发规则相关副作用
 │  ◀─────────────────────────────────
 │  SessionSnapshot (image_url 切换到新变体)
```

---

## 9. 部署方案

### 9.1 环境变量

```
NOISE_ARCHAEOLOGIST_ALLOWED_ORIGINS    # 逗号分隔的允许来源
NOISE_ARCHAEOLOGIST_ALLOWED_ORIGIN_REGEX  # 允许来源正则
NOISE_ARCHAEOLOGIST_DB_PATH            # SQLite 数据库路径
NOISE_ARCHAEOLOGIST_JWT_SECRET         # JWT 签名密钥（生产环境必须更换）
NOISE_ARCHAEOLOGIST_JWT_EXPIRES_SECONDS # JWT 过期秒数（默认 604800）
NOISE_ARCHAEOLOGIST_TRAJECTORY_MANIFEST # 轨迹清单文件路径
```

### 9.2 部署步骤

1. **准备后端**：创建 venv，安装依赖，配置环境变量
2. **构建前端**：`VITE_API_BASE_URL=/api npm run build`
3. **安装 systemd 服务**：`noise-archaeologist-backend.service`
4. **配置 Nginx**：serve 静态文件 + `/api/` 反向代理到 `127.0.0.1:8000`

### 9.3 性能预估

- **伪实时模式**（当前实现）：普通云主机即可，无 GPU 需求
- **真实小模型模式**（如需在线推理）：需 GPU，单局总推理预算控制在 1-3 秒
- **会话 TTL**：30 分钟自动过期清理
- **图片缓存**：帧图片 HTTP 缓存 24 小时（immutable）

---

## 10. 测试策略

| 测试范围 | 测试内容 | 框架 |
|---------|---------|------|
| 配置测试 | `test_settings.py` - 环境变量加载和默认值 | pytest |
| 认证测试 | `test_auth.py` - 注册、登录、JWT 验证 | pytest |
| API 测试 | `test_api.py` - 请求/响应格式、错误码 | pytest |
| 服务测试 | `test_game_service.py` - 会话管理、规则引擎、计分 | pytest |
| 配置逻辑测试 | `test_gameplay_config.py` - 计分公式、步进风险 | pytest |
| 扩散测试 | `test_diffusion_trajectory.py` - 生成器逻辑 | pytest |

---

## 11. 安全设计

1. **密码存储**：scrypt 哈希（n=16384, r=8, p=1），不可逆
2. **JWT 签名**：HMAC-SHA256，可配置密钥和过期时间
3. **帧图片保护**：HMAC token 签名（frame_secret 为会话级随机密钥），防提前查看
4. **猜测验证**：后端强制校验猜测必须在候选列表内，且不被 masked_candidates 遮盖
5. **关卡解锁**：后端校验关卡是否已解锁，前端不可绕过
6. **输入校验**：用户名格式、密码长度、卡片 ID、冻结区域 ID 等全部在后端校验
7. **会话隔离**：每个会话绑定 player_id，跨玩家不可访问
8. **CORS**：可配置的跨域白名单

---

## 12. 扩展方向

1. **WebSocket 推送**：替换当前 HTTP 轮询，实现服务端主动推送帧，减少延迟和请求开销
2. **真实实时扩散**：从预生成轨迹升级为在线 DDIM 推理，支持更灵活的玩家干预（如自由文本 prompt、任意区域 mask 编辑）
3. **持久化会话**：将会话迁移到 Redis，支持多进程部署和会话恢复
4. **成就系统**：基于关卡完成记录和分数历史构建成就徽章
5. **多语言 UI**：将界面字符串抽象为 i18n 资源文件
6. **更高分辨率**：当前 384×384，可升级到 512×512 或更高
7. **社交功能**：好友对战、每日挑战、分享回放
