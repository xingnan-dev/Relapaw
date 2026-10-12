# Evaluation 与 Safety 评估体系

状态：Slice 1–2 已关闭并推送；Slice 3 三轮真实评估完成，当前 Qwen/v5 组合判定为 `NOT_QUALIFIED`，等待人工验收

本阶段把 Phase 2 的 Prompt/Safety 边界转化为版本化、可重复执行的评估资产。评估结果用于发现回归，不自动修改产品数据、Prompt 或用户决定。

当前门禁：不再通过无上限 Prompt 迭代追求“全绿”。三轮结果和模型资格结论需人工验收；后续更换模型、契约或新增真实调用必须另立 Slice 并重新授权。

- [需求](01_REQUIREMENTS.md)
- [架构决策](02_ARCHITECTURE_DECISIONS.md)
- [范围与验收](03_SCOPE_ACCEPTANCE.md)
- [评估说明](04_EVALUATION_PROTOCOL.md)
- [实施日志](05_IMPLEMENTATION_LOG.md)
- [测试结果](06_TEST_RESULTS.md)
