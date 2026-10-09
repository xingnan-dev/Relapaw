# Phase 2 Test Plan and Results

状态：Slice 2 前端文本 Understanding 闭环已完成自动验证；真实 Provider 暂不接入。

## 后端计划

### Adapter contract

- 输入严格区分 Raw Input、Observation、OwnerInterpretation、Safety 和 Evidence keys。
- DisabledAdapter 返回 `MODEL_NOT_CONFIGURED`，不生成假 Claim。
- 合法结构化输出通过；缺字段、未知枚举、诊断字段和未知 Evidence key 被拒绝。
- Provider timeout、rate limit、network failure 映射为稳定错误。

### Safety

- 缺少 SafetyCheck 拒绝分析且不调用 Adapter。
- `ESCALATE_TO_VET` 创建/返回 blocked run，不调用 Adapter、不生成 Claim。
- 正常分析不能修改 SafetyCheck 或 VeterinaryEscalation。

### 持久化与事务

- 成功保存 AnalysisRun、Claim、Evidence 快照、Uncertainty 和版本元数据。
- 任一子对象失败时不留下部分 completed run 或部分 Claim。
- FAILED run 不包含部分模型结果或敏感 provider 错误。
- 同一 request_id 幂等；并发确认只能产生一个最终决定。

### Evidence 与隔离

- 未知、跨 Episode、跨宠物 Evidence 被拒绝。
- Episode 编辑后旧 Evidence 快照仍可读并显示 stale。
- 有 AnalysisRun 的 Episode 删除返回 `EPISODE_HAS_ANALYSIS`。

### 用户确认

- CONFIRMED / REJECTED 成功；重复或冲突决定返回统一 409。
- 只有 CONFIRMED Claim 进入长期记忆投影。
- 确认前后 Observation、OwnerInterpretation、Baseline 和 Episode 原文完全不变。

## 前端计划

- 发起前输入预览保持三类来源分区。
- loading、Safety blocked、provider unavailable、invalid output、retry、completed 状态。
- Claim、Evidence、Uncertainty 和模型版本清晰展示。
- 模型生成/未确认提示持续可见。
- 确认与拒绝二次确认；失败后保留页面和选择。
- stale 历史与重新分析入口。
- Safety blocked 时不存在行为 Claim 卡片。
- 窄屏和桌面下底部导航不遮挡操作。

## 迁移与交付计划

```text
backend full pytest
frontend full vitest
frontend production build
fresh database upgrade to head
Phase 1 database upgrade to Phase 2 head
downgrade to previous revision and re-upgrade
alembic current
alembic check
git diff --check
secret / token / temp database / build artifact inspection
```

## 本轮结果

- 功能测试：未运行，本轮没有功能代码变化。
- `git diff --check`：通过，无输出。
- 变更范围：仅 `docs/development/INDEX.md` 与新增 `docs/development/phase-2/` 文档。
- 后端、前端、依赖与 `0001`–`0004` migration 均未修改。

## 2026-10-09 — Slice 1 实际结果

```text
backend: 49 passed, 1 StarletteDeprecationWarning in 2.56s
frontend: 1 file passed, 35 tests passed
production build: tsc -b + vite build passed, 26 modules transformed
existing database: upgraded 20261008_0004 -> 20261009_0005 (head)
alembic check: No new upgrade operations detected
fresh database: upgrade from base to head passed
migration cycle: downgrade 0005 -> 0004 and re-upgrade -> 0005 passed
git diff --check: passed, no output
```

新增后端测试覆盖：成功聚合保存与三类输入分离、幂等 request_id、缺少 Safety、Safety 阻断、非法输出契约、未知 Evidence、DisabledAdapter、单次人工确认、stale Evidence 快照、Episode 删除保护、事务回滚和统一 404。

唯一警告来自现有 FastAPI TestClient 对 Starlette/httpx 的弃用提示，不影响本轮断言。临时 migration 数据库已在验证后删除；前端 `dist` 保持忽略状态。

## 2026-10-09 — Slice 2 验证范围

新增前端测试覆盖：三类输入预览、loading、FakeAdapter completed 展示、Claim/Evidence/Uncertainty/置信度/模型与契约版本、逐条确认、MODEL_NOT_CONFIGURED 且无伪结果、invalid output、network error 与同 request_id 重试、确认失败状态保留、Safety blocked、历史与 stale。

后端 Safety 测试扩展为 `NEED_MORE_INFO` 和 `ESCALATE_TO_VET` 均在 Adapter 前阻断。最终测试数字与交付门禁记录在本节后续最终回归结果中。

### 最终回归结果

```text
backend: 50 passed, 1 StarletteDeprecationWarning
frontend: 2 files passed, 41 tests passed
production build: tsc -b + vite build passed, 27 modules transformed
alembic current: 20261009_0005 (head)
alembic check: No new upgrade operations detected
git diff --check: passed, no output
```

构建生成的 `frontend/dist`、pytest cache 和 Python bytecode 均为已忽略产物；没有新增密钥、模型 SDK、真实 Provider 配置、临时数据库或被跟踪的构建文件。唯一警告仍来自 FastAPI TestClient 的既有 Starlette/httpx 弃用提示。

### 人工验收结果

- NORMAL SafetyCheck Episode 的 Understanding 入口和三类输入预览：通过。
- 未配置真实模型时展示 `MODEL_NOT_CONFIGURED` 且不生成伪结果：通过。
- 首轮截图发现的悬浮主操作栏遮挡已修复；修复后按钮位于详情末尾，滚动与底部导航显示正常。
- 用户于 2026-10-09 明确确认 Slice 2 可运行路径验收通过。
- completed、逐条决定与 stale 状态继续由测试 FakeAdapter 自动验证；本轮没有为人工演示生成伪结果。
