# Commit 与证据映射

## 已有里程碑

| Commit | 完成内容 | 代码证据 | 流程证据 | 验证状态 |
|---|---|---|---|---|
| `92f57d6` | Phase 0/0.1 工程基线 | React/FastAPI/Alembic、基础 API/UI/测试 | `docs/development/phase-0.1/` | 已完成并推送 |
| `05e02e4` | Phase 1 结构化记录闭环 | Episode 聚合、Safety、Follow-up、Plan、Evidence、Timeline | `docs/development/phase-1/` | 已完成并推送 |
| `da08fbc` | Phase 2 文本 Understanding 前后端闭环 | migration 0005、AnalysisRun/Claim、FakeAdapter、UI 状态和确认/拒绝 | Phase 2 `01`–`06` | 已完成并推送 |
| `f0229ee` | 真实 Provider 接入 | OpenAI/Qwen Adapter、错误映射、mock 测试、v3 Prompt | Phase 2 Provider 记录 | 已完成并推送 |
| `965d8dd` | Phase 2 Review 与关闭 | Review 回归补强、Acceptance、路线修正 | Phase 2 `07`–`09` | 已完成并推送 |
| `05e46a1` | Phase 3 长期记忆候选生命周期 | MemoryCandidate、追加式决定、stale 与回滚 | Phase 3 Slice 1 记录与测试 | 已完成并推送 |
| `1841365` | Phase 3 确定性量化 Baseline | 7/30/90/all、样本门槛、趋势与快照 | Phase 3 Slice 2 记录与测试 | 已完成并推送 |
| `7ea8fc8` | Phase 3 Baseline Evidence lineage | 字段级来源、编辑删除生命周期、原子回滚 | Phase 3 Slice 3 记录与测试 | 已完成并推送 |

## 需求到证据的查找方式

| 要证明的内容 | 首选证据 |
|---|---|
| AI Coding 用于完整开发流程 | 各 Phase 的 `04`–`09` 文档与对应 commit diff |
| Observation 与 Interpretation 分离 | Phase 1 Requirements、ORM/schema、Episode 页面 |
| Safety 在模型调用前阻断 | Phase 2 架构、`test_text_understanding.py`、浏览器安全路径 |
| 模型输出不是事实 | Understanding UI 标签、UserConfirmation、真实 REJECTED 验收 |
| Provider 失败不保存部分 Claim | 错误映射测试、FAILED AnalysisRun 历史 |
| 真实模型可工作 | Qwen Chat smoke test与浏览器 AnalysisRun #3 |
| AI 建议经过 Review 与修复 | Phase 0.1/2 AI Review 和 Fix/Regression 文档 |
| 密钥未进入仓库 | `.gitignore`、`.env.example`、Phase 2 污染检查 |
| 长期记忆由用户控制 | MemoryCandidate/MemoryDecision API、Slice 1 测试、Slice 4 前端决定入口 |
| Baseline 不伪造趋势 | `quantitative-baseline/v1`、样本不足测试、字段级来源下钻 |

## 后续 commit 规则

每个较大阶段最多使用四类可审计提交：Planning、Implementation、Fix/Regression、Acceptance/Closeout。每次提交前记录测试结果、diff 范围、污染检查和人工授权。每次 push 必须再次获得明确授权并核对远端 commit。

## 截图与演示证据状态

Phase 2 已有人工验收截图和真实浏览器操作，但当前只映射仓库内可追溯证据。正式比赛材料阶段再建立经过脱敏、统一命名的截图/视频资产目录，并把每个资产映射到版本和演示步骤；不得使用包含 API key、私人路径或无关窗口的原始截图直接提交。
