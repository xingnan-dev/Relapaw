# 人与 AI 交互案例

本文件只记录已有代码、日志、测试和人工验收可以证明的案例。它不是逐字聊天导出，也不补造缺失对话。

## Case 1：从产品边界到可执行 Phase

**人类目标**：建立“记录 → 观察 → 复评 → 长期记忆”的路线，同时坚持 Observation 与 Owner Interpretation 分离。

**AI 工作**：审计 Phase 0 基线，把 Phase 1 拆为原子创建、Timeline 管理、人工 Safety、Follow-up、Observation Plan、Evidence 与完整回归七个切片。

**人类控制**：明确 Phase 1 禁止 LLM、诊断和自动 Safety；commit/push 必须另行授权。

**结果**：形成 Phase 1 开发文档，并在提交 `05e02e4` 完成结构化记录闭环。

**价值**：AI 不只是生成代码，而是把产品原则转成可测试的数据库、API 和 UI 契约。

## Case 2：模型兼容假设被真实请求推翻

**初始方案**：OpenAI 与 Qwen 都尝试走 Responses Structured Outputs。

**真实证据**：经用户逐次授权的最小 Qwen 请求返回 Markdown，未满足 UnderstandingOutput；系统安全映射为 `MODEL_OUTPUT_INVALID`，没有保存 completed 或部分 Claim。

**AI 调查与修复**：核对 Provider 官方能力后，为 Qwen 增加 OpenAI-compatible Chat Completions JSON Schema 路径，同时保持 OpenAI Responses；两者仍经过同一 Pydantic 和 Evidence key 校验。

**再次授权验收**：新的最小请求约 6 秒完成，返回 1 条契约合法 Claim；浏览器端 AnalysisRun #3 为 COMPLETED。

**证据**：Phase 2 的 Implementation Log、Test Results、Fix and Regression，提交 `f0229ee`。

**价值**：AI 提出的实现必须接受官方文档、真实行为和应用契约三重校验。

## Case 3：契约合法不等于产品质量合格

**模型结果**：首条真实 Claim 通过 JSON、Pydantic 和 Evidence 校验，但偏向解释“主人为什么联系兽医”，且中文输入返回英文。

**人类决定**：用户在产品中将 Claim 标记为 REJECTED；刷新后决定仍存在，原始 Episode 未被改写。

**AI 改进**：Prompt 升级为 `text-understanding/v3-provider-neutral`，要求聚焦 Episode 行为、避免复述、跟随输入语言，并把未记录背景限制为 Uncertainty 而非 Evidence。

**后续真实评估**：首轮最小 Provider 评估又发现 Owner Interpretation 被作为支持事实，以及未记录刺激和内部状态被写入 Claim。人工拒绝该结果后，Prompt 升级为 `text-understanding/v4-evidence-boundary`，并新增 Interpretation Evidence 硬门禁。这一失败—复核—修复链路保留为 AI 原生开发证据。

**第二轮复核**：v4 修正了 Interpretation 的 Evidence 角色和报告编码，但模型仍未跟随中文，并继续猜测未记录原因。人工再次拒绝，Prompt 升级为 `text-understanding/v5-grounded-claims`，加入显式语言指令与“证据不足则返回空 Claim”规则。

**资格结论**：第三轮 v5 通过全部确定性硬门禁，但人工仍发现中文时间顺序偏移和英文无依据原因。团队没有把结构化输出成功包装成模型质量成功，而是将该组合标记为 `NOT_QUALIFIED` 并停止无上限付费试错。这展示了 AI 输出、自动评估和人工最终决定之间的清晰权责边界。

**边界**：未擅自发起第二次付费请求；v3 先通过自动契约测试，语义质量保留为后续 Evaluation 抽样项。

**证据**：Phase 2 Prompt 与 Acceptance 文档。

**价值**：用户拒绝不是系统失败，而是 Human-in-the-loop 的必要控制信号。

## Case 4：AI Code Review 发现并发与数据血缘风险

**风险**：Provider 等待期间数据库读事务未结束；Episode 若同时编辑，SQLite ID 复用还可能让旧 Claim 的 Evidence 外键误连新行。

**AI Review**：识别事务边界和 ORM identity cache 问题，增加“Provider 等待期间编辑 Episode”回归。

**修复**：输入快照后结束读事务；保存前刷新来源更新时间；来源变化时 Evidence 外键置空，只保留不可变快照并标记 stale。

**证据**：Phase 2 AI Code Review 与 Provider/Understanding 测试。

**价值**：AI 被用于审查并修正自身实现，而不以“测试曾经通过”作为结束条件。

## Case 5：前端人工验收推动布局修复

**自动测试状态**：Phase 2 前端状态测试通过。

**人工发现**：浏览器长页面中 Episode 主操作栏遮挡正文。

**AI 修复**：将操作栏恢复到详情末尾的普通文档流；保留底部一级导航。

**人工复验**：Safety、Understanding、Evidence、复评关系和详情操作可滚动查看，用户确认通过。

**证据**：Phase 2 Implementation Log 的 Slice 2 人工验收记录。

**价值**：自动测试与真实视觉验收互补，AI 不能仅凭测试结果宣布体验完成。
