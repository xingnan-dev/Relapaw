# Phase 2 Prompts

## 2026-10-09 — 审计与计划

用户要求进入 Phase 2 文本 Understanding，本轮只执行：

- 审计 Understand、Safety、EvidenceReference、Episode 和长期记忆边界。
- 制定需求、架构、数据模型、API、前端交互、测试与验收计划。
- 建立 `docs/development/phase-2/` 文档。

明确约束：Observation 与 Interpretation 分离；Claim 不包装成事实；模型输出不直接更新 Observation、Baseline 或长期记忆；保存 Evidence、Uncertainty、模型及 Prompt 契约版本；用户确认后才能进入记忆；Medical Safety 优先；不实现 RAG、Agent、多模态或自动诊断；不修改既有 migration；不编写功能代码；不 commit、不 push。

## 2026-10-09 — OpenAI Provider Prompt Contract v2

`text-understanding/v2-openai` 的系统 Prompt 固定以下边界：

- 仅基于传入 Episode JSON 生成等待用户确认的可能解释，不把 Claim 表述为事实。
- 不诊断，不提供治疗、药物或剂量建议，不建议延误兽医处理。
- Raw Input、Observation、Owner Interpretation 分开；主人解释不是观察事实。
- Evidence 只能引用输入中已有的 `evidence_key`，不得使用外部知识或隐含来源。
- 每条 Claim 必须包含 Evidence 与有意义的 Uncertainty。
- 置信度仅允许 LOW/MEDIUM/HIGH，不生成数值概率、情绪分数或关系评分。
- 不调用工具、检索、图片或隐藏上下文，不重新解释或降低人工 SafetyCheck。

## 2026-10-11 — Provider-neutral Prompt Contract v3

`text-understanding/v3-provider-neutral` 保留 v2 的全部 Safety、Evidence 与不诊断边界，并新增：

- Claim 必须聚焦 Episode 中记录的行为或 Observation 本身，不得把主人为何担忧、为何联系兽医或如何措辞作为 Claim 主体。
- 不得只复述输入；必须提供谨慎、可供用户核对且有实际理解价值的可能解释。
- 面向用户的 Claim 与 Uncertainty 跟随 Raw Input 的自然语言；枚举值与契约字段保持稳定。
- 未记录的环境或背景只能作为明确的缺失信息或不确定性，不得作为支持证据或已经成立的原因。
- OpenAI Responses 与 Qwen Chat Completions 共用此 Prompt 契约及相同的 Pydantic 输出校验。
