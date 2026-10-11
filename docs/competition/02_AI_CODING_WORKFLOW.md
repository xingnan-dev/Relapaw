# AI Coding 完整工作流

## 固定生命周期

Relapaw 不把 AI Coding 限定为“让模型写代码”，而是将其纳入每个阶段的完整软件生命周期：

```text
人类给出目标与约束
→ Codex 审计代码、数据、迁移、测试和未提交修改
→ 人与 AI 明确范围、非目标、架构和验收条件
→ Codex 按垂直切片实现并补测试
→ 自动测试暴露问题
→ Codex 执行独立代码审查
→ Codex 修复并完整回归
→ 人工浏览器/真实 Provider 验收
→ Codex 更新过程、测试、风险和证据文档
→ 人类单独授权 commit
→ 核对本地提交
→ 人类单独授权 push
→ 核对远端
```

该流程的权威顺序见 `docs/PROJECT_EXECUTION_GUIDE.md`。任何变更均需记录原因、影响和风险，并由用户确认。

## 每一步的输入与可验证输出

| 环节 | 人类输入 | AI 工作 | 可验证输出 |
|---|---|---|---|
| 审计 | 项目目录、目标、禁止项 | 读取 status、历史、代码、迁移和测试 | 审计结果、保留项、风险清单 |
| 设计 | 产品边界与优先级 | 拆解 Requirement/ADR/Scope/Acceptance | Phase 文档 |
| 实现 | 已确认范围 | 修改代码、迁移、测试 | diff、垂直切片、契约测试 |
| Review | 审查范围 | 检查 Safety、事务、Evidence、隐私、并发 | `07_AI_CODE_REVIEW.md` |
| 修复回归 | Review 发现 | 修复并运行全套命令 | `08_FIX_AND_REGRESSION.md`、测试输出 |
| 人工验收 | 用户真实操作和决定 | 解释状态、记录真实结果 | `09_ACCEPTANCE.md`、截图（提交材料阶段整理） |
| Git 门禁 | 明确授权 | 精确 stage/commit 或 push | commit hash、远端核对 |

## Prompt 管理

- 每个 Phase 保留经过整理、可公开的关键 Prompt，不保存 API key、私人目录噪声或无关聊天。
- Prompt 同时写明“要做什么”和“不得做什么”，例如不得诊断、不得绕过 Safety、不得擅自 commit/push。
- 运行时 Prompt 有独立版本；Phase 2 当前为 `text-understanding/v3-provider-neutral`。
- Prompt 版本、输入契约和输出契约随 AnalysisRun 保存，便于回放与比较。

## 失败不是隐藏步骤

- 测试失败必须定位根因，再修复并回归；
- Provider 失败映射稳定错误码并保留失败运行，不保存部分 Claim；
- 不满足契约的模型响应不得包装为成功；
- 人工可以拒绝语义质量较差但契约合法的 Claim；
- 真实失败与修复进入 Case Study，而不是从比赛叙事中删除。

## 当前覆盖范围

- Phase 0/0.1：工程基线、迁移、错误结构、前端入口、Review 和回归。
- Phase 1：结构化记录闭环的审计、七个切片、事务修复与验收。
- Phase 2：模型契约、Safety/Evidence 边界、Provider 兼容调试、真实验收和 Prompt 迭代。
- 后续阶段必须继续采用同一流程，并同步更新本目录的证据映射。
