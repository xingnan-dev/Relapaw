# Phase 2 Prompts

## 2026-10-09 — 审计与计划

用户要求进入 Phase 2 文本 Understanding，本轮只执行：

- 审计 Understand、Safety、EvidenceReference、Episode 和长期记忆边界。
- 制定需求、架构、数据模型、API、前端交互、测试与验收计划。
- 建立 `docs/development/phase-2/` 文档。

明确约束：Observation 与 Interpretation 分离；Claim 不包装成事实；模型输出不直接更新 Observation、Baseline 或长期记忆；保存 Evidence、Uncertainty、模型及 Prompt 契约版本；用户确认后才能进入记忆；Medical Safety 优先；不实现 RAG、Agent、多模态或自动诊断；不修改既有 migration；不编写功能代码；不 commit、不 push。
