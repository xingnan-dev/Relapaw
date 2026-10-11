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

### Slice 2 人工验收

- 2026-10-12：用户本地运行专项测试，终端显示 `11 passed in 0.37s`。
- 用户明确确认 Phase 3 Slice 2 人工验收通过。
