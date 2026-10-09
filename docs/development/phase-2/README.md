# Phase 2 Development Record

Phase：文本 Understanding
启动日期：2026-10-09
状态：Slice 2 前端文本 Understanding 闭环完成；真实 Provider 暂不接入

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

- 未选择或安装模型 SDK，不配置真实密钥；默认 Adapter 明确返回 `MODEL_NOT_CONFIGURED`。
- 未修改任何既有 migration；新增 revision `20261009_0005`。
- 已完成后端契约、持久化、仅 NORMAL 放行的 Safety 门禁、审计/确认 API，以及 Episode 详情内的前端分析、历史、stale 与逐条决定闭环。
- 产品默认 Adapter 仍明确返回 `MODEL_NOT_CONFIGURED`；completed UI 仅由后端合法运行（自动测试中为 FakeAdapter）驱动，不生成前端伪结果。
- 本阶段修改保持未提交，不 push。
