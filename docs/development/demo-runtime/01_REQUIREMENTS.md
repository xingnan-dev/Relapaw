# Batch 1 需求与范围

日期：2026-10-17

## 必须完成

- 运行时 AI 由显式 `RELAPAW_AI_ENABLED` 控制，默认关闭；配置 Key 不得自动开启；
- 提供不泄露 Secret 的 Capabilities API；
- 非 NORMAL 或缺失 Safety Check 的语义优先于通用功能关闭；
- NORMAL 且 AI 关闭时拒绝创建 AnalysisRun，也不写失败审计；
- 前端读取能力失败时 fail closed；
- AI 关闭时可只读查看历史 AnalysisRun，但不能创建运行或提交新的 Claim 决定/候选；
- 合成 demo 环境显示数据标识；
- 现有 AI 能力在测试显式开启时保持可回归。

## 非目标

- 本批实现版本化 seed 与 verify，但不实现 reset、static serving 或 launcher；
- 不增加账号、部署或数据库 migration；
- 不改变 Evaluation 资格结论；
- 不发起真实 Provider 请求。
