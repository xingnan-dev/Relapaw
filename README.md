# RelaPaw

RelaPaw 帮助宠物主人区分事实与自己的理解，保留原始记录，按计划复评，并回看长期变化。当前交付为本地响应式 Web。AI 默认关闭，核心旅程使用本地账号与合成数据即可完成。

## 从空库启动（Windows PowerShell）

使用 Python 3.14 和 Node.js 24。以下命令在 **产品体验 Beta 工作区**运行。两套本地服务都只监听回环地址，关闭服务时分别按 Ctrl+C。

### 终端一 · 后端

```powershell
Set-Location E:\Relapaw-ProductExperienceBeta\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 在此 PowerShell 进程清除继承的 RelaPaw/供应商配置。
Get-ChildItem Env: | Where-Object Name -Match '^(RELAPAW_|RESEND_|OPENAI_|DASHSCOPE_|QWEN_)' |
  ForEach-Object { Remove-Item -LiteralPath ("Env:" + $_.Name) }
$acceptanceDir = Join-Path $env:TEMP ("relapaw-local-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory $acceptanceDir | Out-Null
$env:RELAPAW_DISABLE_DOTENV = '1'
$env:RELAPAW_AI_ENABLED = 'false'
$env:RELAPAW_EMAIL_IDENTITY_MODE = 'local'
$env:RELAPAW_LOCAL_INVITE_CODE = '246810'
$env:RELAPAW_SESSION_PEPPER = 'local-acceptance-only'
$env:RELAPAW_CORS_ORIGINS = '["http://127.0.0.1:5173"]'
$env:RELAPAW_DATABASE_URL = 'sqlite:///' + ((Join-Path $acceptanceDir 'relapaw.db') -replace '\\', '/')
$env:RELAPAW_MEDIA_DIR = Join-Path $acceptanceDir 'relapaw_media'

.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.demo.invite_local first@example.test
.\.venv\Scripts\python.exe -m app.demo.invite_local second@example.test
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

数据库和媒体目录位于 `$acceptanceDir`。如需保留并复用本地记录，请在同一终端重启服务或继续使用该目录的配置。API 文档位于 `http://127.0.0.1:8000/docs`，`/ready` 检查数据库和迁移版本。

### 终端二 · 前端

```powershell
Set-Location E:\Relapaw-ProductExperienceBeta\frontend
npm.cmd ci
$env:VITE_API_PROXY_TARGET = 'http://127.0.0.1:8000'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

打开 `http://127.0.0.1:5173/`。填写 `first@example.test`，点击“获取验证码”，在页面输入固定本地测试码 `246810`，然后登录、同意数据约定并完成引导。用无痕窗口与 `second@example.test` 验证数据隔离。两个账号均使用本地适配器，获取验证码只创建本地挑战。

- **今天**提供记录入口、观察计划、待复评和近期记录。
- **记录 / 足迹**支持保存原话与安全检查，选填事实与理解，关联计划，搜索、修订、安排复评及管理附件。
- **我们**提供宠物档案、头像、归档与恢复、基线、手工长期记忆、生活及关系事件、照护背景和数据与隐私入口。账户导出包含 JSON 与媒体元数据，原文件在媒体入口逐项保存。
- AI 保持关闭。受控模型评估、非医疗知识和真机范围见[产品体验 Beta 使用手册](docs/PRODUCT_EXPERIENCE_BETA_GUIDE.md)。

## 自动复验

后端在新的 PowerShell 中执行，避免继承手工启动的数据库和环境配置：

```powershell
Set-Location E:\Relapaw-ProductExperienceBeta\backend
Get-ChildItem Env: | Where-Object Name -Match '^(RELAPAW_|RESEND_|OPENAI_|DASHSCOPE_|QWEN_)' |
  ForEach-Object { Remove-Item -LiteralPath ("Env:" + $_.Name) }
$env:RELAPAW_DISABLE_DOTENV = '1'
.\.venv\Scripts\python.exe -m pytest -q
```

前端在 `frontend` 中执行：

```powershell
npm.cmd test
npm.cmd run build
$env:PLAYWRIGHT_BROWSERS_PATH = '0'
npx.cmd playwright install chromium
npm.cmd run test:e2e
```

Playwright 另起 `127.0.0.1:8765` 与 `127.0.0.1:4173`，每次用新的 `backend/.e2e` 数据和预置合成邀请，覆盖桌面与移动 Chromium 视口。HTML 报告位于 `frontend/playwright-report/index.html`。

只跑到期复评与关系补测可执行 `npm.cmd run test:e2e -- followups-relationships`。用例从页面建档和安排复评，仅在本次运行的 `backend/.e2e/relapaw-e2e.db` 调整复评到期时间，并推进浏览器测试时钟。关系候选的跨日证据由页面表单填写合成日期。

入口、步骤、预期、结果和待补测项见[本地功能验收表](docs/LOCAL_FUNCTIONAL_ACCEPTANCE.md)。

### 备份和恢复本次临时数据

停止后端和前端。在仍保留 `$acceptanceDir` 的终端一中，把备份工具所在的应用目录复制到该临时目录，然后从临时目录执行。恢复会覆盖其中的数据库和媒体。

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe).Path
Copy-Item -LiteralPath .\app -Destination $acceptanceDir -Recurse
Push-Location -LiteralPath $acceptanceDir
try {
  & $python -m app.local_data backup --archive acceptance.zip
  if ($LASTEXITCODE -ne 0) { throw '备份失败' }
  & $python -m app.local_data restore --archive acceptance.zip --confirm-restore
} finally { Pop-Location }
```

使用默认工作区数据路径的 CLI 示例见[本地数据手册](docs/LOCAL_ALPHA_GUIDE.md#备份与恢复)。

## 固定合成数据演示

完成依赖安装后，在 **Beta 工作区根目录**运行：

```powershell
.\scripts\demo.ps1 start
.\scripts\demo.ps1 verify
# 在浏览器查看合成数据后停止
.\scripts\demo.ps1 stop
```

打开 `http://127.0.0.1:8000/`，使用 `demo@example.test` 与本地测试码 `246810`，同意本地数据约定后查看固定合成档案。数据位于 Beta 工作区的 `backend/.demo`，详见[演示操作手册](docs/DEMO_OPERATOR_GUIDE.md)。
