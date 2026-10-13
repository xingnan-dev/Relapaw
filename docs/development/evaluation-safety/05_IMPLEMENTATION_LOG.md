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

## 2026-10-12 — Slice 2 实施

- 新增 `recorded_outputs_v1.json`，包含 14 个录制案例和 2 个独立版本分组。
- 覆盖 Adapter 的 11 个稳定 Provider 错误码，包括认证、权限、超时、限流、网络、非法/截断输出、拒绝和 Provider 故障。
- 录制输出复用 Slice 1 硬门禁；人工语义 Review 独立记录边界分离、无依据断言和置信度校准。
- 报告按完整 Adapter/模型/Prompt/输入/输出契约版本分组，避免混合不可比结果。
- 运行器固定报告 `recorded_only: true` 和 `network_calls: 0`；未读取密钥、未连接 Provider、未写产品数据库。
- 下一步固定为人工验收门禁；未验收、commit 和 push 前不进入 Slice 3。

## 2026-10-12 — Slice 3 调用前准备

- 冻结 2 个去标识化、非医疗、`NORMAL` Safety 样本，中英文各 1 个。
- 冻结单次执行预算：2 请求、每例最多 800 输出 token、30 秒超时、零重试、零产品数据库写入。
- live runner 默认 dry-run；真实执行需要 CLI `--execute` 与临时环境授权同时存在。
- Adapter 与 Settings 仅在通过执行授权后延迟加载；dry-run 不建立 Provider 客户端。
- FakeAdapter 专项测试覆盖默认零请求、缺少授权拒绝、成功硬门禁和 Provider 失败无重试。
- 当前没有执行真实请求；下一门禁是用户确认预算并单独授权本次真实调用。

## 2026-10-12 — Slice 3 首轮真实评估与修复

- 用户单独授权后执行 2/2 请求，Qwen `qwen3.8-flash`，每例上限 800 输出 token、30 秒超时、零重试、零数据库写入。
- 两例均通过 Schema、Evidence key、禁用内容和语言硬门禁；延迟约 7.25 秒与 7.70 秒。
- 人工 Review 未通过：中文第二条 Claim 将 Owner Interpretation 标为 `SUPPORTS`；英文输出把未记录刺激写为可能触发原因，并推断“判断安全”“完成警戒循环”。
- 首次 Windows stdout 出现中文乱码，影响人工复核，不能视为可接受报告。
- 修复：Prompt 升级为 `v4-evidence-boundary`；新增 `INTERPRETATION_SUPPORT_INVALID` 硬门禁；明确禁止从行为推断未记录刺激和内部状态；CLI 强制 UTF-8 stdout。
- 首轮授权已耗尽，修复后未再次调用 Provider。第二轮必须重新取得相同或更严格预算授权。

## 2026-10-12 — Slice 3 第二轮真实评估与 v5 修复

- 用户重新授权后执行 2/2 请求，仍为 800 输出 token、30 秒超时、零重试、零数据库写入。
- v4 成功修复 Owner Interpretation Evidence 角色：第二轮使用 `CONTEXT`，不再使用 `SUPPORTS`。
- 中文样本返回英文，被确定性门禁标记为 `LANGUAGE_MISMATCH`。
- 中文第二条仍把“主人假设与观察是否吻合”作为 Claim 主体；英文样本仍把“未记录环境刺激或内部状态”写成可能触发原因，人工 Review 未通过。
- UTF-8 stdout 修复有效，第二轮中文输入对应输出可正常审阅。
- 修复：Prompt 升级为 `v5-grounded-claims`；用户消息显式声明输出语言；禁止评价 Owner Interpretation 是否吻合；无法基于记录 Evidence 解释时要求返回空 Claim。
- 第二轮授权已耗尽，v5 尚未进行真实 Provider 验证。

## 2026-10-12 — Slice 3 第三轮真实评估与资格结论

- 用户第三次单独授权后执行 v5 的 2/2 请求，仍为 800 输出 token、30 秒超时、零重试、零数据库写入。
- 两例均通过契约、Evidence key、Interpretation 角色、禁用内容和语言硬门禁。
- 中文输出已跟随语言，但 Claim 主要复述 Observation，并出现“进门后停顿再进入室内”的时间顺序偏移；`HIGH` 也不符合待确认解释的谨慎程度。
- 英文输出继续将未记录的声音或移动写为可能触发原因，违反 Grounded Claim 边界。
- 人工 Review 判定 Qwen `qwen3.8-flash` + `text-understanding/v5-grounded-claims` 为 `NOT_QUALIFIED`。
- 停止继续付费 Prompt 试错。该结论不删除失败证据，也不包装为模型质量通过；如需更换模型或重构契约，进入独立后续 Slice。

## 2026-10-13 — Slice 4 报告与证据收口

- 新增版本化机器摘要 `evaluation_summary_v1.json`，统一引用 Slice 1–3 的冻结指标、预算和资格结论。
- 新增离线摘要校验器，检查期待结果、真实请求预算、零重试、零数据库写入、人工 Review 与资格结论的一致性。
- 摘要中的复现命令仅覆盖离线与 recorded-output 评估，不包含 `--execute`，不会隐式发起真实 Provider 请求。
- 新增最终报告、已知限制和人工 Review 记录；明确自动硬门禁通过不等于语义质量合格。
- 比赛证据映射已同步到真实提交与失败证据；生产监控、漂移检测、成本遥测和新模型重新资格评估仍属于后续工作。
