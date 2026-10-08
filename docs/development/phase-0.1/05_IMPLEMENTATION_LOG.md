# Implementation Log

## 工程与后端

- 加入 Alembic 配置和 `20261007_0001` 初始迁移。
- 增加受控领域枚举、aware datetime 校验、结构化 API 错误。
- Timeline 增加分页元数据与稳定排序。
- 增加 PetBaseline、LifeEvent、ObservationPlan、VeterinaryEscalation API。
- 保持 Observation 与 OwnerInterpretation 独立。

## 前端与 UX

- 增加 Splash、三页 Onboarding、最小 Pet Setup。
- 增加 Current Pet Context、本地恢复、无效 ID 清理与真实空状态。
- 调整 Today、Understand、Timeline、Us 信息架构。
- 增加浮动底栏、轻量 CSS 转场与 reduced-motion 支持。

## 实现中发现并修复

- 修复当前 Starlette/FastAPI 组合下 `JSONResponse` 参数冲突。
- 修复 SQLite Alembic PRAGMA 隐式事务导致版本号未提交的问题。
- 修复 ObservationPlan 部分更新时间比较 aware/naive datetime 的风险。

未进行 commit 或 push。
