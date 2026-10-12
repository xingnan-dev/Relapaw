# Implementation Log

## 2026-10-12 — 启动审计

- 现有 Pydantic `UnderstandingInput/Output` 已强制严格字段、Evidence/Uncertainty 最小数量和枚举。
- `understanding.py` 已在持久化前验证 Evidence key；非 NORMAL Safety 已在 Adapter 前阻断。
- Adapter mock 测试已覆盖认证、权限、超时、限流、网络、拒绝、截断、非法响应和 Provider 错误映射。
- 主要缺口是版本化跨案例数据集、统一指标、期待结果漂移检查和独立报告。
- Slice 1 固定为无网络、无数据库、无 Provider 的确定性评估基线。

## 2026-10-12 — Slice 1 实施

- 新增 `backend/evals/text_understanding_v1.json`，冻结 9 个中英文、契约、Evidence、Safety 与语言案例。
- 新增 `app.evaluation.text_understanding` 离线运行器；不导入 Adapter，不读取 API Key，不访问网络或产品数据库。
- 稳定错误码：`SAFETY_OUTPUT_PRESENT`、`OUTPUT_MISSING`、`CONTRACT_INVALID`、`EVIDENCE_INVALID`、`PROHIBITED_CONTENT`、`LANGUAGE_MISMATCH`。
- CLI 以 JSON 输出逐案例结果和总匹配率；仅在全部冻结期待匹配时返回成功退出码。
- 下一步固定为人工验收门禁；未验收前不进入 Slice 2。
