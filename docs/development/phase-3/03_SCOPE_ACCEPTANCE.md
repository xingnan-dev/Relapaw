# Scope and Acceptance

## Slice 1：候选与人工决定

- [x] 新 migration 与 ORM/schema 契约，不修改 `0001`–`0005`。
- [x] 只有当前、已确认、同宠物 Claim 可建立候选。
- [x] INCLUDE/WITHDRAW 追加审计、合法转换、幂等和并发冲突保护。
- [x] stale Claim 不可新纳入；既有 ACTIVE 显示 stale 且历史保留。

## Slice 2：量化算法与快照

- [x] 纯函数覆盖 7/30/90/all 窗口、UTC 边界和 `as_of`。
- [x] duration/frequency/intensity/measured_value 按字段、behavior_type 和 unit 正确分组。
- [x] count/min/max/median、EMPTY、INSUFFICIENT_DATA 和趋势门槛有测试。
- [x] 不从自然语言或 Claim 推断数值。
- [x] 同 fingerprint 重算幂等；来源变化创建新快照并使旧快照 stale。

## Slice 3：Evidence lineage 与生命周期

- [x] 每个指标能下钻到来源字段和值快照。
- [x] Episode 编辑、新增、删除后的 stale/recompute 行为有集成测试。
- [x] lineage 写入失败整体回滚，不保留部分 Snapshot。
- [x] 人工 PetBaseline、SafetyCheck、VeterinaryEscalation 和 AnalysisRun 不被修改。

## Slice 4：前端闭环

- [x] 人工 Baseline、长期记忆与量化 Baseline 分区展示。
- [x] 候选纳入、撤回、重纳入失败时页面状态保留。
- [x] 7/30/90/all、样本量、数据不足、stale、重算和来源下钻完整。
- [x] loading/empty/error/completed 使用 Design System primitive，且不只靠颜色。
- [x] 移动端、桌面、键盘和长来源列表通过人工验收。

## 完成门禁

- [ ] Backend/Frontend 全量测试与 production build 通过。
- [ ] fresh Alembic upgrade/downgrade/current/check 与 PostgreSQL 兼容审查通过。
- [ ] 独立 AI Code Review、修复与再次完整回归通过。
- [x] 浏览器人工验收通过。
- [ ] Phase 3 与比赛证据文档更新。
- [ ] 密钥、依赖、数据库、缓存和构建产物检查通过。
- [ ] 用户分别授权 commit 与 push。
