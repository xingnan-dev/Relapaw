# Phase 0 Development Record — Historical Reconstruction

本记录于 2026-10-07 根据现有代码、文档和已知测试摘要重建，不声称还原完整开发对话。

## 可确认事实

- 建立 React/TypeScript/Vite 与 FastAPI/Pydantic/SQLAlchemy/SQLite 工程。
- 建立 Pet、OwnerProfile、PetBaseline、Episode、Observation、OwnerInterpretation、LifeEvent、ObservationPlan、VeterinaryEscalation。
- Observation 与 OwnerInterpretation 已分表、分 schema、分 API。
- 建立四页 App Shell、UnderstandResult 契约和基础测试。
- 明确禁止 LLM、RAG、Agent、自动医学判断与伪精确情绪评分。

## 已知历史验证

进入 Phase 0.1 前的已知摘要为：后端 `6 passed, 1 warning`，前端 `4 passed`，前端 build 成功。由于缺少当时完整输出和逐轮 Review 记录，不补写不存在的原始日志。

## 人工决策

- 正式唯一工作目录确定为 `E:\Relapaw`。
- 迁移时不复制 `.venv`、`node_modules`、`dist`，随后通过锁文件和依赖清单恢复。
- Phase 0 之后先加固工程和 UX 入口，不提前接 AI。

## Git

当前尚未建立项目 Git 基线；等待 Phase 0/0.1 Review 后由人工授权提交。
