# Phase 2 Requirements Analysis

## 问题

Phase 1 已能保存人工结构化记录，但 Understand 仍只承担人工录入。项目尚不能生成与证据绑定的文本理解结果，也没有模型运行版本、Claim、不确定性或用户确认记录。早期 `UnderstandResult` 只包含字符串数组，无法证明某项解释使用了哪些来源，也无法区分模型草稿和已确认长期记忆。

## 用户价值

- 用户可从已保存 Episode 发起一次文本分析，而不是让分析和原始记录混在一次写入中。
- 每条解释明确标为 Claim，展示支持或限制它的证据和未知信息。
- 用户可确认或拒绝每条 Claim；未确认内容不会出现在长期记忆视图。
- 相同输入的每次运行保留模型、Prompt 契约和输出契约版本，便于审计与未来评估。
- Safety 优先：人工 Safety Check 表示需要联系兽医时，不生成行为解释来分散注意力。

## 核心规则

1. Observation、OwnerInterpretation、Model Claim、UserConfirmation 是四类不同对象。
2. Adapter 输入必须使用带类型标签的数据，禁止把 OwnerInterpretation 当作 Observation。
3. Claim 必须至少包含 statement、claim_type、Evidence 和 Uncertainty；没有足够证据时可以返回“无法形成 Claim”，不能补写事实。
4. 不使用伪精确概率或情绪分数。可信度采用有限的定性枚举，例如 `LOW / MEDIUM / HIGH`，且不能替代不确定性说明。
5. 模型只能引用本次输入中提供的证据键；服务端拒绝未知、跨 Episode 或跨宠物引用。
6. 模型输出先进入分析审计区。只有用户明确 `CONFIRMED` 的 Claim 才进入长期记忆投影；`REJECTED` 与未决 Claim 保留审计但不进入投影。
7. 确认 Claim 不会创建或修改 Observation、OwnerInterpretation、PetBaseline、SafetyCheck 或 VeterinaryEscalation。
8. 人工 Safety Check 缺失时禁止运行；结果为 `ESCALATE_TO_VET` 时创建被 Safety 阻断的 AnalysisRun，不调用模型、不生成行为 Claim。
9. 不输出诊断、处方、治疗方案、动物心理确诊或因果定论。
10. 不使用 RAG、外部知识库、Agent 工具调用、媒体输入或自动长期趋势。

## 主要用户故事

### 发起分析

用户从 Episode 详情或 Understand 的已保存记录入口发起分析。页面先展示将发送的原始输入、Observation、Owner Interpretation 和人工 Safety 状态。用户明确确认后才请求模型。

### 查看结果

结果按 Claim 卡片展示：声明、类型、定性可信度、证据来源、限制证据、不确定性和“模型生成、尚未确认”状态。原始输入、Observation 与 Owner Interpretation 仍为独立只读分区。

### 确认或拒绝

用户可逐条确认、拒绝或暂不处理。确认动作记录 Claim 版本、决定和时间。已决定的版本不可静默覆盖；重新分析生成新的 AnalysisRun。

### 失败与重试

Provider 未配置、超时、限流、返回非法结构或网络失败时，输入与既有 Episode 不变。失败运行保留安全的错误码和版本元数据，不保存密钥、堆栈或供应商敏感原文；用户可以显式重试并产生新运行。

## 非目标

- 不自动拆分或改写用户原始文本为 Observation。
- 不把模型 Claim 写入 Timeline 作为 Episode。
- 不计算 Baseline、趋势、异常分数或“爱/焦虑”等指标。
- 不检索兽医知识，不生成引用文献，不调用外部工具。
- 不做异步任务队列、流式输出、推送通知或多模型编排。
