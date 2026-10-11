# Phase 2 Scope and Acceptance Criteria

## A. 数据与迁移

- [x] 新增独立 Alembic revision，不修改 `0001`–`0004`。
- [x] AnalysisRun、Claim、ClaimEvidenceReference、Uncertainty、UserConfirmation 具备明确外键、唯一约束和删除策略。
- [x] 全新数据库和已有 Phase 1 数据库均可升级、降级、再升级。
- [x] 所有外部时间为带时区输入并使用 UTC 响应语义。

## B. Adapter 与版本

- [x] 业务服务只依赖 TextUnderstandingAdapter 协议。
- [x] 模型 provider、名称、版本及输入/输出/Prompt 契约版本被保存。
- [x] 未配置 provider 时返回真实错误，不生成模拟结果。
- [x] 非测试运行不使用 FakeAdapter；密钥不进入日志、响应或持久化。
- [x] Provider 认证、权限、超时、限流、网络、服务异常、refusal、截断和非法输出有稳定错误映射。

## C. Observation / Interpretation / Claim 边界

- [x] Adapter 输入明确区分 Raw Input、Observation 与 OwnerInterpretation。
- [x] Claim 作为独立模型对象，不写入 Observation 或 OwnerInterpretation。
- [x] 每条 Claim 含可展示 Evidence 和 Uncertainty，未知来源引用被拒绝。
- [x] Prompt 明确禁止伪精确评分、诊断、治疗/用药建议和因果定论，并要求逐 Claim 不确定性。

## D. Safety

- [x] 缺少人工 SafetyCheck 时禁止分析。
- [x] 所有非 `NORMAL` Safety 结果在调用 Adapter 前阻断行为分析。
- [x] Safety 阻断页面持续显示联系兽医提示。
- [x] 历史模型结果不能降低或覆盖当前人工 Safety/VeterinaryEscalation。

## E. 用户确认与长期记忆

- [x] 未确认 Claim 仅存在于分析审计区，不进入长期记忆投影。
- [x] 用户可逐条确认或拒绝 Claim。
- [x] 重复或冲突决定被拒绝；确认历史不可静默覆盖。
- [x] 确认不修改 Observation、OwnerInterpretation、Baseline、SafetyCheck 或 Episode 原文。
- [x] 重新分析创建新运行并保留旧版本。

## F. 编辑、删除与可追溯性

- [x] Episode 编辑后旧运行显示 stale，证据快照仍完整。
- [x] 有 AnalysisRun 的 Episode 删除被明确阻止。
- [x] Claim Evidence 可追溯到运行时来源类型、对象、字段和时间。
- [x] 不存在跨宠物或跨 Episode 引用。

## G. 前端体验

- [x] loading、blocked、empty、content、provider error、invalid output、network error、retry 状态齐全。
- [x] Claim、Evidence、Uncertainty 与用户决定使用独立标题和语义结构。
- [x] 模型生成与未确认状态持续可见，不只使用颜色或 toast。
- [x] 保存失败保留当前页面、分析内容和决定操作。
- [x] 分析区位于 Episode 可滚动详情中，操作不被底部导航遮挡。

## H. 测试与交付门禁

- [x] 后端完整测试、前端完整测试和 production build 通过。
- [x] migration current/check、fresh upgrade、downgrade/re-upgrade 通过。
- [x] Adapter contract、Safety short-circuit、非法 Evidence、事务回滚和确认冲突有测试。
- [x] 完成 AI Code Review、修复、回归与污染检查。
- [x] 完成 Slice 2 可运行路径人工验收（2026-10-09；completed/FakeAdapter 分支由自动测试覆盖）。
- [ ] 仅在人工明确授权后 commit；不得自动 push。

## 人工验收主路径

```text
打开一个 NORMAL SafetyCheck 的 Episode
  -> 预览模型输入边界
  -> 发起分析
  -> 查看 Claim / Evidence / Uncertainty / 版本
  -> 确认一条、拒绝一条
  -> AnalysisRun 历史保留每条用户决定且不改写人工记录
  -> 编辑原 Episode 后看到 stale 提示
  -> 重新分析并保留旧运行

打开 ESCALATE_TO_VET 的 Episode
  -> 分析被 Safety 阻断
  -> 未调用模型、未生成行为 Claim
  -> 持续显示联系兽医提示
```
