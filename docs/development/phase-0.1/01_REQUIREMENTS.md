# Requirements Analysis

## 问题

Phase 0 已有领域骨架，但缺少正式迁移、稳定错误契约、分页、时区边界、current pet，以及可信的首次使用流程。页面能切换但还不足以表达 Relapaw 的核心原则。

## 用户价值

- 新用户先理解 Observation ≠ Interpretation 和安全边界，再建立宠物档案。
- 老用户恢复上次宠物，不读取硬编码 `pet_id=1`。
- 长期记录支持稳定分页，并明确区分事实与主人解释。
- 工程变更具备数据库迁移与可复现测试。

## 不在范围

LLM、RAG、Agent、多模态识别、自动医学/情绪判断、账号、支付、高保真 UI 与 Pet↔Pet 关系模型。
