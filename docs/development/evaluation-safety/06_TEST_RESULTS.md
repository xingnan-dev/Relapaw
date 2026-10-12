# Test Results

## 2026-10-12 — Slice 1

| 检查 | 结果 |
| --- | --- |
| 离线评估 CLI | 9/9 冻结期待匹配，`passed: true` |
| Evaluation 专项测试 | 3 passed |
| 后端全量测试 | 100 passed |
| 前端全量测试 | 56 passed |
| 前端生产构建 | passed |
| Alembic | `20261012_0008 (head)` |
| Python 依赖一致性 | `No broken requirements found` |
| `git diff --check` | passed |

复现命令（从 `backend` 目录执行）：

```powershell
.\.venv\Scripts\python.exe -m app.evaluation.text_understanding evals\text_understanding_v1.json
```

本轮没有调用真实 Provider，没有产生模型费用，也没有写入产品数据库。

## 2026-10-12 — Slice 2

| 检查 | 结果 |
| --- | --- |
| recorded-output CLI | 14/14 冻结期待匹配，2 个版本分组均为 100% |
| Evaluation + Adapter 专项测试 | 31 passed |
| 后端全量测试 | 104 passed |
| 前端全量测试 | 56 passed |
| 前端生产构建 | passed |

本轮 `network_calls: 0`，没有真实 Provider 请求、模型费用、密钥读取或产品数据库写入。

## 2026-10-12 — Slice 3 调用前预检

| 检查 | 结果 |
| --- | --- |
| live runner 专项测试 | 4 passed |
| 默认 CLI 模式 | `dry-run` |
| 计划请求 | 2 |
| 实际请求 | 0 |
| 数据库写入 | 0 |
| 重试 | 0 |
| 显式授权门禁 | ready，尚未授权执行 |

本记录只证明执行框架和预算门禁，不代表真实模型质量评估已经完成。

## 2026-10-12 — Slice 3 首轮真实 Provider 结果

| 检查 | 结果 |
| --- | --- |
| Provider / 模型 | Qwen / `qwen3.8-flash` |
| Prompt | `text-understanding/v3-provider-neutral` |
| 请求 | 2/2 |
| 重试 | 0 |
| 数据库写入 | 0 |
| 硬门禁 | 2/2 passed |
| 延迟 | 7252.751 ms / 7698.499 ms |
| 人工语义 Review | failed |
| 报告可读性 | 中文 stdout 编码 failed |

修复后的 `v4-evidence-boundary` 尚未进行真实 Provider 验证；当前不能宣称 Slice 3 通过。

## 2026-10-12 — Slice 3 第二轮真实 Provider 结果

| 检查 | 结果 |
| --- | --- |
| Prompt | `text-understanding/v4-evidence-boundary` |
| 请求 / 重试 / 数据库写入 | 2 / 0 / 0 |
| 中文样本硬门禁 | failed：`LANGUAGE_MISMATCH` |
| 英文样本硬门禁 | passed |
| Interpretation Evidence 角色 | fixed：`CONTEXT` |
| UTF-8 报告 | passed |
| 人工语义 Review | failed |
| 延迟 | 6126.455 ms / 2958.447 ms |

修复后的 `v5-grounded-claims` 尚未进行真实 Provider 验证；当前仍不能宣称 Slice 3 通过。

## 2026-10-12 — Slice 3 第三轮真实 Provider 结果

| 检查 | 结果 |
| --- | --- |
| Provider / 模型 | Qwen / `qwen3.8-flash` |
| Prompt | `text-understanding/v5-grounded-claims` |
| 请求 / 重试 / 数据库写入 | 2 / 0 / 0 |
| 硬门禁 | 2/2 passed |
| 中文语言跟随 | passed |
| Interpretation Evidence 角色 | passed |
| 延迟 | 3298.007 ms / 3455.981 ms |
| 人工语义 Review | failed |
| 资格结论 | `NOT_QUALIFIED` |

该结果表示评估流程成功完成，但当前 Provider/模型/Prompt 组合没有获得产品质量资格。硬门禁通过不等于语义质量通过。
