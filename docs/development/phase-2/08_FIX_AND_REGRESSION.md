# Phase 2 Fix and Regression

日期：2026-10-11
关联主提交：`f0229ee`

## 修复闭环

| 问题 | 修复 | 验证 |
|---|---|---|
| Provider 错误可能暴露不稳定细节 | 映射认证、权限、timeout、限流、网络、拒绝、截断和非法输出稳定码 | Adapter mock 与 API 失败审计测试 |
| Provider 等待占用数据库事务 | 快照后结束读事务，返回后使用短事务保存聚合 | Provider 等待期间编辑 Episode 回归 |
| stale Evidence 可能错连新行 | 来源变化时 Evidence FK 置空，保留不可变来源快照 | 并发编辑与 stale 回归 |
| 百炼 Responses 不执行 JSON Schema | Qwen 使用 Chat Completions `parse` 并关闭 thinking | mock 契约测试与一次真实 smoke test |
| Pydantic parse 异常未归一化 | 映射为 `MODEL_OUTPUT_INVALID` | 非 JSON 输出回归 |
| 真实 `.env` 影响 DisabledAdapter 测试 | 测试显式注入 DisabledAdapter | 配置真实 Qwen 后完整测试仍不联网 |
| 前端 Provider 错误语义不足 | 增加认证、timeout、限流、不可用文案并保留 retry | Vitest 状态测试 |
| Claim 偏题且语言不跟随输入 | v3 Prompt 聚焦 Episode 行为、跟随输入语言、限制缺失上下文用途 | Prompt 断言测试；后续持续人工抽样 |

## 最终回归

```text
backend pytest: 76 passed
frontend Vitest: 2 files passed, 45 tests passed
production build: passed, 27 modules transformed
pip check: No broken requirements found
alembic current: 20261009_0005 (head)
alembic check: No new upgrade operations detected
git diff --check: passed
```

自动测试没有访问真实付费 API。真实请求仅在用户逐次明确授权后执行，且 SDK `max_retries=0`。

## 污染检查

- `backend/.env`、虚拟环境、数据库、Python cache、frontend `dist`/`node_modules` 均被 Git 忽略。
- `.env.example` 只有空占位符；受版本控制文件未发现真实 API Key。
- 没有修改旧 migration，也没有因 Provider 接入新增数据库 migration。
