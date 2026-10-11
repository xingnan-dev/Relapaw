# AI 工具与具体用途

状态：持续维护

建立日期：2026-10-11

## 工具清单

| 工具 | 类型 | 在 Relapaw 中的用途 | 不承担的职责 | 证据 |
|---|---|---|---|---|
| OpenAI Codex（桌面工作区代理） | AI Coding 工具 | 需求拆解、仓库审计、架构方案、代码与测试实现、命令执行、代码审查、缺陷修复、回归和文档维护 | 不替代产品负责人作最终范围决定；未经授权不 commit/push；不替代人工验收 | 各 Phase 的 `04_PROMPTS.md`、`05_IMPLEMENTATION_LOG.md`、`07_AI_CODE_REVIEW.md`、`08_FIX_AND_REGRESSION.md`、`09_ACCEPTANCE.md` |
| Qwen（阿里云百炼） | 产品运行时文本模型 Provider | 在 SafetyCheck=`NORMAL` 后，根据当前 Episode 的三类输入生成严格结构化、待确认的可能解释 | 不诊断、不治疗、不联网检索、不改写人工记录、不自动写入 Baseline | `docs/development/phase-2/`、提交 `f0229ee` |
| OpenAI Python SDK | Provider 接入 SDK | OpenAI Responses Structured Outputs；以及 Qwen OpenAI-compatible Chat Completions JSON Schema 调用 | 不绕过应用侧 Pydantic/Evidence 校验；不在前端持有密钥 | `backend/app/services/understanding_adapter.py`、Provider mock 测试 |
| FakeAdapter / mock client | 自动测试替身 | 离线验证成功、错误、非法 Evidence、事务回滚和 Safety short-circuit | 不在产品界面生成伪结果，不访问付费 API | `backend/tests/test_text_understanding.py`、`backend/tests/test_openai_understanding_adapter.py` |

## 开发工具与产品模型的区别

```text
Codex
  └─ 协助人类开发、测试、审查和记录 Relapaw

Relapaw 产品
  └─ 服务端 TextUnderstandingAdapter
       ├─ 未配置：DisabledAdapter → MODEL_NOT_CONFIGURED
       ├─ OpenAI：Responses API
       └─ Qwen：OpenAI-compatible Chat Completions JSON Schema
```

Codex 的对话和开发决策属于软件工程过程；Qwen/OpenAI Adapter 的输出属于运行时业务数据。两者不得混称为“产品使用了 Codex 生成分析”，也不得把开发工具的能力宣传为最终产品功能。

## 人与 AI 的权责边界

- 人类确定产品目标、比赛方向、Safety 边界、是否进行真实付费请求，以及 commit/push 授权。
- Codex 可以在已授权范围内自主审计、实现、测试和修复，但必须保存可复核证据并报告风险。
- 模型输出始终标记为“模型生成、尚未确认”；用户只能逐条确认或拒绝。
- 人工决定不会改写 Episode、Observation、OwnerInterpretation、SafetyCheck、VeterinaryEscalation 或 Baseline。
- Provider key 只存在服务端环境变量；不得进入 Git、前端、日志、API 响应或数据库。

## 提交时可使用的简明声明

> 本作品使用 OpenAI Codex 参与需求分析、架构设计、代码与测试实现、代码审查、缺陷修复、回归验证和开发文档维护。产品运行时的文本 Understanding 通过服务端 Adapter 接入 Qwen/OpenAI-compatible API；模型只生成带 Evidence 与 Uncertainty 的待确认可能解释，不进行诊断或自动事实写入。人与 AI 的完整协作流程、失败案例和 Git 证据见 `docs/competition/` 与 `docs/development/`。
