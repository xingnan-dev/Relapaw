# Architecture Decisions

## P3-001：保留人工 PetBaseline

现有 `pet_baselines` 六组 JSON 是人工档案数据，API 继续兼容。Phase 3 不向该表自动写入；新增派生快照使用独立聚合，避免来源和信任层级混淆。

## P3-002：Confirmation 与 Memory Inclusion 分离

`UserConfirmation` 继续保持一次性最终决定。CONFIRMED 只使 Claim 具备候选资格；用户通过独立追加式 `MemoryDecision(INCLUDE/WITHDRAW)` 控制长期投影。这样撤回长期记忆无需篡改历史确认。

候选通过显式、幂等的 `POST /claims/{claim_id}/memory-candidate` 物化，不在现有 confirmation 路由中增加隐藏副作用。这也允许对 Phase 2 已存在的 CONFIRMED Claim 安全补建候选。建立候选仍不等于 INCLUDE。

## P3-003：建议的数据聚合

```text
MemoryCandidate
  - pet_id, claim_id(unique)
  - claim/evidence/uncertainty/model snapshot
  - source_episode_updated_at, created_at

MemoryDecision
  - candidate_id
  - decision: INCLUDE | WITHDRAW
  - note, created_at

BaselineSnapshot
  - pet_id, window, window_start, window_end, as_of
  - status: READY | INSUFFICIENT_DATA | EMPTY
  - algorithm_version, source_fingerprint
  - sample_count, metrics_json, created_at

BaselineEvidence
  - snapshot_id
  - nullable episode_id / observation_id
  - source/field/value/time snapshot
```

最终 migration 名称与约束在实现前由 ORM/migration 设计测试锁定，但不得复用或修改 `pet_baselines`。

## P3-004：当前状态从追加事件推导

候选的当前投影状态由最新 MemoryDecision 推导：无事件为 ELIGIBLE，最新 INCLUDE 为 ACTIVE，最新 WITHDRAW 为 WITHDRAWN。若源 AnalysisRun stale，则对外优先显示 STALE；历史决定仍保留。

## P3-005：确定性 Baseline 算法

算法版本初始为 `quantitative-baseline/v1`。默认最低样本量为每项指标 3 个有效值；窗口边界、单位分组、空值处理、中位数和趋势阈值均写入纯函数与测试。不同单位绝不自动换算或合并。

所有时间先规范化为 UTC。有限窗口采用 `window_start <= happened_at <= as_of`；全部历史采用 `happened_at <= as_of`。未来时间 Episode 不进入当前快照。`as_of` 必须带时区，响应返回规范化 UTC。

## P3-006：Source fingerprint 与不可变快照

fingerprint 由参与计算的 pet、Episode/Observation ID、更新时间、时间和结构化数值规范化后哈希得到。读取旧快照时以当前同窗口来源重新计算 fingerprint 判定 stale。重算只新增快照；lineage 保存字段和值快照，外键删除时 SET NULL。

## P3-007：删除与编辑策略

- 有 AnalysisRun 的 Episode 延续现有删除保护。
- 仅被 BaselineSnapshot 引用的 Episode 可以按产品既有规则删除；lineage 外键置空、快照保留并变 stale。
- Episode 编辑不自动重算，UI 提示 stale 并由用户触发重算。
- Active memory 的源 Claim stale 后不删除人工决定，但不再作为“当前”投影展示。

## P3-008：建议 API

```text
GET  /pets/{pet_id}/memory-candidates
POST /claims/{claim_id}/memory-candidate
POST /memory-candidates/{candidate_id}/decisions
GET  /pets/{pet_id}/long-term-memory

POST /pets/{pet_id}/baseline-snapshots/recompute
GET  /pets/{pet_id}/baseline-snapshots/latest?window=7d|30d|90d|all
GET  /baseline-snapshots/{snapshot_id}
```

写接口使用 request_id 或等价幂等键；错误码稳定区分资格、stale、状态转换、跨宠物和数据不足。

## P3-009：计算与事务

v1 使用同步、确定性本地计算，不调用 Provider。读取来源和生成 fingerprint 后，在短事务中原子保存 Snapshot、metrics 和 lineage；任一 lineage 失败必须整体回滚。
