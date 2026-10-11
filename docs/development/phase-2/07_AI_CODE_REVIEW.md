# Phase 2 AI Code Review

审查日期：2026-10-11
审查范围：migration `20261009_0005`、AnalysisRun 聚合、Safety 门禁、Provider Adapter、确认 API、Episode 详情前端、测试与 Phase 2 文档。
关联主提交：`f0229ee`

## 结论

未发现未关闭的高危或中危代码问题。Phase 2 可以按当前边界关闭：模型结果始终是待用户决定的 Claim，不修改人工记录、Safety、VeterinaryEscalation 或 Baseline；长期记忆投影不属于本阶段。

## 已审查边界

- Safety：缺少 SafetyCheck 返回 `SAFETY_CHECK_REQUIRED`；`NEED_MORE_INFO` 与 `ESCALATE_TO_VET` 在 Adapter 调用前阻断。
- Evidence：输出只能引用输入快照中的 evidence key；未知或跨 Episode 引用被拒绝。
- 事务：Provider 等待前结束数据库读事务；FAILED/COMPLETED 聚合在短事务中原子保存，不保存部分 Claim。
- stale：Episode 在 Provider 等待期间变化时保留输入与证据快照，避免旧 Claim 错连复用的 EvidenceReference ID。
- Provider：密钥仅存在服务端 SecretStr；timeout、零自动重试、错误归一化、`store=False`（Responses）及无 tools 已覆盖。
- 用户决定：确认/拒绝不可静默覆盖，且不回写 Episode、Observation、OwnerInterpretation、SafetyCheck 或 Baseline。
- 前端：模型来源、尚未确认/用户决定、错误与重试、历史和 stale 均有文本语义，不只依赖颜色。

## 审查中发现并已关闭的问题

1. Provider 等待期间持有数据库读事务：改为输入快照后先结束事务。
2. Episode 并发编辑与 SQLite ID 复用可能造成 Evidence 外键错连：来源变化时仅保留不可变证据快照。
3. 百炼 Responses 忽略 Structured Outputs：Qwen 改走官方支持 JSON Schema 的 Chat Completions，OpenAI 保持 Responses 优先。
4. SDK Pydantic parse 失败未稳定映射：统一为 `MODEL_OUTPUT_INVALID`。
5. 本地真实 `.env` 可能让自动测试误调用 Provider：DisabledAdapter 测试显式依赖注入，全部 Provider 测试使用 mock。
6. 真实 Claim 偏向解释主人决策且未跟随中文：Prompt 升级为 `text-understanding/v3-provider-neutral`。

## 剩余风险

- 模型输出具有非确定性；v3 Prompt 的语言跟随和内容质量仍需持续抽样，而非只依赖契约测试。
- Qwen/OpenAI 兼容行为可能随 Provider 升级变化，需要以 mock 回归加最小人工 smoke test监控。
- 当前主要验证数据库为 SQLite；进入生产前仍需针对 PostgreSQL 做迁移和并发验证。
- SafetyCheck 是人工门禁；错误选择 `NORMAL` 不代表医学安全保证，产品文案必须持续保留该边界。
- 尚未实现成本、延迟和错误率监控；正式部署前应增加预算告警与可观测性。

以上风险均不要求在 Phase 2 内引入 RAG、Agent、多模态、自动诊断或长期记忆写入。
