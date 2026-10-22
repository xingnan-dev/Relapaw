# Relapaw

Relapaw 是面向宠物主人的 AI 行为理解与人宠关系 Copilot。产品坚持 **Observation ≠ Interpretation**：帮助主人区分客观观察与主观理解，不替宠物说话，也不进行疾病或心理诊断。

> Beyond the Paw. The Bond.  
> 两心相照，寂而相通。

## 技术栈

- 前端：React、TypeScript、Vite、Vitest、Testing Library
- 后端：Python、FastAPI、Pydantic v2、SQLAlchemy 2.x、Alembic
- 数据库：SQLite（开发期），通过 ORM、迁移脚本和环境配置保留 PostgreSQL 边界
- 接口与测试：REST、pytest、Vitest

## 本地启动

建议使用 Python 3.11+ 与 Node.js 20+。当前环境已在 Python 3.14.4 与 Node.js 24 上完成回归。

### 合成数据演示（推荐）

准备好 `backend/.venv` 与前端依赖后，在仓库根目录执行：

```powershell
.\scripts\demo.ps1 start
.\scripts\demo.ps1 verify
.\scripts\demo.ps1 stop
```

演示页面位于 `http://127.0.0.1:8000/`。固定演示数据完全合成，保存在独立的 `backend/.demo/relapaw-demo.db`，运行时 AI 默认关闭。需要恢复固定数据时执行 `.\scripts\demo.ps1 reset`，再重新 `start`。完整说明见[演示操作手册](docs/DEMO_OPERATOR_GUIDE.md)。长期本地使用、媒体存储和备份恢复见[本地 Alpha 使用手册](docs/LOCAL_ALPHA_GUIDE.md)。

### 后端

```powershell
cd E:\Relapaw\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API 默认位于 `http://localhost:8000`，交互文档位于 `http://localhost:8000/docs`。数据库连接可通过 `RELAPAW_DATABASE_URL` 配置。应用启动不再自动建表，数据库结构统一由 Alembic 管理。

若要在内部评估环境显式启用 Phase 2 文本 Understanding，请把仓库根目录 `.env.example` 中的变量复制到 `backend/.env`，填写服务端专用的 `OPENAI_API_KEY` 和 `RELAPAW_OPENAI_MODEL`，并设置 `RELAPAW_AI_ENABLED=true`。配置 Key 本身不会开启运行时 AI；比赛演示保持默认 `false`。密钥不得放入前端或提交到 Git；模型未配置时接口会明确返回 `MODEL_NOT_CONFIGURED`，不会生成替代结果。可选的 `RELAPAW_OPENAI_BASE_URL` 可指向实现 Responses API 的 OpenAI 兼容服务，`RELAPAW_MODEL_PROVIDER` 用于如实记录 Provider 名称；超时和最大输出分别由 `RELAPAW_OPENAI_TIMEOUT_SECONDS` 与 `RELAPAW_OPENAI_MAX_OUTPUT_TOKENS` 控制。

阿里云百炼 Qwen 示例（仅填写在 `backend/.env`）：`RELAPAW_MODEL_PROVIDER=qwen`、`RELAPAW_OPENAI_MODEL=qwen3.8-flash`、`RELAPAW_OPENAI_BASE_URL=https://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`，并把百炼 API Key 填入 `OPENAI_API_KEY`。请按实际地域替换端点和 WorkspaceId；不要把真实密钥写入仓库。由于百炼 Responses 接口未列出 Structured Outputs 参数，Qwen 配置会使用同一官方 SDK 的 OpenAI-compatible Chat Completions `parse`；OpenAI 配置仍优先使用 Responses API。

### 前端

```powershell
cd E:\Relapaw\frontend
npm ci
npm run dev
```

前端默认位于 `http://localhost:5173`，开发服务器将 `/api` 代理到后端。当前宠物由应用状态与本地持久化选择，不再硬编码宠物 ID。

### 测试与构建

```powershell
cd E:\Relapaw\backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m alembic current

cd E:\Relapaw\frontend
npm test -- --run
npm run build
```

## 当前阶段

Phase 2 文本 Understanding、Phase 3 长期记忆/量化 Baseline 与 Evaluation & Safety 已完成。当前 Qwen `qwen3.8-flash` + `text-understanding/v5-grounded-claims` 的真实资格结论为 `NOT_QUALIFIED`。

真实文本分析使用可选的 OpenAI Responses Adapter；未配置服务端 key/model 时安全返回 `MODEL_NOT_CONFIGURED`。`NOT_QUALIFIED` 表示当前组合不得被描述为已获得产品语义质量资格，不影响离线评估与失败审计证据的有效性。当前仍不包含 RAG、Agent Loop、多模态识别、自动诊断、处方/用药建议或模型自动修改人工记录与 Baseline。当前比赛版本采用[本地可重复演示](docs/DEMO_RELEASE_PROFILE.md)，只使用合成数据且默认禁用运行时 AI；运行包 Batch 1–4 已完成。另见 [产品核心](docs/PRODUCT_CORE.md)、[真实产品首发契约](docs/LAUNCH_PRODUCT_SCOPE.md)、[首发差距审计](docs/LAUNCH_GAP_AUDIT.md)、[P0-1 身份与租户架构](docs/P0_1_IDENTITY_TENANCY_ARCHITECTURE.md)、[技术架构](docs/ARCHITECTURE.md)、[UX 架构](docs/UX_ARCHITECTURE.md)、[产品路线](docs/ROADMAP.md) 与 [AI Coding 开发生命周期](docs/development/INDEX.md)。
