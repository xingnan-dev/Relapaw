# Relapaw 本地演示运行包实施计划

状态：**Batch 1–5 已完成（2026-10-17）**  
版本：1.0  
冻结日期：2026-10-16  
上游依据：[比赛与演示版本发布形态](DEMO_RELEASE_PROFILE.md)  

## 1. 实施目标

把当前需要两个开发服务器、手工迁移且没有固定演示数据的开发环境，收口为一个可重复、可验证、可安全重置的 Windows 本地演示运行包。

完成后，演示者应能从仓库根目录执行：

```powershell
.\scripts\demo.ps1 start
.\scripts\demo.ps1 verify
.\scripts\demo.ps1 reset
.\scripts\demo.ps1 stop
```

目标运行结构：

```text
PowerShell launcher
  → frontend production build
  → Alembic migration
  → versioned synthetic seed
  → FastAPI on 127.0.0.1
       ├─ /api/v1/*
       ├─ /health
       └─ / 及静态前端资源

database: E:\Relapaw\backend\.demo\relapaw-demo.db
manifest: E:\Relapaw\backend\.demo\manifest.json
pid:      E:\Relapaw\backend\.demo\server.pid
```

所有路径在实现时从脚本自身位置解析为绝对路径，不能依赖调用者当前目录。

## 2. 实施原则

- 不修改既有业务状态机和数据语义；
- 不增加账号、登录、OTP 或真实用户能力；
- 不引入 Docker 作为演示前置；
- 不把合成演示数据写入 Alembic migration；
- 不让应用启动自动 seed 或 reset；
- 不向演示数据库写入真实 API Key、真实人物或真实宠物资料；
- AI 默认关闭，客户端和服务端都不能创建新 AnalysisRun；
- 读取已存在的录制/合成 AnalysisRun 与创建新运行分开控制；
- destructive reset 必须由显式命令触发并严格验证目标路径；
- 每个批次可独立测试和回滚。

## 3. 文件级变更总表

### 3.1 新增文件

| 文件 | 作用 |
|---|---|
| `scripts/demo.ps1` | `start/reset/verify/stop` 唯一入口；安全路径校验、进程管理和错误汇总 |
| `backend/app/demo/__init__.py` | 演示模块边界 |
| `backend/app/demo/dataset_v1.py` | `relapaw-demo/v1-observe-review-baseline` 的合成数据声明与相对时间规则 |
| `backend/app/demo/seed.py` | 事务化、幂等 seed CLI；只允许 demo 环境和 demo 数据库 |
| `backend/app/demo/verify.py` | 数据集、迁移、能力开关和关键业务状态验证 CLI |
| `backend/app/schemas/capabilities.py` | 对前端公开的非敏感能力响应 schema |
| `backend/app/api/routes/capabilities.py` | `GET /api/v1/capabilities`，返回环境展示信息和 AI 可用性 |
| `backend/tests/test_demo_seed.py` | 空库 seed、幂等、回滚、相对时间、合成数据覆盖测试 |
| `backend/tests/test_demo_verify.py` | 正常与损坏 manifest/数据/迁移状态验证 |
| `backend/tests/test_demo_capabilities.py` | 默认关闭 AI、POST 拒绝、历史读取边界测试 |
| `frontend/src/state/CapabilitiesContext.tsx` | 启动时读取能力；统一提供 demo 与 AI 状态 |
| `frontend/src/state/CapabilitiesContext.test.tsx` | loading/success/failure 与安全默认值测试 |
| `docs/DEMO_OPERATOR_GUIDE.md` | 演示前准备、主演示、安全流程、故障回退与演示后清理 |

### 3.2 修改文件

| 文件 | 修改内容 |
|---|---|
| `.gitignore` | 忽略 `backend/.demo/`、PID、manifest、演示数据库与日志 |
| `.env.example` | 增加 `RELAPAW_ENV`、`RELAPAW_AI_ENABLED`、`RELAPAW_STATIC_DIR`；说明默认值和禁止提交 Secret |
| `backend/app/core/config.py` | 增加环境、AI 开关、静态目录配置；校验 demo 模式与路径边界 |
| `backend/app/main.py` | API 注册后、仅在显式 static dir 存在时挂载构建前端；保留 `/health` 真实错误；不自动 seed |
| `backend/app/api/router.py` | 注册 capabilities 路由 |
| `backend/app/api/routes/analysis.py` | POST 创建 AnalysisRun 前检查 AI 总开关；GET 历史仍可读 |
| `backend/app/api/errors.py` | 如现有错误结构不足，增加稳定的 `FEATURE_DISABLED` 使用方式，不改变响应外壳 |
| `backend/alembic.ini` | 不硬编码演示数据库；继续由环境/`env.py` 注入 URL |
| `backend/alembic/env.py` | 明确优先读取配置数据库 URL，保证 launcher 指定独立 demo DB |
| `frontend/src/types.ts` | 增加 `Capabilities` 类型 |
| `frontend/src/api.ts` | 增加 `getCapabilities()`；保持同源 `/api` 请求 |
| `frontend/src/main.tsx` | 注入 `CapabilitiesProvider` |
| `frontend/src/App.tsx` | 显示合成演示数据标识；能力加载失败时采用 AI 关闭的安全默认值 |
| `frontend/src/pages/Timeline.tsx` | 向 Understanding 区域传入能力，不直接决定服务端权限 |
| `frontend/src/components/UnderstandingPanel.tsx` | AI 关闭时移除创建/重试动作；允许展示明确标注的历史录制结果和 Safety blocked 状态 |
| `frontend/src/components/UnderstandingPanel.test.tsx` | 增加 disabled/read-only/Safety/history 测试 |
| `frontend/src/App.test.tsx` | 增加 demo 标识与能力失败安全默认值测试 |
| `frontend/src/styles.css` | 增加轻量 demo 标识与只读 AI 状态样式，不削弱 Safety |
| `README.md` | 增加演示运行包命令与当前边界；保留开发启动方法 |
| `docs/PROJECT_EXECUTION_GUIDE.md` | 实施完成后更新批次状态和证据，不在实现前宣称完成 |
| `docs/competition/*` | 每批关闭时更新工具用途、交互案例、来源、Commit/Evidence Map 与要求矩阵 |

### 3.3 明确不修改

- 不新增 Alembic 业务 migration；
- 不修改现有 Pet、Episode、Safety、Analysis、Memory、Baseline 表结构；
- 不修改 `docker-compose.yml`，Docker 继续作为未来项；
- 不添加 Supabase 或其他身份依赖；
- 不修改 Evaluation 数据集的既有资格结论；
- 不提交 `frontend/dist`、`.demo` 数据库、日志或 PID 文件。

## 4. 关键技术契约

### 4.1 环境配置

新增配置语义：

| 配置 | 默认值 | demo 要求 | 说明 |
|---|---|---|---|
| `RELAPAW_ENV` | `development` | 必须为 `demo` | 枚举：development/test/demo；当前不定义 production 行为 |
| `RELAPAW_DATABASE_URL` | 现有开发 SQLite | launcher 指向固定 `.demo` SQLite | seed/reset 不接受其他数据库 |
| `RELAPAW_AI_ENABLED` | `false` | 必须为 `false` | 只有显式 true 才允许 POST AnalysisRun；仍受 Safety 门禁 |
| `RELAPAW_STATIC_DIR` | 空 | 指向 `frontend/dist` 绝对路径 | 空时保持现有 API-only 开发模式 |

`OPENAI_API_KEY` 存在不能隐式打开 AI；必须同时显式设置 `RELAPAW_AI_ENABLED=true`。这防止开发机器遗留 Key 导致演示现场发送请求。

### 4.2 Capabilities API

响应冻结为最小非敏感信息：

```json
{
  "environment": "demo",
  "synthetic_data": true,
  "dataset_version": "relapaw-demo/v1-observe-review-baseline",
  "ai_analysis_enabled": false,
  "model_qualification": "NOT_QUALIFIED"
}
```

规则：

- 不返回 Key、数据库路径、Provider URL、文件路径或内部异常；
- `dataset_version` 来自已验证 manifest；非 demo 环境为 `null`；
- 能力读取失败时，前端默认 `ai_analysis_enabled=false`，不能 fail-open；
- Capabilities 只负责 UI 表达；服务端 POST 路由仍独立执行开关和 Safety 检查。

### 4.3 AI 关闭顺序

创建 AnalysisRun 的服务端判定顺序冻结为：

```text
读取 Episode 与 Safety Check
→ 非 NORMAL：返回/保存既有 Safety blocked 语义，Adapter 调用数为 0
→ NORMAL 但 AI disabled：返回 403 FEATURE_DISABLED，不创建失败 AnalysisRun
→ NORMAL 且 AI enabled：进入现有 Adapter 流程
```

先执行 Safety 判定，确保危险场景始终明确显示 Safety 阻断，而不是被通用功能关闭提示覆盖。AI disabled 不创建 AnalysisRun，避免把产品配置状态污染为模型失败审计。

前端行为：

- 非 NORMAL：持续展示 Safety blocked；无创建按钮；
- NORMAL + AI disabled：展示“运行时 AI 未纳入当前演示版本”；无创建或重试按钮；
- 历史录制结果存在：只读展示，并标明录制/合成来源、模型版本和 `NOT_QUALIFIED`；
- AI enabled：维持现有交互，但不属于默认演示路径。

### 4.4 静态前端托管

- `frontend` 先执行 `npm run build`；
- FastAPI 在所有 API 和 `/health` 路由注册后挂载静态目录；
- 当前应用没有 URL 路由，首版只需要 `/` 返回 `index.html` 和 `/assets/*` 返回资源；不添加吞掉未知 API 404 的全局 SPA fallback；
- static dir 缺失、不是目录或缺少 `index.html` 时，demo 启动直接失败；development API-only 模式不受影响；
- 静态文件响应不读取任意用户提供路径。

### 4.5 Demo manifest

`backend/.demo/manifest.json` 由 seed 成功提交后原子写入：

```json
{
  "dataset_version": "relapaw-demo/v1-observe-review-baseline",
  "schema_revision": "20261012_0008",
  "base_date": "<seed 当天的本地日期>",
  "synthetic": true
}
```

Manifest 不作为业务真相；`verify` 同时检查数据库内容。Seed 事务失败时不得写 manifest，manifest 写入失败时命令失败并提示重新 reset。

### 4.6 合成数据生成

`dataset_v1.py` 使用明确的构建函数，不保存真实来源文本。基准时间规则：

- `base_now` 由 CLI 注入；默认是启动时 UTC；测试传固定时间；
- UI 需要“今日到期”的复评按 `base_now` 与本地时区偏移计算；
- Episode 使用相对天数生成，保证窗口覆盖稳定；
- 合成宠物、描述和观察计划写成代码常量并有显著注释；
- Seed 调用现有 service/ORM 维护 Evidence 和业务约束，不通过 HTTP 自我调用；
- Baseline 通过现有 `recompute_snapshot` 生成，不手写聚合 JSON；
- Safety blocked AnalysisRun 通过现有安全逻辑生成或使用不调用 Adapter 的专用 fixture adapter；
- 如保留 COMPLETED 历史 Claim，只能来自冻结 recorded-output fixture，并在 snapshot 中标注 `recorded-demo`，不能调用 Provider。

首版不要求合成长期记忆候选。如果加入，必须保持 Claim 确认与 INCLUDE 两步人工语义，并明确是演示预置状态。

### 4.7 Safe reset

PowerShell 必须在同一 shell 内完成路径解析与文件操作：

1. 从 `$PSScriptRoot` 推导仓库与 `backend/.demo`；
2. 使用 `[System.IO.Path]::GetFullPath()` 得到绝对路径；
3. 验证父目录精确等于预期 `.demo` 目录；
4. 验证文件名精确等于 `relapaw-demo.db`、SQLite sidecar、manifest、PID 或允许的 demo log；
5. 验证环境为 demo；
6. 先停止由 PID 文件确认的演示进程；
7. 使用 PowerShell `Remove-Item -LiteralPath` 删除逐个明确文件，不使用递归通配符；
8. 重新 migration、seed、verify。

不得删除整个仓库、`backend`、用户主目录、默认开发数据库或任意传入路径。

### 4.8 进程管理

- `start` 检查 PID 文件与实际进程；已健康运行则返回已有 URL，不重复启动；
- 端口默认 8000，使用前检查；不自动杀死未知占用者；
- 后端使用明确虚拟环境 Python 启动；不使用 `--reload`；
- 使用隐藏后台窗口启动服务并记录 PID、命令身份和启动时间；
- `stop` 只停止 PID 文件对应且命令行/健康标识匹配的演示进程；PID 被复用或无法确认时拒绝停止并提示人工处理；
- 日志写入 `.demo`，启动失败时显示最近的安全日志行；日志不得包含完整 Episode 正文或 Secret。

## 5. 实施批次

### Batch 1：能力开关与只读 AI 边界

文件：

- `backend/app/core/config.py`
- `backend/app/api/routes/capabilities.py`
- `backend/app/schemas/capabilities.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/analysis.py`
- `frontend/src/types.ts`
- `frontend/src/api.ts`
- `frontend/src/state/CapabilitiesContext.tsx`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/pages/Timeline.tsx`
- `frontend/src/components/UnderstandingPanel.tsx`
- 对应测试与样式

验收：

- 默认配置下没有创建 AI 分析的 UI；
- 直接 POST AnalysisRun 被服务端拒绝；
- 非 NORMAL 始终先返回 Safety blocked，Adapter 调用为 0；
- 历史 AnalysisRun 仍可只读展示；
- Capabilities 失败时前端安全关闭 AI；
- 现有 AI 测试通过显式启用配置继续验证原功能。

回滚：删除 capability 路由/Context 与开关改动即可恢复现状；不涉及数据库。

### Batch 2：版本化合成数据与验证器

状态：**已完成（2026-10-17）**

文件：

- `backend/app/demo/*`
- `backend/tests/test_demo_seed.py`
- `backend/tests/test_demo_verify.py`
- `.gitignore`
- `.env.example`

验收：

- 空临时 SQLite 经 migration 后 seed 成功；
- 固定 `base_now` 产生稳定状态；
- 重复 seed 不复制数据；
- 人为破坏 manifest、删除关键关联或改变数据集版本时 verify 失败；
- seed 中途异常完整回滚；
- 不产生 Provider 网络调用；
- `.demo` 产物不进入 Git。

回滚：删除 demo 模块和忽略规则；业务 schema 与默认开发库不变。

### Batch 3：构建前端托管与健康预检

状态：**已完成（2026-10-17）**

文件：

- `backend/app/core/config.py`
- `backend/app/main.py`
- `backend/tests/test_demo_static_serving.py`（新增）
- `frontend/vite.config.ts`（仅在资产基路径确有需要时修改）

验收：

- development 未配置 static dir 时保持 API-only 行为；
- demo static dir 有效时 `/` 和哈希资源可加载；
- `/api/v1/*` 与 `/health` 不被静态挂载吞掉；
- 缺少 index、路径非法或 build 不完整时 demo 启动失败；
- 前端刷新根路径工作，未知 API 保持 JSON 404。

回滚：移除 static mount；API 不受影响。

### Batch 4：安全 Launcher 与 Operator Guide

状态：**已完成（2026-10-17）**

文件：

- `scripts/demo.ps1`
- `docs/DEMO_OPERATOR_GUIDE.md`
- `README.md`
- `backend/tests` 中可由 Python 覆盖的 CLI 契约测试
- 必要的 PowerShell 静态/集成检查脚本

验收：

- `start → verify → stop` 从干净环境成功；
- `reset` 只删除固定 demo 文件；恶意或错误路径被拒绝；
- 端口被未知进程占用时不结束对方；
- stale PID、PID 复用、迁移失败、build 失败均安全退出；
- start 两次幂等；stop 两次幂等；
- 演示进程不使用 reload 且只监听 `127.0.0.1`；
- Operator Guide 可由另一位操作者照做完成。

回滚：停止演示进程并删除 launcher；前三批仍可通过手工命令使用。

### Batch 5：完整回归与阶段关闭

状态：**已完成（2026-10-17）**

不新增业务功能，只做：

- 后端全量测试；
- 前端全量测试；
- production build；
- Alembic fresh migration；
- 空库 seed/verify；
- 连续三次 reset 与主演示路径；
- Safety 演示路径；
- 360px、720px、宽桌面；
- Chrome、Edge、键盘、焦点、reduced motion；
- 密钥、数据库、日志、PID、dist 与缓存产物检查；
- AI Code Review、修复和再次完整回归；
- 更新 competition 证据与第三方来源；
- 人工验收。

回滚：本批不引入功能代码；发现阻断问题则回到对应 Batch 修复，不带问题关闭阶段。

## 6. 测试矩阵

| 层级 | 新增重点 | 不得回退 |
|---|---|---|
| 配置单元测试 | demo 枚举、布尔开关、static path、默认 AI false | 现有模型配置和错误映射 |
| API 测试 | capabilities、FEATURE_DISABLED、Safety 优先级、历史读取 | Episode、Analysis、Memory、Baseline 全部现有 API |
| Seed 测试 | 事务、幂等、相对时间、数据覆盖、无网络 | 现有业务约束和 Evidence 生成 |
| Verify 测试 | schema、manifest、关键对象、能力开关、损坏检测 | Alembic current 与 fresh migration |
| 前端组件测试 | capability 安全默认、disabled/read-only、demo 标识 | 现有 69 项前端行为 |
| 静态托管测试 | root、asset、API 优先、缺 build 失败 | development API-only 模式 |
| Launcher 集成 | start/reset/verify/stop、路径安全、PID、端口 | 不修改系统配置，不终止未知进程 |
| 人工测试 | 三次主演示、安全路径、断网、屏幕尺寸、键盘 | UI/UX 已验收边界 |

## 7. 完成定义

只有以下条件全部成立，本地演示运行包才可标记完成：

```text
Batch 1–4 实施与定向测试完成
→ AI Code Review 完成
→ Review 问题修复
→ Batch 5 完整回归通过
→ fresh demo 可从空库启动
→ reset 三次结果一致
→ 主流程与 Safety 流程人工验收通过
→ 演示文档可由非实现者执行
→ competition 证据同步
→ 工作区无数据库、Key、日志、PID、dist 或缓存产物
→ 用户授权 commit
```

完成本阶段不表示外部多人 Beta、账号体系或生产部署已经完成。

## 8. 实施前检查

开始 Batch 1 前只需确认：

- 接受默认运行时 AI 关闭、只读展示历史录制结果；
- 接受本地演示使用独立 SQLite；
- 接受不引入 Docker 和账号体系；
- 接受演示数据完全合成且可 reset。

这些决定均来自已经冻结的演示发布形态。本计划不需要额外外部服务或付费资源。

## 9. 下一步

本地演示运行包阶段已关闭。后续在用户授权后创建里程碑 commit；之后进入比赛演示材料制作，不扩展到账号体系或公网部署。
