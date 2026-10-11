# Phase 2 Acceptance

验收日期：2026-10-09 至 2026-10-11
主实现提交：`da08fbc`、`f0229ee`

## 自动验收

- NORMAL Episode 可发起分析；非 NORMAL 与缺失 SafetyCheck 在 Provider 前阻断。
- Raw Input、Observation、Owner Interpretation 分离进入版本化输入快照。
- completed 分区展示 Claim、Evidence、Uncertainty、置信度、Provider、模型及契约版本。
- loading、Safety blocked、MODEL_NOT_CONFIGURED、invalid output、network/provider error、retry、completed、history 与 stale 均有覆盖。
- 用户可以逐条确认或拒绝；失败不丢失当前分析页面状态。
- AnalysisRun/Claim/UserConfirmation 不修改 Observation、OwnerInterpretation、Baseline、SafetyCheck、VeterinaryEscalation 或 Episode 原文。

## 真实 Provider 验收

1. 初始未配置状态真实返回 `MODEL_NOT_CONFIGURED`，没有伪造结果。
2. Qwen Responses 最小请求暴露 Structured Outputs 不兼容，结果未保存为 completed。
3. 切换到百炼 Chat Completions JSON Schema 后，最小 smoke test约 6 秒完成：`understanding-output/v1`、1 条 Claim、Evidence key 合法。
4. 浏览器从人工 SafetyCheck=`NORMAL` 的 Episode 发起真实分析，AnalysisRun #3 为 COMPLETED，并显示：
   - `qwen / qwen3.8-flash / qwen3.8-flash`
   - `qwen-openai-chat-completions`
   - Claim、Evidence、Uncertainty、MEDIUM 置信度与契约版本
5. 历史中 `MODEL_NOT_CONFIGURED` 和 `MODEL_NETWORK_ERROR` 失败运行继续保留，没有部分 Claim。
6. 用户将真实 Claim 标记为 REJECTED；刷新并重新打开 Episode 后决定仍存在，页面明确说明不会改写原始记录。

## 人工决定与产品反馈

- 首条真实 Claim 因偏向解释“主人为何联系兽医”而被人工拒绝；这是有效的产品决定，不是将模型输出视为事实。
- 该反馈促成 v3 Prompt：Claim 聚焦 Episode 行为、避免复述、跟随输入语言、未记录背景只能作为不确定性。
- v3 Prompt 已通过自动契约回归，但未额外产生付费请求；语言与内容质量列为持续抽样项，不阻断 Phase 2 关闭。

## 验收结论

Phase 2 通过。系统实现的是可追溯、可失败、可拒绝的文本 Understanding，而不是诊断或自动事实生成器。确认/拒绝仅形成 UserConfirmation 审计；Phase 3 才定义长期记忆投影和量化 Baseline。
