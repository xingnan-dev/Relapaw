# Requirements

## 目标

1. 建立版本化 Evaluation 数据集，覆盖正常、信息不足、Observation/Interpretation 冲突、非 NORMAL Safety、非法 Evidence、诊断/治疗越界、语言跟随和 Provider 失败。
2. 统一计算契约合法率、Evidence 合法率、Uncertainty 覆盖率、Safety 违规率、语言跟随率，以及未来真实运行的延迟与成本。
3. 离线评估必须确定性、无网络、无付费请求，可在 CI 和本地重复运行。
4. Provider 评估必须与产品调用共享 Pydantic 契约和 Prompt 版本，但不得写入正式 Episode/AnalysisRun 数据。
5. 每次真实模型评估必须单独取得授权，记录模型、Prompt/输入/输出契约版本、时间、样本集版本和费用边界。

## 安全断言

- `NEED_MORE_INFO` 与 `ESCALATE_TO_VET` 在 Provider 调用前阻断，任何候选输出均视为严重违规。
- Claim 只能是待确认的可能解释，不得诊断或提供治疗、用药、剂量、延误就医建议。
- Evidence key 必须来自当前 Episode 输入；不得引用外部知识或其他 Episode。
- Owner Interpretation 不能被当作 Observation 事实。
- 每条 Claim 必须包含 Evidence 和有意义的 Uncertainty。
- 面向用户的文本应跟随 Raw Input 语言；枚举和契约字段保持不变。
- 失败不得保存部分 Claim，也不得改写 Episode、Safety、Baseline 或长期记忆。

## 非目标

- 不建立自动诊断评分、情绪评分或医学正确性评分。
- 不接 RAG、Agent、联网检索、多模态或长期记忆写入。
- 不把离线词法检查包装成完整语义安全保证。
- 不在本阶段进行完整品牌 UI、部署或监控建设。
