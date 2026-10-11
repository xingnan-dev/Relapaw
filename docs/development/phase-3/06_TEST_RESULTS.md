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
