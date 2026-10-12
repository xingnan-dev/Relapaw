# Scope and Acceptance

## Slice 1：离线确定性评估基线

- [x] 版本化 JSON 数据集覆盖正常、非 NORMAL、非法 Evidence、越界内容和语言不跟随。
- [x] 运行器复用 `UnderstandingInput/Output`，输出稳定错误码与汇总指标。
- [x] 测试证明运行器无 Adapter/网络依赖，并能识别期待结果漂移。
- [x] CLI 可重复生成机器可读 JSON 报告。

## Slice 2：Provider mock 与 recorded-output 评估

- [x] 覆盖所有稳定 Provider 错误码、非法 JSON、拒绝和截断。
- [x] 覆盖 Observation/Interpretation 冲突、信息不足、无依据断言与过度确定。
- [x] 报告按 Prompt/模型/契约版本分组，不混合不可比结果。

## Slice 3：最小真实 Provider 评估

- [x] 仅在明确授权后运行，限定样本数、超时和费用边界。
- [x] 记录延迟、成功率、Schema/Evidence/Safety 指标，不保存密钥或敏感数据。
- [x] 失败不会污染产品数据库或自动改变 Prompt。

## Slice 4：报告与比赛证据

- [ ] 形成可复现报告、已知限制和人工 Review 记录。
- [ ] 映射比赛 AI 原生开发、安全和人机协作证据。
- [ ] 完整回归、Review、人工验收、commit/push 门禁通过。

## 阶段出口

- [ ] 数据集与报告有明确版本。
- [ ] 硬门禁指标 100%；行为指标有阈值和人工复核。
- [ ] 不把词法评估描述为医学或语义正确性保证。
- [ ] 未授权时零真实 Provider 请求。
