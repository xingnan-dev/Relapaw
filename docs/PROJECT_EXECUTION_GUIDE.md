# Relapaw 项目完整执行指引

版本：1.1

冻结日期：2026-10-11
适用范围：比赛版本及赛后产品路线

## 1. 指引地位与变更控制

本文档是 Relapaw 后续开发的唯一主顺序。任何任务开始前先核对本文档，不得在进入下一步时临时改变阶段顺序。

只有以下情况允许调整：

1. 比赛官方规则或截止要求发生变化；
2. 当前阶段发现阻断后续开发的安全、数据或架构问题；
3. 用户明确要求改变产品方向。

调整流程固定为：

```text
提出变更原因
→ 标明受影响阶段、收益与风险
→ 更新本文档版本
→ 用户明确确认
→ 才能执行新顺序
```

未经上述流程，不得跳过阶段、提前接入后续能力，或把规划内容描述为已完成。

## 2. 全项目固定顺序

```text
Phase 0/0.1 工程基础（已完成）
→ Phase 1 结构化记录闭环（已完成）
→ Phase 2 文本 Understanding（已完成）
→ 比赛 AI Coding 证据框架（已验收）
→ 轻量 Design System（已验收）
→ Phase 3 长期记忆投影与量化 Baseline
→ Evaluation 与 Safety 评估体系
→ 完整 UI/UX 与品牌精修
→ 生产部署与可观测性
→ 比赛演示数据与材料
→ Release Candidate 总验收
→ 比赛提交与版本冻结
→ 赛后 Phase 4–6
```

## 3. 已完成基线

### Phase 0 / 0.1：工程基础

- React + TypeScript、FastAPI、SQLAlchemy、Alembic；
- 迁移、错误结构、时间与分页边界；
- 基础导航、页面结构和自动测试框架。

### Phase 1：结构化记录闭环

- Episode、Observation、Owner Interpretation；
- 人工 SafetyCheck、VeterinaryEscalation；
- Timeline、Observation Plan、Follow-up、EvidenceReference；
- 编辑、删除、复评与来源追溯。

### Phase 2：文本 Understanding

- OpenAI Responses 与 Qwen Chat Structured Outputs Adapter；
- AnalysisRun、Claim、Evidence、Uncertainty；
- Safety 前置门禁、稳定错误、失败审计、history 与 stale；
- 用户逐条确认/拒绝，不修改人工记录或 Baseline；
- 自动测试、真实 Provider、浏览器人工验收和标准开发记录。

Phase 2 关闭基线：`965d8dd`。

## 4. 比赛 AI Coding 证据框架（已验收）

目标：在继续开发前，先让后续每项工作自然产生比赛要求的证据，而不是比赛前倒推补写。

必须建立：

```text
docs/competition/
  01_AI_TOOLS_AND_PURPOSES.md
  02_AI_CODING_WORKFLOW.md
  03_HUMAN_AI_INTERACTION_CASES.md
  04_AI_NATIVE_METHODOLOGY.md
  05_THIRD_PARTY_ATTRIBUTIONS.md
  06_COMMIT_AND_EVIDENCE_MAP.md
  07_COMPETITION_REQUIREMENTS_MATRIX.md
```

必须覆盖：

- AI Coding 工具名称和用途；
- 产品运行时模型与开发工具的区别；
- 人与 AI 的职责、授权和决策边界；
- 从需求、实现、失败、修复到验收的完整交互案例；
- AI 原生生命周期方法论；
- 官方文档、开源依赖和引用代码来源；
- 比赛每项要求对应的代码、测试、截图、文档和 commit。

出口条件：材料结构建成、Phase 0–2 已有证据完成映射、第三方来源规则明确。

### 4.1 比赛要求的持续门禁

比赛证据框架完成不代表后续可以停止留痕。自本版本起，以下四项要求贯穿 UI/UX、部署、演示材料和 Release Candidate，不允许在比赛前临时补写：

1. **使用 AI Coding 工具开发**：每个实施批次记录所用工具、人工目标、AI 参与环节和最终人工决定；
2. **提交时说明工具名称与具体用途**：持续更新工具清单，并明确区分开发工具与产品运行时模型；
3. **独立展示完整 AI Coding 过程与 AI 原生方法论**：每个阶段至少保留一条“目标 → 交互 → 实现 → 失败或 Review → 修复 → 测试 → 人工验收 → Git”的真实链路，最终作为独立章节和演示资产，不得只嵌入产品说明书；
4. **引用来源透明**：新增依赖、代码片段、字体、图标、插画、图片、数据集和官方资料时立即登记来源与许可证；无法确认授权的素材不得进入 Release Candidate。

每个阶段关闭前必须同步更新 `docs/competition/` 中的工具用途、交互案例、第三方来源、Commit/Evidence Map 和比赛要求矩阵。

出口条件：该阶段的代码、测试、截图、人工决策、AI 交互记录和 Git 证据能够互相对应，且第三方来源没有待确认项。

## 5. 轻量 Design System（已验收）

目标：在 Phase 3 增加复杂页面前，冻结基础视觉语言；此阶段不重写业务逻辑。

必须完成：

- 颜色、字号、间距、圆角、边框、阴影 token；
- 按钮、输入框、卡片、状态提示等基础组件；
- 页面最大宽度、移动端和桌面响应式规则；
- loading、empty、error、blocked、stale 视觉语义；
- Claim、Evidence、Uncertainty 和 Safety 层级；
- 键盘焦点、触控面积和颜色对比度基础要求。

出口条件：基础组件和核心状态有规范及测试，现有业务页面功能不回退。

## 6. Phase 3：长期记忆投影与量化 Baseline

固定目标：建立可撤回、可重算、可追溯的派生信息，不允许模型直接写长期事实。

执行顺序：

1. 审计现有 Baseline、确认审计和 Evidence 边界；
2. 编写 Requirements、Architecture、Scope、Prompt/算法说明和验收条件；
3. 设计 migration 与数据生命周期；
4. 实现长期记忆候选、纳入、撤回、stale 与重算；
5. 实现 7/30/90 天及全部历史时间窗口；
6. 实现样本量、范围、频率、持续时间和数据不足状态；
7. 实现 Evidence lineage 与算法版本；
8. 实现前端 Baseline、趋势、样本状态和来源下钻；
9. 完成自动测试、Review、修复、回归和人工验收；
10. 经授权 commit 和 push。

禁止：模型直接改 Baseline、伪精确健康/情绪评分、在样本不足时生成趋势。

## 7. Evaluation 与 Safety 评估体系

固定在 Phase 3 功能完成之后、完整视觉精修之前。

必须覆盖：

- 正常、信息不足、Observation/Interpretation 冲突；
- 非法 Evidence、越界诊断、治疗/用药建议；
- 非 NORMAL Safety 阻断；
- Provider timeout、限流、网络、非法 JSON；
- 中英文语言跟随、无依据断言和过度确定；
- Schema/Evidence 合法率、违规率、延迟和成本。

出口条件：版本化 Evaluation 数据集、可重复运行、结果进入比赛证据。

## 8. 完整 UI/UX 与品牌精修

固定在 Phase 3 信息架构和 Evaluation 稳定后进行。

必须完成：

- 先完成页面职责、入口和跳转清点，删除虚假可点击元素与重复入口；
- 品牌色、字体、Logo/图形语言和统一中文产品语言；
- Today、Understand、Timeline、Episode、Baseline、Us 页面精修；
- 桌面宽屏、移动端、长页面和底部导航优化；
- 表单、骨架屏、空状态、错误、Safety 与用户决定反馈；
- Chrome/Edge、常见屏幕尺寸、键盘和无障碍验收；
- 视觉截图回归；
- 为本阶段保存至少一条完整 AI Coding 交互案例，登记新增字体、图标、插画和图片来源。

出口条件：核心演示路径视觉一致、无明显遮挡或大面积无效留白、功能测试不回退。

## 9. 生产部署与可观测性

必须完成：

- PostgreSQL 与迁移验证；
- 前后端正式部署、HTTPS、CORS 白名单；
- 服务端 Secret 管理和 API Key 轮换；
- 数据库备份与恢复演练；
- 健康检查、结构化日志、错误监控；
- Provider timeout、限流、预算和成本告警；
- 开发、测试、演示和生产环境隔离；
- 可重复的演示环境初始化。

出口条件：演示不依赖开发者电脑上的临时终端，密钥不进入前端、Git、日志或数据库。

## 10. 比赛演示数据与材料

演示主路径固定为：

```text
记录 Episode
→ 区分 Observation 与 Owner Interpretation
→ 人工 SafetyCheck
→ NORMAL 才允许文本分析
→ 展示 Claim / Evidence / Uncertainty
→ 用户拒绝不合理 Claim、确认合理 Claim
→ 多次记录形成可重算 Baseline
→ 展示趋势、样本量与来源
```

安全路径固定为：

```text
SafetyCheck = ESCALATE_TO_VET
→ Provider 不调用
→ 不生成行为解释
→ 持续显示联系兽医提示
```

必须准备：项目简介、问题与用户、创新点、架构、安全、AI 方法论、Evaluation、隐私、测试、Git 证据、截图、Demo 视频、演示脚本、已知限制和路线图。

AI Coding 必须作为独立重点内容展示：工具名称与具体用途、开发工具与运行时模型的区别、完整人机交互案例、覆盖需求至交付的生命周期图、人工否决与安全决定、对应 commit/测试/截图，以及第三方代码和素材来源清单。

禁止把 Phase 4–6 的规划描述为已实现。

## 11. Release Candidate 与比赛提交

进入 Release Candidate 后冻结新功能，只允许修复阻断问题。

固定门禁：

```text
需求冻结
→ 最终 AI Code Review
→ 修复与完整回归
→ fresh migration + PostgreSQL 验证
→ Provider 最小 smoke test
→ Safety 人工验收
→ 响应式与无障碍验收
→ 密钥和许可证检查
→ 部署演练
→ Demo 彩排
→ 比赛材料一致性检查
→ 创建 release commit/tag
```

推荐比赛版本标签：`v0.3.0-competition`。

## 12. 赛后路线

比赛版本冻结后才继续：

- Phase 4：安全 RAG；
- Phase 5：多模态；
- Phase 6：Relationship Copilot 与 Pet↔Pet。

除非比赛规则明确要求，否则比赛前不提前接入这些能力。

## 13. 每个开发任务的固定生命周期

所有后续任务无论大小均遵守：

```text
审计现状
→ 明确范围与非目标
→ 需求 / 架构 / 验收条件
→ 实现
→ 定向测试
→ AI Code Review
→ 修复
→ 完整回归
→ 人工验收
→ 更新开发记录和比赛证据
→ 更新 AI 工具用途、完整交互案例和第三方来源登记
→ 密钥、依赖、迁移、产物检查
→ 用户授权 commit
→ 核对本地提交
→ 用户授权 push
→ 核对远端
```

不得省略 Review、回归、人工验收或授权步骤。

## 14. Commit 与 Push 固定规则

每个较大 Phase 最多使用四类清晰提交：

1. Planning：Requirements、Architecture、Scope、Acceptance；
2. Implementation：migration、后端、前端、单元测试；
3. Fix and Regression：Review 修复和完整回归；
4. Acceptance/Closeout：人工验收、证据映射和路线图更新。

允许 push 的条件：

- 当前任务是完整、可验证、可独立回滚的单元；
- 自动测试、build、migration 和人工验收通过；
- Review 问题已关闭；
- 工作区和提交范围已核对；
- 无密钥、数据库、缓存、临时脚本或构建产物；
- 本地没有意外落后或分叉；
- 用户明确授权 push。

禁止在功能半成品、测试失败、仍在调试或缺少授权时 push。

## 15. 当前唯一下一步

当前 Phase 0–3、比赛 AI Coding 证据框架、轻量 Design System 与 Evaluation & Safety 均已完成、人工验收并推送。Evaluation 的最终资格结论为：

```text
qwen/qwen3.8-flash + text-understanding/v5-grounded-claims = NOT_QUALIFIED
```

该结论必须保留，不得因进入视觉阶段而弱化或隐藏 Safety、Evidence、Uncertainty、模型来源和人工决定。按本指引，当前唯一下一阶段是：

```text
完整 UI/UX 与品牌精修
```

当前 UI/UX 已进入产品结构收口：先完成页面职责、入口、真实数据能力和跳转目标清点，再删除重复入口与虚假交互，然后完成核心路径、深层状态、响应式、无障碍和视觉回归。每个实施批次同步保存 AI Coding 过程与第三方素材来源。当前不得跳到生产部署、比赛材料、Release Candidate 或赛后 Phase 4–6，也不得在视觉精修中改变既有业务状态机、数据语义或模型资格结论。
