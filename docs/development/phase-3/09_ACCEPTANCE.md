# Phase 3 Acceptance

## Slice 1：长期记忆候选与人工纳入/撤回

验收日期：2026-10-12
结果：通过

### 人工检查证据

- 用户在本地运行 `tests/test_memory_candidates.py -v`。
- 终端显示 5 项测试全部 `PASSED`。
- 用户明确回复“Phase 3 Slice 1 人工验收通过”。

### 已接受的产品行为

- 确认 Claim 不会自动成为长期记忆。
- 用户必须通过独立 `INCLUDE` 决定明确纳入。
- `WITHDRAW` 与重新纳入均追加历史，不改写原确认。
- Episode 更新后候选显示 stale，不再进入当前长期记忆投影。
- stale 候选不可重新纳入，已有纳入可以撤回并保留历史。
- Slice 1 不修改 Episode 原文、Observation、OwnerInterpretation、人工 PetBaseline、SafetyCheck、VeterinaryEscalation 或 UserConfirmation。

### 后续边界

- Slice 1 没有前端页面；前端闭环固定在 Slice 4。
- 本次验收不代表 Slice 2–4 或整个 Phase 3 已完成。
- 下一门禁为用户授权 commit；push 仍需单独判断和授权。

## Slice 2：确定性量化 Baseline 与不可变快照

验收日期：2026-10-12
结果：通过

### 人工检查证据

- 用户在本地运行 `tests/test_quantitative_baselines.py -v`。
- 终端截图显示 11 项测试全部 `PASSED`，汇总为 `11 passed in 0.37s`。
- 用户明确回复“Phase 3 Slice 2 人工验收通过”。

### 已接受的产品行为

- 7/30/90/all 窗口使用明确 UTC 边界并排除未来记录。
- 不同字段、behavior_type 和 unit 不会错误合并。
- 少于 3 个样本不生成趋势；当前与对照均满足门槛后才按 20% 阈值比较。
- 不从 Raw Input、Owner Interpretation 或模型 Claim 推断数值。
- 相同来源重算幂等；来源变化使旧快照 stale，并创建新快照。
- 量化快照不覆盖人工 `PetBaseline`。

### 后续边界

- 字段级 BaselineEvidence、删除后的 lineage 保留和事务回滚属于 Slice 3。
- 前端量化展示属于 Slice 4。
- 下一门禁为用户授权 commit；push 仍需单独判断和授权。
