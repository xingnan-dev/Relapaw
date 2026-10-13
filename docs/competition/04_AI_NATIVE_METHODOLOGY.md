# Relapaw 的 AI 原生软件开发方法论

## 定义

Relapaw 的“AI 原生”不是把聊天框附加到传统应用，也不是把所有决定交给模型。它包含两个彼此独立但可追溯的层面：

1. **AI 参与完整开发生命周期**：从需求、架构、实现、测试、Review、修复、验收到证据维护；
2. **产品以不确定性为一等数据**：模型输出具有版本、Evidence、Uncertainty、失败审计和人工决定，不自动成为事实。

## 七项原则

### 人类目标，AI 执行，证据裁决

人类确定目标和不可越界项；AI 提出并执行方案；代码、测试、真实运行和人工验收共同判断是否完成。

### 先契约，后模型

先定义 UnderstandingInput/Output、Evidence key、版本与错误语义，再接 Provider。模型不能决定数据库结构或绕过应用验证。

### Safety 在 Provider 之前

只有人工 SafetyCheck=`NORMAL` 才调用模型；`NEED_MORE_INFO` 和 `ESCALATE_TO_VET` 在网络请求前阻断。Safety 是可测试的服务门禁，不只是 Prompt 提醒。

### 模型建议与事实分层

Raw Input、Observation、Owner Interpretation、Claim 和用户决定分别保存。Claim 始终是待确认解释；即使 CONFIRMED，也不自动改写人工记录或 Baseline。

### 失败可见、可审计、可重试

配置、认证、超时、限流、网络、Provider、拒绝、截断和非法输出均映射稳定状态。失败 AnalysisRun 保留，但不保存部分 Claim。

### AI 审查 AI 生成物

实现后必须单独进行 AI Code Review，再修复和完整回归。Review 重点包含数据血缘、事务、并发、隐私、Safety、迁移和 UI 误导风险。

### 人工授权外部副作用

真实付费请求、commit 和 push 使用独立人工授权。AI 可以准备动作和验证条件，不能把一次授权扩大到之后的不同操作。

## 生命周期中的 AI 嵌入点

| 生命周期 | AI 的作用 | 人类门禁 |
|---|---|---|
| 发现 | 审计现状、识别缺口与约束冲突 | 确认目标和优先级 |
| 设计 | 生成 Requirement/ADR/Scope/Acceptance 草案 | 决定产品与安全边界 |
| 开发 | 按垂直切片实现代码、迁移和测试 | 处理方向性选择 |
| 验证 | 运行测试/build/migration、分析失败 | 授权真实付费 smoke test |
| Review | 检查 AI 自身生成代码与文档 | 接受或要求继续修复 |
| 体验 | 支持浏览器验收和问题定位 | 执行真实用户决定 |
| 交付 | 更新证据、检查密钥/产物、准备提交 | 分别授权 commit/push |
| 运营 | 版本化 Evaluation 已完成；监控、漂移和成本遥测待部署阶段实现 | 模型资格、上线与预算决策 |

## 质量模型

Relapaw 不用“模型返回了答案”定义成功。一个运行只有同时满足以下条件才可成为 COMPLETED：

- Safety 门禁允许；
- Provider 请求完成；
- 输出通过 Pydantic 契约；
- Evidence key 全部来自当前输入快照；
- 整个聚合在短事务内原子保存；
- UI 继续显示模型来源与待确认状态。

语义质量仍由人工决定并由版本化 Evaluation 衡量。契约合法、用户拒绝或模型未获资格的结果，都是产品需要保留的真实反馈。

## 后续阶段如何沿用

- Phase 3 的长期记忆只能从明确的人类决定投影，且必须可撤回、可重算、可追溯。
- Evaluation 必须覆盖越界诊断、非法 Evidence、语言跟随、过度确定、延迟和成本。
- UI 精修必须保留 Safety、来源、不确定性和用户决定层级，不能为了视觉简洁隐藏它们。
- 部署后必须记录错误率、延迟、Provider 版本与预算，但不得记录 API key 或不必要的原文。
