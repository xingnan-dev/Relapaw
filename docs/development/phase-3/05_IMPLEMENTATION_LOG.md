# Audit and Implementation Log

## 2026-10-11 — 编码前审计

### 当前可复用基础

- Episode 已有 happened_at、duration_seconds、frequency_count、intensity、location、trigger_context 和 updated_at。
- Observation 已有 behavior_type、measured_value、unit 和独立 EvidenceReference。
- AnalysisRun 保存输入/输出/模型/契约版本快照，并能根据 Episode.updated_at 判定 stale。
- Claim 保存 Evidence/Uncertainty；UserConfirmation 唯一且不可覆盖。
- Timeline 支持时间、类型和计划筛选；Follow-up 保留原记录并创建新 Episode。
- Lightweight Design System 已提供 Button、Surface、StatusNotice 和核心状态语义。

### 主要缺口

1. `pet_baselines` 是人工、可整体覆盖的 JSON，没有审计时间、版本、样本量、窗口、算法或 lineage。
2. CONFIRMED Claim 没有候选/纳入/撤回层；直接把它当长期事实会违反 Phase 2 边界。
3. UserConfirmation 一次性最终决定，不适合承载可反复 INCLUDE/WITHDRAW 的投影生命周期。
4. 当前 stale 只存在于 AnalysisRun 读取属性，没有跨 Memory/Baseline 的 fingerprint。
5. 没有 7/30/90/all 纯计算、数据不足、单位分组或趋势门槛。
6. 没有派生快照与 Episode/Observation 字段级 lineage。
7. Baseline API 只支持人工 upsert，前端没有长期记忆或量化视图。

### 风险与控制

- **确认被误当事实**：确认与纳入分离，ACTIVE 只由追加式 INCLUDE 产生。
- **伪精确指标**：只计算结构化数值，展示 count/range/median，样本不足不输出趋势。
- **单位污染**：behavior_type + field + unit 分组，不自动换算。
- **编辑后陈旧**：source fingerprint + immutable snapshot；不静默自动重算。
- **删除破坏审计**：lineage 外键 SET NULL 并保留值快照；既有 AnalysisRun 删除保护不回退。
- **部分聚合**：Snapshot/metrics/lineage 单事务写入并测试回滚。
- **范围膨胀**：v1 不接 Provider/RAG/Agent，不设计医学或情绪评分。

### 固定实施顺序

1. Slice 1：MemoryCandidate / MemoryDecision 契约、migration、服务、API 和测试；
2. Slice 2：量化纯函数、窗口、门槛、fingerprint、Snapshot 和测试；
3. Slice 3：lineage、stale/recompute、编辑删除与事务回滚；
4. Slice 4：前端分区、窗口、来源下钻、纳入撤回和状态；
5. Review、修复、完整回归、人工验收和 Git 门禁。

本轮只完成审计与规划，没有修改代码、依赖、数据库或 migration。

## 规划 Review

- 明确有限窗口为 UTC `[window_start, as_of]`，全部历史为 `happened_at <= as_of`，排除未来记录。
- 明确候选由显式幂等端点物化，不给现有 UserConfirmation 路由增加隐藏副作用。
- 保留“候选”与“INCLUDE”两步，确保确认 Claim 不会自动成为长期事实。
- 删除策略不扩大现有 AnalysisRun 保护；Snapshot lineage 使用可空外键和不可变字段快照。

未发现需要改变项目阶段顺序的阻断问题。下一步固定为 Slice 1 契约、migration、服务、API 和测试。

## 2026-10-11 — Slice 1 实现

### 已实现

- 新增 migration `20261011_0006`，独立创建 `memory_candidates` 与 `memory_decisions`，未修改旧 migration。
- `MemoryCandidate` 保存 Claim、Evidence、Uncertainty、模型及契约元数据的不可变快照。
- 候选仅能由非 stale、已完成 AnalysisRun 中经过用户确认的 Claim 显式、幂等创建。
- `MemoryDecision` 只追加 `INCLUDE/WITHDRAW` 事件；当前状态由事件推导，不覆盖 `UserConfirmation`。
- 决策写入锁定候选行；重复 request_id 同载荷幂等返回，不同载荷返回稳定冲突码。
- stale 状态优先展示；stale 候选不可新纳入，但既有决定保留且仍可追加撤回记录。
- 长期记忆读取只返回当前非 stale 且 ACTIVE 的候选。

### API

```text
POST /api/v1/claims/{claim_id}/memory-candidate
GET  /api/v1/pets/{pet_id}/memory-candidates
POST /api/v1/memory-candidates/{candidate_id}/decisions
GET  /api/v1/pets/{pet_id}/long-term-memory
```

### 边界保持

- 未修改 Observation、OwnerInterpretation、PetBaseline、SafetyCheck、VeterinaryEscalation、Episode 原文或 UserConfirmation。
- 未调用 Provider，未引入 RAG、Agent、多模态、诊断或自动长期记忆写入。
- Slice 2 量化 Baseline 尚未开始。

## 2026-10-12 — Slice 1 人工验收

- 用户在本地执行 `tests/test_memory_candidates.py -v`，截图显示 5 项专项测试全部通过。
- 用户明确回复“Phase 3 Slice 1 人工验收通过”。
- 验收范围为后端候选/纳入/撤回/stale/回滚行为；Slice 1 没有前端页面。
- 当前进入 Git commit 授权门禁；尚未 commit、尚未 push，Slice 2 尚未开始。

## 2026-10-12 — Slice 2 实现

### 已实现

- 新增 migration `20261012_0007` 与独立 `BaselineSnapshot`，未修改人工 `PetBaseline` 或旧 migration。
- 实现 `quantitative-baseline/v1` 纯函数：7/30/90/all、UTC 边界、未来记录排除、等长前置对照窗口。
- 聚合 Episode `duration_seconds/frequency_count/intensity` 及 Observation `measured_value`；后者严格按 `behavior_type + unit` 分组，不换算单位。
- 每个数值指标输出 count/min/max/median；每种 Episode 类型输出 count/observation_days。
- 每项最少 3 个样本；当前与对照均满足时才使用 20% 中位数变化门槛生成趋势。
- `source_fingerprint` 只基于结构化来源、ID、时间与更新时间；相同身份重算幂等，来源变化后旧快照动态 stale。
- 实现 recompute、latest 和 snapshot detail API；不调用模型，不读取自然语言生成数值。

### API

```text
POST /api/v1/pets/{pet_id}/baseline-snapshots/recompute
GET  /api/v1/pets/{pet_id}/baseline-snapshots/latest?window=7d|30d|90d|all
GET  /api/v1/baseline-snapshots/{snapshot_id}
```

### 范围边界

- Slice 2 暂不建立字段级 `BaselineEvidence`；该 lineage 与删除生命周期固定留在 Slice 3。
- Slice 2 没有前端变更；展示与交互固定留在 Slice 4。

## 2026-10-12 — Slice 2 人工验收

- 用户在本地执行 `tests/test_quantitative_baselines.py -v`，截图显示 11 项专项测试全部通过。
- 用户明确回复“Phase 3 Slice 2 人工验收通过”。
- 验收覆盖窗口边界、单位隔离、样本门槛、趋势、fingerprint、幂等重算、stale 及人工 Baseline 隔离。
- 当前进入 Git commit 授权门禁；尚未 commit、尚未 push，Slice 3 尚未开始。

## 2026-10-12 — Slice 3 实现

### 已实现

- 新增 migration `20261012_0008` 与 `BaselineEvidence`，没有修改旧 migration。
- 每个 Episode 数值字段、Observation measured_value 和 Episode 类型频率均保存独立 evidence。
- lineage 区分 `CURRENT/COMPARISON`，并保存 metric key、field path、值、发生时间、来源更新时间及 behavior/unit 快照。
- Episode 更新删除旧 Observation 后，旧 evidence 的 observation_id 置空但值快照保留。
- 仅被 Baseline 引用的 Episode 可按既有规则删除；episode_id/observation_id 置空，Snapshot 和 lineage 保留并显示 stale。
- 当前或对照窗口新增相关 Episode 会使旧 Snapshot stale；as_of 之后的未来 Episode 不影响旧 Snapshot。
- recompute 原子写入 Snapshot 与全部 lineage；任一 evidence 构造失败会整体回滚。
- 旧 `0007` Snapshot 在相同来源重算时可幂等补建 lineage，不覆盖指标快照。

### 边界保持

- 未扩大 Episode 删除保护：AnalysisRun/Follow-up 规则保持原样。
- 未修改人工 PetBaseline、SafetyCheck、VeterinaryEscalation、AnalysisRun、Claim 或 Memory 决定。
- 未调用 Provider；前端 Slice 4 尚未开始。

## 2026-10-12 — Slice 3 人工验收

- 用户在本地执行 `tests/test_baseline_lineage.py -v`，截图显示 5 项专项测试全部通过。
- 用户明确回复“Phase 3 Slice 3 人工验收通过”。
- 验收覆盖字段级 lineage、编辑/新增/删除生命周期、未来记录排除及事务回滚。
- 当前进入 Git commit 授权门禁；尚未 commit、尚未 push，Slice 4 尚未开始。

## 2026-10-12 — Slice 4 前端闭环实现

### 已实现

- Episode 的已确认且非 stale Claim 可显式建立 `MemoryCandidate`；建立候选不会自动纳入长期记忆。
- “我们”页面分开显示人工档案 Baseline、长期记忆候选和确定性量化 Baseline，避免来源语义混淆。
- 候选支持 INCLUDE、WITHDRAW 和重新 INCLUDE；网络失败保留候选、当前状态与可重试入口，并复用 request_id。
- stale 候选明确标注来源已变化，不允许新纳入；既有 ACTIVE stale 候选仍可撤回。
- 量化 Baseline 支持 7d/30d/90d/all，显示状态、样本量、截止时间、算法版本、stale、重算及字段级来源。
- EMPTY/INSUFFICIENT_DATA 不生成趋势；来源删除后仍显示冻结值并标注原记录已删除。
- loading、empty、error、success、stale 均使用现有 Design System primitive 和文字标签，不只依赖颜色。

### 边界保持

- 前端只调用既有 Phase 3 API；无数据库结构变化，因此没有新增或修改 migration。
- 未修改 Observation、OwnerInterpretation、人工 PetBaseline、SafetyCheck、VeterinaryEscalation、Episode 原文或 AnalysisRun 输出。
- 未调用 Provider，未接入 RAG、Agent、多模态、诊断或自动长期记忆写入。
- 完整品牌视觉精修仍固定在 Evaluation 之后，本 Slice 只完成信息架构、状态与可用性闭环。

## 2026-10-12 — Slice 4 浏览器人工验收

- 用户使用真实 Qwen 完成新的 `AnalysisRun #9`，状态为 COMPLETED；此前 Provider 网络失败保留为 FAILED 审计记录且没有部分 Claim。
- 用户确认新 Claim 后，页面出现“建立长期记忆候选”；候选建立后明确显示“尚未纳入长期记忆”。
- “我们”页面验证候选 ELIGIBLE、明确 INCLUDE 后 ACTIVE、WITHDRAW 后 WITHDRAWN，以及重新纳入入口。
- 7d 与 all 窗口成功生成 `quantitative-baseline/v1` 快照；页面同时展示 READY 总状态、指标级 INSUFFICIENT_DATA 和“无趋势结论”。
- 来源下钻展示 CURRENT、EPISODE、字段名、冻结值和发生时间；长列表滚动时底部导航未遮挡内容。
- 用户完成 30d/90d、重新纳入、窄窗口和键盘焦点检查后，明确回复“Phase 3 Slice 4 人工验收通过”。
- 当前进入 commit 授权门禁；尚未 commit、尚未 push。
