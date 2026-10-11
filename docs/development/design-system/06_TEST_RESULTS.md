# Test Results

日期：2026-10-11

## 定向验证

```text
Design System + Understanding: 13 passed
production build: passed, 28 modules transformed
```

初次定向测试发现 Safety 标题和正文重复 “Safety blocked”，导致唯一文本查询失败；去除正文重复前缀后通过。

## 完整回归

```text
backend pytest: 76 passed
frontend Vitest: 3 files passed, 49 tests passed
production build: passed, 28 modules transformed
pip check: No broken requirements found
alembic current: 20261009_0005 (head)
alembic check: No new upgrade operations detected
git diff --check: passed
```

`backend/.env`、虚拟环境、pytest cache、`frontend/node_modules` 和 `frontend/dist` 继续处于 Git ignored 状态。没有真实 Provider 请求。
