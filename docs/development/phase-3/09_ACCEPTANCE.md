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
