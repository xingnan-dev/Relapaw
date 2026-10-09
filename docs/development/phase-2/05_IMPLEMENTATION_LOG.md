# Phase 2 Implementation Log

## 2026-10-09 — 编码前审计与实施计划

执行者：Codex
工作类型：只读代码审计、架构设计与文档建立

### Git 与基线

- 审计开始时工作区干净。
- Phase 1 基线为 `05e02e4 feat: complete Relapaw Phase 1 record lifecycle`。
- 数据库 head 为 Phase 1 的 `20261008_0004`；本轮不修改 migration。

### 审计发现

1. **Understand 前端**：当前页面是纯人工记录表单，明确分开 Raw Input、Observation 和 Owner Interpretation，并完成人工 Safety Check 后调用 `POST /episodes/complete`。页面明确声明当前不做 AI 分析。
2. **Safety**：SafetyCheck 是 Episode 一对一人工记录；危险信号由用户主动选择，`ESCALATE_TO_VET` 创建人工 VeterinaryEscalation。没有自动安全规则或医疗分类器。
3. **EvidenceReference**：Phase 1 引用隶属于 Episode，覆盖 Raw Input、Observation、OwnerInterpretation 和 Follow-up，含 source、field_path、observed_at、recorded_at。普通 Episode 编辑会重建这些引用，因此不能直接作为永久 Claim 外键而不保存快照。
4. **Episode 生命周期**：Episode 详情聚合会加载人工子对象；普通编辑不修改 Safety/VeterinaryEscalation；有 Follow-up 的 Episode 已阻止删除。Phase 2 必须增加分析历史删除保护和编辑后的 stale 语义。
5. **长期记忆**：目前仅有人工 Episode 及关联记录，没有模型长期记忆投影。PetBaseline 是人工 JSON 结构，Phase 2 禁止模型更新。
6. **早期 DTO**：`backend/app/schemas/understand.py` 的 `UnderstandResult` 未被任何路由或服务使用。它只有字符串列表，没有 Claim ID、Evidence、版本、确认或审计能力，不能作为 Phase 2 正式契约，应替换而非扩展成模糊大对象。
7. **模型基础设施**：依赖、配置和代码中没有模型 SDK、API key、Adapter、Provider 客户端、异步队列或重试策略。不存在需要保留的隐藏集成。
8. **测试**：当前测试覆盖人工记录、Safety、Evidence、Timeline、Follow-up 和 Observation Plan，但没有 Adapter contract、模型输出验证、确认或分析事务测试。

### 实施切片

#### Slice 1：契约与持久化骨架

- 冻结 UnderstandingInput/Output、Claim、Evidence、Uncertainty、Confirmation 枚举与 schema。
- 新增 Phase 2 Alembic revision 和 ORM 关系。
- 加入详情/列表/确认 API 的纯持久化测试。
- 不接真实 provider。

#### Slice 2：Adapter 与分析服务

- 定义 Adapter Protocol、DisabledAdapter 和测试 FakeAdapter。
- 实现输入构建、Safety short-circuit、Evidence key 校验、输出契约校验、短事务写入与错误映射。
- 选择并隔离一个真实文本 Provider；密钥仅由环境注入。

#### Slice 3：前端 Understanding 结果与确认

- 从 Episode 详情发起分析，展示预览和版本信息。
- 实现 loading/blocked/error/retry、Claim/Evidence/Uncertainty 分区及逐条确认/拒绝。
- 显示历史运行和 stale 状态；不改变 Phase 1 人工编辑表单。

#### Slice 4：记忆投影与最终门禁

- Episode 详情只在“已确认洞见”区域投影 CONFIRMED Claim。
- 加入删除保护、重跑版本历史、并发/idempotency 测试。
- 完整回归、迁移验证、AI Code Review、人工验收和经授权 Git 基线。

### 关键风险

- 模型可能生成语义上越界的诊断或把主人猜测写成事实；结构契约、系统 Prompt、输出审查和 UI 标签都必须共同约束，但不能宣称完全消除语义风险。
- Episode 编辑会让旧分析与当前记录不一致；必须保留输入/证据快照并显式 stale，不能自动重跑。
- 同步 Provider 调用可能超时；MVP 需严格超时和可重试错误，不能持有数据库事务等待网络。
- Provider 选择、数据出境、隐私与成本尚未由用户决定；进入真实 Provider 实现前必须明确配置与数据处理边界。
- Phase 1 文档部分“当时未 commit”的历史表述是时点记录，不应在 Phase 2 中回写历史。

### 本轮实际修改

- 仅新增 Phase 2 开发文档并更新 `docs/development/INDEX.md`。
- 未修改后端、前端、测试、依赖或 migration。
- 未执行功能测试，因为本轮没有功能代码变化；交付前执行 `git diff --check` 与工作区范围核对。

## 2026-10-09 — Slice 1 后端契约与持久化骨架

### 实际架构选择

- 使用独立 `AnalysisRun` 聚合保存不可变输入快照、规范化输出、模型/Adapter 信息和三类契约版本。
- `Claim` 与 Phase 1 的 Observation、OwnerInterpretation 完全分离；每条 Claim 独立保存置信度标签、Evidence 快照和 Uncertainty。
- Claim Evidence 同时保留可空的原 EvidenceReference 外键和不可变来源快照。Episode 编辑重建 Phase 1 Evidence 时，外键置空但历史快照继续可读。
- 人工决定使用一 Claim 一条 `UserConfirmation` 的唯一约束；普通接口不能覆盖既有决定。
- 缺少 SafetyCheck 返回 `SAFETY_CHECK_REQUIRED`；人工 `ESCALATE_TO_VET` 在 Adapter 调用前生成 `BLOCKED_BY_SAFETY` 审计运行。
- 默认 `DisabledAdapter` 返回真实 `MODEL_NOT_CONFIGURED`；FakeAdapter 仅存在于自动测试，没有引入 SDK、密钥或模拟产品结果。
- Episode 一旦存在 AnalysisRun 即返回 `EPISODE_HAS_ANALYSIS`，避免删除破坏审计历史。

### 修改范围

- 新增 migration：`backend/alembic/versions/20261009_0005_text_understanding.py`。
- 新增 Analysis schema、Adapter 协议、Understanding 服务和 API 路由。
- 扩展领域枚举、ORM 模型、模型导出、API router 与 Episode 删除保护。
- 新增 `backend/tests/test_text_understanding.py`，覆盖 10 个关键场景。
- 未修改 Phase 1 migration，未修改前端功能，未 commit、未 push。

### AI Code Review 与修复

- 发现输出 `contract_version` 原为普通字符串，可能接受不兼容版本；改为严格 Literal。
- 发现嵌套 Claim/Evidence/Uncertainty/Confirmation 时间可能以 SQLite naive 时间序列化；统一补 UTC 响应规范化。
- 发现并发确认唯一约束冲突可能退化为通用冲突码；在确认路由映射为 `CLAIM_ALREADY_DECIDED`。
- 发现 ORM 与 migration 对 UserConfirmation 唯一性的声明形式可能导致 Alembic 漂移；统一改为命名唯一约束。

### 尚未完成与风险

- 未选择真实 Provider，也没有 timeout/rate-limit/network 的具体 Provider 映射。
- 尚未实现 Phase 2 前端、Safety 阻断页面、Claim/Evidence/Uncertainty 展示与用户确认交互。
- 尚未实现“已确认洞见”长期记忆读取投影；当前确认只保存审计决定，不写入 Baseline 或其他长期事实表。
- 结构契约能阻止未知字段和未知证据，但真实模型的语义越界仍需 Prompt、输出审查和 UI 标识共同控制。

## 2026-10-09 — Slice 2 前端文本 Understanding 闭环

### 编码前审计

- 保留 Slice 1 的全部未提交修改、migration `20261009_0005`、后端契约测试和 Phase 2 文档；未回退或覆盖既有工作。
- 编码前基线：后端 49 passed、前端 35 passed、production build 通过、数据库处于 `0005 (head)`、Alembic 无漂移、`git diff --check` 通过。

### 实现

- 在 Episode 详情加入独立 Understanding 面板，仅 `NORMAL` SafetyCheck 可发起分析。
- 明确预览 Raw Input、Observation、Owner Interpretation；所有内容只读，不通过分析面板修改 Episode 聚合。
- 覆盖 loading、Safety blocked、MODEL_NOT_CONFIGURED、invalid output、network error、retry、completed 和历史空/读取失败状态。
- completed 运行分区展示 Claim、Evidence、Uncertainty、置信度、模型/Adapter 与三类契约版本；Claim 始终显示“模型生成、尚未确认”。
- 支持逐条 CONFIRMED / REJECTED；确认网络失败时保留完整页面和可重试操作。
- 显示所有 AnalysisRun、错误码和 stale 标记；网络重试复用 request_id，避免响应丢失时重复运行。
- 后端门禁由仅阻断 `ESCALATE_TO_VET` 收紧为仅 `NORMAL` 放行，`NEED_MORE_INFO` 同样不会调用 Adapter。

### 明确未做

- 未接入真实付费模型、SDK、密钥或 Provider；未生成前端伪结果。
- 未引入 RAG、Agent、多模态、自动诊断或自动修改 Baseline/Observation/OwnerInterpretation/Safety/VeterinaryEscalation。
- 未 commit、未 push。

### 人工验收

- 用户在浏览器中确认 NORMAL SafetyCheck Episode 可见文本 Understanding、三类输入预览和分析入口。
- 默认 DisabledAdapter 正确显示 `MODEL_NOT_CONFIGURED`，明确说明失败已记录且没有生成或伪造结果。
- 首轮截图发现 Episode 主操作栏遮挡正文；已将该操作栏改回详情末尾的普通文档流布局。
- 修复后 Safety、Understanding、Evidence、复评关系和详情操作均可滚动查看；用户于 2026-10-09 确认通过。
- 由于本轮明确不接真实 Provider，completed、逐条确认/拒绝和 stale 分支由 FakeAdapter 自动测试验收，不伪造浏览器人工结果。

### 最终代码审查

- 修复已决定 Claim 仍显示“尚未确认”的矛盾文案：PROPOSED、CONFIRMED、REJECTED 现在分别显示对应的模型来源与用户决定。
- 修正文档中超出 Slice 2 范围的“长期记忆投影”人工验收步骤；本轮确认只保存在分析审计聚合中，不写 Baseline 或人工记录。
- 复核 migration/ORM 一致性、Safety short-circuit、失败运行审计、Evidence 边界、事务回滚、确认冲突、Episode 删除保护和前端网络重试，没有发现需要扩展范围的阻断问题。
