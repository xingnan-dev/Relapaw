# Evaluation Final Report

报告版本：`evaluation-summary/v1`  
冻结日期：2026-10-13

## 结论

Evaluation 流程已覆盖离线确定性规则、录制 Provider 结果、限额真实 Provider 请求和人工语义 Review。当前资格结论为：

> `qwen/qwen3.8-flash + text-understanding/v5-grounded-claims`：`NOT_QUALIFIED`

该结论表示当前组合不应被宣传为语义质量已认证，也不能获得自动写事实或长期记忆的权限。它不影响应用继续保存失败记录、展示待确认 Claim，以及允许用户确认或拒绝。

## 汇总

| 层级 | 样本/请求 | 结果 |
| --- | ---: | --- |
| 离线确定性数据集 | 9 | 9/9 冻结期待匹配 |
| recorded-output 数据集 | 14 | 14/14 匹配；2 个版本组隔离 |
| 真实 Provider v3 | 2 | 硬门禁通过；人工 Review 失败 |
| 真实 Provider v4 | 2 | 中文语言硬门禁失败；人工 Review 失败 |
| 真实 Provider v5 | 2 | 硬门禁通过；人工 Review 失败 |

三轮真实请求均经过单独授权，每轮最多 2 请求、每例最多 800 输出 token、30 秒超时、零重试、零产品数据库写入。

## 为什么不继续追求“全绿”

第三轮已经证明契约和 Evidence 门禁可以全部通过，但模型仍可能产生时间顺序偏移和未记录原因。继续无上限修改 Prompt 并付费重试会把评估变成针对两个样本的过拟合。因此当前正确工程结论是保留失败、停止试错、标记未获资格，并把更换模型或重构 Claim 契约作为独立后续工作。

## 可复现检查

从 `backend` 目录执行以下命令，均不会发送真实请求：

```powershell
.\.venv\Scripts\python.exe -m app.evaluation.text_understanding evals\text_understanding_v1.json
.\.venv\Scripts\python.exe -m app.evaluation.recorded_outputs evals\recorded_outputs_v1.json
.\.venv\Scripts\python.exe -m app.evaluation.live_provider evals\live_provider_v1.json
.\.venv\Scripts\python.exe -m app.evaluation.summary_report evals\evaluation_summary_v1.json
```

权威机器可读汇总为 `backend/evals/evaluation_summary_v1.json`。
