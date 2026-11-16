# Relapaw 本地 Alpha 使用手册

本版本面向单机长期使用，不是生产服务，不需要域名、云平台、邮件供应商或外部 AI。AI 默认关闭，记录、复评、Timeline、Baseline、长期记忆、关系事件、安全知识和媒体附件均可独立使用。

## 启动

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

另开终端执行 `cd frontend` 和 `npm run dev`，然后打开 `http://localhost:5173`。只使用合成宠物和合成记录。媒体默认保存在 `backend/relapaw_media`，数据库默认是 `backend/relapaw.db`。

## 日常路径

1. 顶部选择宠物；“我们”中编辑、归档或恢复档案。
2. “记录”分开填写原始输入、Observation、主人理解与人工 Safety Check。
3. “今天”完成复评和观察计划；“足迹”搜索、筛选并打开来源。
4. “我们”维护长期记忆、Baseline、Life Event 和 Owner↔Pet / Pet↔Pet 关系事件。
5. Episode 详情读取带版本和引用的本地教育参考，并管理附件及人工可观察事实。

非 `NORMAL` Safety 会阻断解释和教育参考；历史 Baseline 不会降低当前风险。知识示例未经正式兽医审批；产品不诊断、不治疗、不提供药物或剂量。

## 备份与恢复

为获得数据库与媒体的一致快照，先停止前后端，然后运行：

```powershell
.\scripts\local-alpha-data.ps1 status
.\scripts\local-alpha-data.ps1 backup
```

备份只写入 `backend/.local-backups`。恢复会覆盖当前数据库与媒体，必须显式确认：

```powershell
.\scripts\local-alpha-data.ps1 restore -Archive relapaw-local-YYYYMMDD-HHMMSS.zip -ConfirmRestore
```

恢复后执行迁移再启动。固定合成演示继续使用 `scripts/demo.ps1 start|verify|reset|stop`，与长期使用数据库分离。

## 已知边界

- 不支持公网部署、真实用户邀请或生产级并发。
- 本地知识集是教育性示例，不是正式兽医审核知识库。
- 媒体不做自动识别；只存储、校验并保存人工事实。
- 不合格模型不能进入核心路径；关闭 AI 时所有核心功能仍可用。
- 删除附件或 Episode 会删除对应本地文件；操作前可先备份。

## 当前验证状态（2026-10-22）

- `VERIFIED`：每次运行使用全新 E2E 数据库；桌面与移动项目分别使用隔离的空账户，覆盖登录、隐私同意、首次建档、非 AI 手工记录和 Timeline 详情。1440×1000 与 Pixel 7 均通过真实 Tab/Enter、可见焦点、关键 accessibility-tree 名称、Safety 选中状态、横向溢出及移动关键控件可见/不重叠断言。该证据只代表这条核心记录旅程，不代表每个产品功能都有浏览器 E2E。
- `VERIFIED`：后端全量、前端组件、TypeScript、生产构建、fresh Alembic 迁移和本地备份恢复 round-trip 均纳入回归。
- `VERIFIED`：媒体 API 的跨租户列表、内容读取和删除攻击均以两个真实本地测试账户执行，返回 404 且不修改所有者数据。
- `INFERRED`：未逐像素穷举所有屏幕尺寸；未测试尺寸依据已经验证的 CSS 响应式断点推断。
- `UNABLE TO VERIFY`：真实屏幕阅读器语音体验、所有操作系统高对比度组合和生产级并发不在本地环境验证范围。

项目内运行浏览器回归：

```powershell
cd frontend
$env:PLAYWRIGHT_BROWSERS_PATH='0'
npm run test:e2e
```

Chromium 仅安装在项目的 `frontend/node_modules/playwright-core/.local-browsers`，没有修改全局浏览器环境。
