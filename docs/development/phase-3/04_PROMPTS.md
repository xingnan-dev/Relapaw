# Phase 3 Coding Prompt

```text
继续开发 Relapaw Phase 3：长期记忆投影与量化 Baseline。

开始前完整读取 docs/PROJECT_EXECUTION_GUIDE.md、Phase 1/2/Design System 验收材料和本目录 01–03。

必须遵守：
- UserConfirmation 不等于长期事实；只有独立 INCLUDE 才进入投影。
- MemoryDecision 追加保存，WITHDRAW 不覆盖确认或历史。
- 量化 Baseline 只使用结构化数值，不从自然语言或模型 Claim 猜测。
- 保留人工 pet_baselines，不自动写入。
- 每个快照带窗口、样本量、算法版本、fingerprint、lineage 和 stale。
- 不接 RAG、Agent、多模态、诊断、治疗、用药或长期模型记忆。
- 不修改旧 migration；不 commit、不 push，除非用户明确授权。

先审计工作区并输出 Slice 1 的模型、migration、API、测试和风险，再开始编码。每个 Slice 完成定向测试；最终执行完整 Review、回归与人工验收。
```

