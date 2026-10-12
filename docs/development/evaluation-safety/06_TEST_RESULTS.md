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
