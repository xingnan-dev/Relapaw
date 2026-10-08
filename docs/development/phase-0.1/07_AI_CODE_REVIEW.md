# AI Code Review

Review 日期：2026-10-07  
Reviewer：OpenAI Codex  
范围：安全边界、状态恢复、API/迁移、时间、分页、可访问性、测试和禁止能力。

## Findings

### [P2] 临时接口故障会清除有效 current pet

- 位置：`frontend/src/state/CurrentPetContext.tsx`、`frontend/src/api.ts`
- 现象：任何 `getPet` 失败都被当作 404，localStorage 中的宠物 ID 被删除。
- 影响：短暂 5xx、代理错误或离线状态会丢失用户选择，恢复后可能错误切换宠物。
- 决定：修复。API 客户端暴露 status；只有明确 404 才清理，其他错误保留选择并显示重试状态。

### [P2] Timeline 异步结果可能覆盖新宠物页面，加载更多失败未处理

- 位置：`frontend/src/pages/Timeline.tsx`
- 现象：切换/卸载后旧请求仍可更新状态；加载更多没有 error/finally，可能出现未处理 rejection 与重复点击。
- 影响：未来多宠切换可能短暂显示错误宠物记录；失败路径不稳定。
- 决定：修复。增加 effect 失效标记、loading 状态、错误提示和重复请求保护。

### [P3] Pet Setup 中断没有草稿恢复边界

- 位置：`frontend/src/components/PetSetup.tsx`
- 现象：用户选择“稍后添加”再返回时表单内容丢失。
- 影响：不满足 Phase 0.1 的合理恢复要求。
- 决定：修复。只在本地保存最小表单草稿，创建成功清除；不保存照片或敏感推断。

## 已核对且未发现阻断问题

- Observation 与 OwnerInterpretation 仍是独立表、schema、端点和 UI 区域。
- 枚举非法状态被 Pydantic 拒绝。
- Timeline 稳定倒序与分页元数据有后端测试。
- Alembic migration 与 ORM 自动对比无新增操作。
- 未发现外部模型 SDK、RAG、Agent Loop、自动医学判断或图像识别接入。
- VeterinaryEscalation 仅能人工创建/更新。

## 非阻断遗留项

- API 客户端尚无统一超时、AbortController、请求 ID 和重试策略；Phase 1 前可按实际接口体验决定。
- 500 边界不泄露内部错误，但尚无结构化服务端日志和 correlation ID。
- 多宠物显式选择、账户所有权和跨设备状态属于后续 Phase。
- TestClient/Starlette 存在一条上游弃用 warning，按要求未修改业务依赖消除。

结论：三个发现均已修复，无剩余 P1/P2 阻断项；等待人工验收。
