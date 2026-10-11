# Phase 2 Development Record

Phase：文本 Understanding
启动日期：2026-10-09
状态：已完成实现、真实 Provider 验证、人工验收与 Git 交付；进入 Phase 2 收尾

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
  -> UserConfirmation 不可变审计
  -> Phase 3 再定义长期记忆投影
```

模型输出不是 Observation，不覆盖主人原始解释，也不自动更新 Baseline。AnalysisRun 与 UserConfirmation 是审计数据；本阶段无论确认或拒绝都不自动写入长期记忆投影。

## 导航

- [需求分析](01_REQUIREMENTS.md)
- [架构决策](02_ARCHITECTURE_DECISIONS.md)
- [Scope 与验收条件](03_SCOPE_ACCEPTANCE.md)
- [本轮 Prompt](04_PROMPTS.md)
- [审计与实施计划](05_IMPLEMENTATION_LOG.md)
- [测试计划与结果](06_TEST_RESULTS.md)
- [AI Code Review](07_AI_CODE_REVIEW.md)
- [修复与回归](08_FIX_AND_REGRESSION.md)
- [人工验收](09_ACCEPTANCE.md)

## 当前边界

- 已接入官方 OpenAI Python SDK；OpenAI 使用 Responses Structured Outputs，Qwen 使用百炼 OpenAI-compatible Chat Completions JSON Schema。模型由 `RELAPAW_OPENAI_MODEL` 配置，密钥只从服务端 `OPENAI_API_KEY` 读取。
- 未修改任何既有 migration；新增 revision `20261009_0005`。
- 已完成后端契约、持久化、仅 NORMAL 放行的 Safety 门禁、审计/确认 API，以及 Episode 详情内的前端分析、历史、stale 与逐条决定闭环。
- 缺少 key 或 model 时仍使用 DisabledAdapter 并明确返回 `MODEL_NOT_CONFIGURED`，不生成替代结果。
- Provider 请求禁用工具与服务端存储，使用严格 timeout、零 SDK 自动重试和稳定错误映射；本轮不接 RAG、Agent、多模态或诊断。
- 主实现已提交并推送为 `f0229ee`；本收尾文档与 v3 Prompt 约束增强等待单独授权提交。
