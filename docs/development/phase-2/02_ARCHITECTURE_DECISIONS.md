# Phase 2 Architecture Decisions

## 1. 分析是独立聚合

`Episode` 继续是人工记录聚合根；`AnalysisRun` 是独立、只追加的分析聚合。它引用一个 Episode，但不能写回 Episode 的 Observation、OwnerInterpretation、SafetyCheck 或 Baseline。

```text
Episode
  ├─ Observation[]
  ├─ OwnerInterpretation[]
  ├─ SafetyCheck
  └─ AnalysisRun[]
       ├─ Claim[]
       │    ├─ ClaimEvidenceReference[]
       │    ├─ Uncertainty[]
       │    └─ UserConfirmation[]
       └─ input/output/version metadata
```

## 2. 建议数据模型

### AnalysisRun

- `id`
- `episode_id`
- `status`: `PENDING | COMPLETED | FAILED | BLOCKED_BY_SAFETY`
- `adapter_name`
- `model_provider`
- `model_name`
- `model_version`
- `prompt_contract_version`
- `input_contract_version`
- `output_contract_version`
- `input_snapshot`：带明确类型标签的最小 JSON 快照
- `normalized_output`：通过契约验证后的 JSON，不保存 chain-of-thought
- `error_code`：安全、稳定的内部码，不保存密钥或供应商堆栈
- `created_at / completed_at`

### Claim

- `id / analysis_run_id`
- `claim_type`
- `statement`
- `confidence_label`: `LOW | MEDIUM | HIGH`
- `status`: `PROPOSED | CONFIRMED | REJECTED`
- `created_at`

Claim 状态是便于查询的投影，真实决定历史由 UserConfirmation 保存。

### ClaimEvidenceReference

- `id / claim_id`
- `evidence_reference_id?`：指向 Phase 1 来源，允许来源变更后置空
- `source_type / source_id / field_path`
- `observed_at / recorded_at`
- `excerpt?`
- `role`: `SUPPORTS | LIMITS | CONTEXT`

这里保存运行时不可变证据快照，避免 Phase 1 编辑重建 EvidenceReference 后造成历史 Claim 悬空。快照只证明“模型当时看到了什么”，不把 Claim 变成事实。

### Uncertainty

- `id / claim_id`
- `kind`: `MISSING_CONTEXT | ALTERNATIVE_EXPLANATION | LIMITED_OBSERVATION | OTHER`
- `description`

### UserConfirmation

- `id / claim_id`
- `decision`: `CONFIRMED | REJECTED`
- `note?`
- `created_at`

同一 Claim 只允许一个最终决定。需要修订时重新运行分析，不覆盖历史决定。

## 3. LLM Adapter 边界

服务层只依赖协议，不直接导入供应商 SDK：

```text
UnderstandingService
  -> TextUnderstandingAdapter.analyze(UnderstandingInput) -> UnderstandingOutput
```

- 默认 `DisabledAdapter` 返回 `MODEL_NOT_CONFIGURED`，不得伪造分析结果。
- 测试使用注入的 FakeAdapter，只验证契约和事务，不在产品 UI 展示假结果。
- 真实 Provider 使用官方 OpenAI Python SDK 的 Responses API 与 `responses.parse(..., text_format=UnderstandingOutput)`；Structured Outputs 之后仍执行应用侧 Pydantic 和 Evidence key 校验。
- `OpenAIResponsesAdapter` 不配置 tools、检索或媒体输入，设置 `store=False`，禁用 SDK 自动重试，并使用单次严格 timeout。
- 密钥只从服务端 `OPENAI_API_KEY`（兼容 `RELAPAW_OPENAI_API_KEY`）读取，模型由 `RELAPAW_OPENAI_MODEL` 指定；二者任一缺失即回退 DisabledAdapter。
- 默认使用 SDK 的 OpenAI 官方端点；`RELAPAW_OPENAI_BASE_URL` 可显式指向实现 Responses API 的兼容端点（当前文档化实例为阿里云百炼 Qwen），`RELAPAW_MODEL_PROVIDER` 作为审计元数据保存，不通过 URL 猜测供应商。
- OpenAI Provider 使用 Responses `parse`。百炼官方 Responses 参数表未包含 `text.format/json_schema` 且真实验证会忽略该参数，因此 `model_provider=qwen` 改走百炼官方明确支持 JSON Schema 的 OpenAI-compatible Chat Completions `parse`，并关闭 thinking；两条路径最终都必须通过同一 UnderstandingOutput Pydantic 校验。
- 请求保存配置模型名，并在响应提供 `model` 时把实际解析到的模型标识保存为 model_version；密钥和供应商错误原文不持久化。
- Adapter 输出必须先通过 Pydantic 契约验证，再进入事务。
- Provider 原始 chain-of-thought 不请求、不保存、不展示。

## 4. Safety 门禁顺序

```text
require Episode
  -> require SafetyCheck
  -> SafetyCheck != NORMAL ? BLOCKED_BY_SAFETY : build typed input
  -> Adapter
  -> validate evidence keys and forbidden output shape
  -> persist AnalysisRun aggregate
```

Safety 阻断不调用 Adapter。`NORMAL` 不表示医学安全保证，只表示用户在 Phase 1 人工确认时未选择所列紧急情况。Phase 2 不新增关键词医疗规则。

## 5. API 契约

建议端点：

- `POST /api/v1/episodes/{episode_id}/analysis-runs`
  - 同步 MVP；成功返回 `201` 完整运行。
  - Safety 阻断返回持久化的 `BLOCKED_BY_SAFETY` 运行，不生成 Claim。
- `GET /api/v1/episodes/{episode_id}/analysis-runs`
  - 按 `created_at DESC, id DESC` 返回历史，严格宠物/父记录隔离。
- `GET /api/v1/analysis-runs/{run_id}`
  - 返回版本、Claim、Evidence、Uncertainty 与确认状态。
- `POST /api/v1/claims/{claim_id}/confirmations`
  - 明确提交 `CONFIRMED` 或 `REJECTED`；重复或冲突决定返回 409。

统一错误至少包括：`ANALYSIS_RUN_NOT_FOUND`、`CLAIM_NOT_FOUND`、`SAFETY_CHECK_REQUIRED`、`ANALYSIS_BLOCKED_BY_SAFETY`、`MODEL_NOT_CONFIGURED`、`MODEL_AUTHENTICATION_FAILED`、`MODEL_PERMISSION_DENIED`、`MODEL_TIMEOUT`、`MODEL_RATE_LIMITED`、`MODEL_NETWORK_ERROR`、`MODEL_PROVIDER_UNAVAILABLE`、`MODEL_REQUEST_REJECTED`、`MODEL_REFUSED`、`MODEL_OUTPUT_INCOMPLETE`、`MODEL_OUTPUT_INVALID`、`MODEL_EVIDENCE_INVALID`、`CLAIM_ALREADY_DECIDED`、`EPISODE_HAS_ANALYSIS`。

## 6. 编辑与删除策略

- Episode 编辑后，既有 AnalysisRun 标记为 `STALE` 或通过计算字段显示“来源记录已更新”；历史 input/evidence 快照保持不变。
- Episode 存在 AnalysisRun 时禁止物理删除，返回 `EPISODE_HAS_ANALYSIS`，避免破坏审计链。
- AnalysisRun、Claim、Evidence 快照与确认记录不提供普通编辑或删除接口。
- 重新分析始终创建新 AnalysisRun，不覆盖旧运行。

实现前需在状态枚举中加入 `STALE`，或明确采用 `source_episode_updated_at` 与当前更新时间比较的计算方案。建议采用计算方案，减少状态写入竞争。

## 7. 前端状态

Episode 详情增加“文本 Understanding”区域：

- 尚未分析：解释边界、预览输入、明确发起按钮。
- Safety 阻断：持续显示联系兽医提示，不显示行为 Claim。
- loading：显示正在分析且不清空原记录。
- provider/error：页面内错误、错误码友好文案、显式重试。
- completed：Claim / Evidence / Uncertainty 分区展示。
- confirmation：逐条确认或拒绝，二次确认后锁定决定。
- stale：明确提示来源 Episode 后续已编辑，可发起新分析。
- history：可查看旧运行与版本，不把旧 Claim 冒充当前结论。

## 8. 事务边界

- Adapter 调用发生在数据库写事务之外，避免长事务占用连接。
- 运行请求先构建不可变输入；Provider 成功且输出验证通过后，在一个短事务中保存 AnalysisRun、Claim、Evidence 快照和 Uncertainty。
- Provider 失败保存独立 FAILED 运行；不得留下部分 Claim。
- 用户确认在单独事务中插入 UserConfirmation 并更新 Claim 查询投影。

并发实现阶段需选择 request token / idempotency key 或数据库唯一约束，防止双击产生无法区分的重复运行。MVP 建议客户端生成 `request_id`，在 Episode 内唯一。
