# Phase 2 Development Record

Phase：文本 Understanding
启动日期：2026-10-09
状态：Slice 3 OpenAI Responses Provider 已实现，等待配置凭据后的人工 smoke test

## 阶段目标

在不引入 RAG、Agent、多模态或自动诊断的前提下，让用户针对一个已有 Episode 请求文本分析，并获得结构化、可追溯、明确表达不确定性的结果：

```text
人工 Episode + Observation + Owner Interpretation + Safety Check
  -> Medical Safety 门禁
  -> 版本化 LLM Adapter
  -> AnalysisRun
       -> Claim
       -> ClaimEvidenceReference[]
       -> Uncertainty[]
  -> 用户逐条确认 / 拒绝
  -> 只有确认结果进入长期记忆投影
```

模型输出不是 Observation，不覆盖主人原始解释，也不自动更新 Baseline。分析运行记录为审计数据；未确认 Claim 不进入长期记忆视图。

## 导航

- [需求分析](01_REQUIREMENTS.md)
- [架构决策](02_ARCHITECTURE_DECISIONS.md)
- [Scope 与验收条件](03_SCOPE_ACCEPTANCE.md)
- [本轮 Prompt](04_PROMPTS.md)
- [审计与实施计划](05_IMPLEMENTATION_LOG.md)
- [测试计划与结果](06_TEST_RESULTS.md)

## 当前边界

- 已接入官方 OpenAI Python SDK 与 Responses Structured Outputs；模型由 `RELAPAW_OPENAI_MODEL` 配置，密钥只从服务端 `OPENAI_API_KEY` 读取。
- 未修改任何既有 migration；新增 revision `20261009_0005`。
- 已完成后端契约、持久化、仅 NORMAL 放行的 Safety 门禁、审计/确认 API，以及 Episode 详情内的前端分析、历史、stale 与逐条决定闭环。
- 缺少 key 或 model 时仍使用 DisabledAdapter 并明确返回 `MODEL_NOT_CONFIGURED`，不生成替代结果。
- Provider 请求禁用工具与服务端存储，使用严格 timeout、零 SDK 自动重试和稳定错误映射；本轮不接 RAG、Agent、多模态或诊断。
- Slice 3 修改保持未提交，不 push。
