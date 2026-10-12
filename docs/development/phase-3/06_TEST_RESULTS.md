# Phase 3 Test Results

## Slice 1 — 2026-10-11

### 自动测试

- 定向测试：`5 passed`。
- Backend 全量 pytest：`81 passed`。
- 覆盖候选资格、显式幂等创建、不可变快照、INCLUDE/WITHDRAW/重新纳入、request_id 冲突、非法转换、stale 优先级、长期投影过滤和事务回滚。
- 测试使用本地 FakeAdapter，没有访问真实或付费模型 API。

### Migration

- 开发数据库从 `20261009_0005` 升级到 `20261011_0006 (head)` 成功。
- 独立空 SQLite 数据库完整 `upgrade head → downgrade base → upgrade head` 成功。
- `alembic check`：`No new upgrade operations detected`。

### 人工验收

- 2026-10-12：用户本地执行 Slice 1 专项测试，`5 passed`，并明确确认人工验收通过。
- Phase 3 全阶段浏览器验收仍保留在 Slice 4；Slice 1 没有前端页面。

## Slice 2 — 2026-10-12

- 定向测试覆盖 7/30/90/all、UTC 包含边界、未来排除、字段/行为/单位分组、中位数、Episode 类型频率、样本不足、空数据、20% 趋势门槛、fingerprint、幂等重算、stale 和人工 Baseline 隔离：`11 passed`。
- Backend 最终全量回归：`92 passed`；Frontend Vitest：`49 passed`；production build：通过；`pip check`：通过。
- 开发数据库升级到 `20261012_0007 (head)`；`alembic check` 无 schema drift。
- 独立空数据库完整 `upgrade head → downgrade base → upgrade head` 成功。
- 测试没有调用 Provider 或真实付费 API。

### Slice 3 人工验收

- 2026-10-12：用户本地运行专项测试，终端显示 `5 passed in 0.66s`。
- 用户明确确认 Phase 3 Slice 3 人工验收通过。

### Slice 2 人工验收

- 2026-10-12：用户本地运行专项测试，终端显示 `11 passed in 0.37s`。
- 用户明确确认 Phase 3 Slice 2 人工验收通过。

## Slice 3 — 2026-10-12

- Baseline 定向测试：`16 passed`，其中 Slice 3 新增 5 项 lineage/lifecycle 集成测试。
- Backend 全量 pytest：`97 passed`。
- Frontend Vitest：`49 passed`；production build：通过；`pip check`：通过。
- 开发数据库升级到 `20261012_0008 (head)`；`alembic check` 无 schema drift。
- 独立空数据库完整 `upgrade head → downgrade base → upgrade head` 成功。
- 覆盖当前/对照字段级 lineage、编辑后不可变旧值、删除后外键置空、相关新增 stale、未来 Episode 排除及 lineage 失败整体回滚。
- 测试没有调用 Provider 或真实付费 API。

## Slice 4 — 2026-10-12

- Frontend Vitest：`56 passed`；新增覆盖候选建立失败保态、INCLUDE 失败重试 request_id、WITHDRAW/重新纳入、stale 阻断、人工/记忆/量化分区、数据不足、stale、重算失败保态和来源下钻。
- Backend 全量 pytest：`97 passed`；前端 production build：通过。
- Alembic current：`20261012_0008 (head)`；`alembic check`：无 schema drift；`pip check`：无损坏依赖。
- 本 Slice 无 schema 变化、无新 migration、无 Provider 或真实付费 API 请求。
- 移动端、桌面、键盘和长来源列表仍需浏览器人工验收，完成前不进入 commit/push 门禁。

### Slice 4 人工验收

- 2026-10-12：真实 Qwen `AnalysisRun #9` COMPLETED，并完成确认 Claim → 建立候选 → 纳入 → 撤回 → 重新纳入闭环。
- 7d/30d/90d/all 窗口、READY/INSUFFICIENT_DATA、无趋势结论、来源展开、窄窗口、键盘焦点和长列表均通过。
- 用户明确确认“Phase 3 Slice 4 人工验收通过”。
