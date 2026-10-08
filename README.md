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

当前为 **Phase 0.1：工程基础加固、UX 架构与入口流程**。现已加入数据库迁移、结构化错误、受控枚举、UTC 输入边界、Timeline 稳定分页、启动/引导/宠物创建流程、当前宠物状态，以及低保真四页信息架构。

本阶段仍明确不包含真实 LLM、RAG、Agent Loop、图像/视频识别、医学规则判断、自动情绪分类、处方或用药建议，也未开始视觉品牌精修。详见 [产品核心](docs/PRODUCT_CORE.md)、[技术架构](docs/ARCHITECTURE.md)、[UX 架构](docs/UX_ARCHITECTURE.md)、[产品路线](docs/ROADMAP.md) 与 [AI Coding 开发生命周期](docs/development/INDEX.md)。
