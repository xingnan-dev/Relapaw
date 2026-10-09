# Phase 1 Implementation Log

## 2026-10-08 — 编码前审计

执行者：Codex
工作类型：只读代码审计与实施设计
代码修改：无

### 已有可复用基础

- `Episode` 已作为宠物事件根对象，具备 `pet_id`、`happened_at`、`episode_type`、`raw_owner_input`、开放 `context` 和 `created_at`。
- `Observation` 与 `OwnerInterpretation` 已使用独立表、Pydantic schema、创建端点和 Timeline 展示区域。
- Timeline 已实现按宠物读取、稳定倒序、分页与加载更多。
- ObservationPlan 与 VeterinaryEscalation 已有最小人工 CRUD 骨架。
- API 已具备统一错误结构、时区输入校验和 SQLite 外键开启逻辑。
- 前端已有 Current Pet、Today 快速记录入口、Understand 双镜头低保真结构和 Timeline 展开视图。

### 主要差距

#### 后端

1. 创建 Episode、Observation、OwnerInterpretation 需要三次独立请求和三次 commit，任一步失败都会留下半条记录。
2. Episode 没有详情、编辑或删除端点；Observation 和 Interpretation 也没有修改路径。
3. Timeline 只支持页码，没有日期、类型或计划筛选。
4. 结构化上下文仍全部依赖开放 JSON，无法稳定验证和用于后续计算。
5. 没有 SafetyCheck、Follow-up、ObservationPlanItem、EpisodePlanLink 或 EvidenceReference 模型。
6. Observation、OwnerInterpretation 和多数纵向资源缺少审计时间。
7. ObservationPlan 仍以 `items_to_observe` JSON 保存项目，无法独立排序、约束和关联。
8. 测试通过 `Base.metadata.create_all()` 建表，不能证明 Alembic 从 Phase 0.1 升级和降级可用。
9. 通用异常处理未显式 rollback；Phase 1 事务服务应自行保证失败回滚并补测试。

#### 前端

1. Understand 的字段没有 state、验证或 API 调用，“保存手工记录”没有行为。
2. Context、Historical Context、Possible Explanations、Next Step 仍是 Phase 0.1 占位，应由 Phase 1 真实结构替换，不能伪装成 AI 分析。
3. 没有人工 Safety Check、持续安全提示或 Veterinary Escalation 操作。
4. Timeline 的搜索、筛选和时间 chip 均未连接查询；没有详情页、编辑和删除。
5. Today 没有读取今日记录、待复评或进行中计划。
6. App 只有本地 Tab 状态；增加详情/编辑层级时需要轻量导航方案，同时保持四个一级 Tab。
7. 前端 API 和类型只覆盖 Pet 与 Timeline 读取，不覆盖 Phase 1 写入流程。

### API 契约建议

第一切片使用以下稳定入口，细节在实现测试中锁定：

```text
POST   /api/v1/episodes/complete
GET    /api/v1/episodes/{episode_id}
PUT    /api/v1/episodes/{episode_id}
DELETE /api/v1/episodes/{episode_id}

GET    /api/v1/pets/{pet_id}/timeline
       ?page=&page_size=&from=&to=&episode_type=&plan_id=

POST   /api/v1/episodes/{episode_id}/follow-ups
POST   /api/v1/follow-ups/{follow_up_id}/complete
GET    /api/v1/pets/{pet_id}/follow-ups?status=due

POST   /api/v1/pets/{pet_id}/observation-plans
GET    /api/v1/observation-plans/{plan_id}
PUT    /api/v1/observation-plans/{plan_id}
```

组合创建请求应包含 Episode 主字段、Observation 列表、OwnerInterpretation 列表、人工 Safety Check，以及可选的计划 ID；响应返回完整聚合。

### 实施切片

#### Slice 1 — 数据与原子记录创建

- 新增 Phase 1 Alembic revision、受控枚举、ORM 关系和 Pydantic 契约。
- 新增事务型 `create_complete_episode` 服务和组合端点。
- 先覆盖原子成功、任一子对象失败回滚、时区与父对象校验测试。
- 暂时保留原有细粒度创建端点以兼容 Phase 0.1 测试。

#### Slice 2 — Timeline 管理

- 增加详情、筛选、更新和删除契约。
- 前端接入真实列表、筛选、详情、编辑和二次删除确认。
- 验证稳定分页和筛选组合。

#### Slice 3 — 人工安全边界

- 保存版本化 SafetyCheck；危险信号由用户显式选择。
- 在同一事务中按选择创建人工 VeterinaryEscalation。
- 前端提供持久提示，不使用自动规则或诊断文案。

#### Slice 4 — Follow-up

- 支持预约、到期列表和完成复评。
- 完成时原子创建新 Episode 与关联，原记录保持不变。
- Today 展示待处理复评，Timeline 支持双向导航。

#### Slice 5 — Observation Plan

- 规范化计划项目并建立 Episode 关联。
- Today 展示当前计划，计划详情显示关联记录。
- 不实现通知和后台调度。

#### Slice 6 — 最小 EvidenceReference

- 为人工来源建立对象级引用与字段路径。
- 验证删除、编辑和引用完整性；不引入 Claim 或模型字段。

#### Slice 7 — 完整回归与交付材料

- 使用迁移建立测试数据库，验证 upgrade/downgrade。
- 运行后端、前端、build 和可访问性主路径测试。
- 独立执行 AI Code Review、修复、回归和人工验收。

### 风险与控制

- **迁移兼容风险**：保留旧 JSON 字段读取，新增字段采用可迁移默认或可空，再由应用约束新写入。
- **级联删除风险**：Follow-up 与 Evidence 引用必须使用明确外键策略；实现前用迁移测试锁定。
- **接口过度扩张风险**：主流程优先组合端点，子资源端点只在编辑需要时增加。
- **前端状态复杂度**：先采用可测试的页面状态机；只有详情层级确实需要 URL 时才引入路由依赖。
- **安全误导风险**：危险信号列表只作为用户勾选项，不声称系统检测到风险。
- **Baseline 污染风险**：Phase 1 只保存原始可计算记录，不产出趋势或“正常范围”。

### 审计结论

现有 Phase 0.1 基线适合增量演进，无需重写。Phase 1 应从 Slice 1 开始，先建立迁移、事务型完整记录创建和测试；在该边界稳定前不应并行铺开全部前端页面。

### 审计后基线验证

- 后端：`12 passed, 1 warning in 0.41s`
- 前端：`1 passed / 15 tests passed, duration 1.98s`
- 前端 build：`26 modules transformed, built in 154ms`

唯一警告来自当前 Starlette TestClient 对 httpx 的弃用提示，不是 Phase 1 引入的问题；依赖升级应单独评估，避免与业务切片混在一起。

## 2026-10-08 — Slice 1：原子完整记录创建

执行者：Codex
范围：后端数据边界、迁移、事务服务、组合 API 与测试
未包含：前端写入、Timeline 管理、Follow-up、计划项目规范化

### 实际修改

- 新增 Alembic revision `20261008_0002`，为 Episode 增加结构化上下文和更新时间，为双镜头子对象增加审计时间与可选测量值。
- 新增人工 `SafetyCheck`、最小 `EvidenceReference` 和 `EpisodePlanLink`。
- 新增 `POST /api/v1/episodes/complete`，在同一事务内创建 Episode、Observation、OwnerInterpretation、安全确认、可选 VeterinaryEscalation、计划关联与证据引用。
- 保留 Phase 0.1 的细粒度端点以维持兼容。
- 新增 6 个组合记录测试，覆盖正常保存、人工危险信号、计划关联、无效计划回滚、安全输入矛盾和 Observation 必填。

### 测试中发现并修复

第一次运行出现 3 个失败：`model_dump(mode="json")` 将 `acknowledged_at` 转成字符串，SQLite DateTime 拒绝写入。修复为保留 Python datetime，仅显式转换枚举值。修复后新增测试全部通过。

最终读取审查又发现 SQLite 会在重新加载时丢失 Safety/Evidence 的时区标记；响应模型现统一恢复 UTC，并增加保存后从 Timeline 重新读取的断言。

本地 `relapaw.db` 的业务表符合 Phase 0.1，但 `alembic_version` 记录为空。确认表与数据后先安全 stamp 到 `20261007_0001`，再升级到 `20261008_0002`；现有 1 条宠物数据保留，`alembic check` 无模型差异。

### 明确边界

- SafetyCheck 完全来自用户显式选择，不运行关键词或医疗规则。
- EvidenceReference 仅记录对象来源与字段路径，不生成 Claim。
- 本切片未创建 Follow-up 或 ObservationPlanItem 表，避免在对应用例设计前提前固化结构；后续切片使用独立 migration 演进。
- 没有提交或 push。

## 2026-10-08 — Slice 1 前端：Understand 手工记录闭环

执行者：Codex
范围：前端类型、API client、Understand 表单、保存导航与交互测试

### 实际修改

- 扩展前端 Episode、Observation、SafetyCheck、EvidenceReference 与完整创建请求类型。
- 新增 `createCompleteEpisode` API client。
- 将 Understand 从静态占位改为真实表单：发生时间、类型、原始描述、双镜头、地点、触发背景、持续时间、次数和 1–5 强度。
- 增加显式人工 Safety Check；只有用户选择紧急情况后才展示危险信号清单和持续兽医提示。
- 正常保存后切换到 Timeline，使新数据由真实 Timeline API 重新读取。
- 保存失败时保留全部输入并允许原地重试。
- 移除 Context / Historical Context / Possible Explanations 等容易被误解为已实现 AI 的占位卡片。

### 测试覆盖

- 双镜头必填验证不会发起 API 请求。
- 正常记录请求保持 Observation 与 OwnerInterpretation 分层。
- 兽医安全分支只提交用户显式勾选的危险信号。
- 网络失败后草稿保留，第二次提交可成功。
- 发生时间无效时前端阻止提交。

### 边界修复

检查状态切换时发现：从紧急切回正常后，隐藏的补充说明不能继续进入请求，否则会与后端 Safety 契约冲突。请求构造现仅在紧急状态下包含 `other_concern`。

本切片没有加入自动文本拆分、情绪判断、风险检测或医疗诊断，也没有提交或 push。

## 2026-10-08 — Slice 2：Timeline 记录管理闭环

执行者：Codex
范围：Episode 聚合详情、Timeline 筛选、事务编辑、级联删除与前端管理状态机

### 编码前审计发现

- Slice 1 未提交修改仍完整存在，数据库位于 `20261008_0002 (head)`，原有 18 项后端与 19 项前端测试通过。
- Timeline 已有宠物隔离、分页和稳定排序，但没有真实筛选、详情、编辑或删除能力。
- Episode 关系已为 Observation、OwnerInterpretation、SafetyCheck、EvidenceReference、VeterinaryEscalation 和 EpisodePlanLink 配置删除级联，无需新 migration。
- EvidenceReference 的 `source_id` 是多态编号而非数据库外键，编辑时必须由服务层重建，不能依赖数据库修复悬空引用。
- 当前没有 Follow-up 模型；本切片不假装处理尚不存在的关联。Slice 4 引入 Follow-up 时必须重新审查 Episode 删除策略。

### 实际架构选择

- 新增 `GET /api/v1/episodes/{episode_id}`，返回完整 Episode 聚合，包括 VeterinaryEscalation。
- Timeline 支持带时区的 `from`、`to`、`episode_type` 和 `plan_id`；查询与 count 共用过滤条件，并继续使用 `happened_at DESC, id DESC`。
- 使用 `PUT /api/v1/episodes/{episode_id}` 完整替换允许编辑的聚合区域。请求模型禁止额外字段，因此不能提交 `pet_id`、SafetyCheck 或 VeterinaryEscalation。
- Observation 与 OwnerInterpretation 始终使用不同请求字段、表、响应区域和前端表单组。
- 编辑事务替换双镜头子对象并重建 RAW_OWNER_INPUT、OBSERVATION、OWNER_INTERPRETATION EvidenceReference；SafetyCheck、VeterinaryEscalation 和计划关联保持不变。
- 新增明确的 `DELETE /api/v1/episodes/{episode_id}`；数据库外键与 ORM 级联共同清理现有聚合子对象，成功返回 204。
- 前端未引入路由依赖，Timeline 内使用 list/detail/edit/delete-confirm 状态机。详情显示原始输入、双镜头、结构化背景、人工 Safety、兽医升级和 Evidence 来源。

### 修改文件

- `backend/app/schemas/episode.py`
- `backend/app/services/timeline.py`
- `backend/app/services/records.py`
- `backend/app/api/routes/episodes.py`
- `backend/app/api/routes/pets.py`
- `backend/tests/test_timeline_management.py`
- `frontend/src/types.ts`
- `frontend/src/api.ts`
- `frontend/src/pages/Timeline.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- Phase 1 开发留痕文档

### 测试发现与修复

- 首次后端新增测试发现：替换子对象并 flush 后，当前 SQLAlchemy 会话中的 Episode 关系集合仍保持清空状态，导致成功响应不包含刚写入的 Observation。修复为在事务中同步设置新的关系集合，并用详情读取再次验证。
- Timeline 改用真实详情请求后，旧前端测试桩没有模拟详情端点。补充真实端点测试桩并将断言改为等待异步详情加载，没有降低功能断言。
- 详情渲染对 Phase 0.1 旧测试数据缺少 Evidence 数组不够健壮，已增加诚实的“暂无来源记录”降级显示。

### 明确限制与风险

- PUT 替换会为 Observation、OwnerInterpretation 和对应 EvidenceReference 创建新 ID；Phase 1 尚无子对象修订历史，旧版本不会伪装为仍可追溯。
- 前端当前开放时间范围和记录类型筛选；`plan_id` 后端契约已完成，计划选择器将在 Observation Plan 具有真实列表入口时接入，避免伪造计划选项。
- Follow-up 尚未建模；未来加入后必须决定阻止删除、保留 tombstone 或显式级联，不能沿用当前假设。
- 人工产品验收仍未执行；本切片未提交、未 push。

### AI Code Review 与修复

自动测试后执行了聚合边界、数据丢失、错误恢复和界面可达性审查，发现并修复：

1. 初版编辑界面只提交第一条 Observation 和 OwnerInterpretation，可能在 PUT 替换语义下丢失其余子对象。现改为逐条编辑、添加和删除，并提交完整集合。
2. 初版只开放地点与触发背景，没有真正开放 `context`、持续时间、频率和强度。现补齐这些结构化字段；`context` 必须是有效 JSON 对象。
3. 详情虽返回 `updated_at`，初版没有向用户显示。现已在结构化背景中展示更新时间。
4. 204 删除响应不能调用 `response.json()`；API client 已显式处理 204。

复审未发现 SafetyCheck/VeterinaryEscalation 被普通 PUT 改写、跨宠物 Timeline 泄漏、Evidence 悬空或底部导航覆盖确认动作的问题。

## 2026-10-08 — Slice 4：Follow-up 复评闭环

执行者：Codex
范围：复评生命周期、到期待办、事务完成、新旧 Episode 双向追溯

### 编码前审计发现

- Slice 1 与 Slice 2 的未提交修改完整保留；起始回归为后端 25 项、前端 26 项通过，数据库为 `20261008_0002 (head)`。
- 项目没有 Follow-up 表、schema、接口或迁移；Today 只有宠物概览和静态 Observation Plan 区域，可安全加入独立异步待办状态。
- Episode 原有删除会级联现有聚合子对象。加入复评关系后继续级联会破坏历史，因此必须改为明确冲突并阻止删除。
- EvidenceReference 是服务层维护的多态来源；复评结果需要新增 `FOLLOW_UP` 来源，不能伪装成 Claim 或模型结论。

### 实际架构选择

- 新增 `episode_follow_ups` 与独立 revision `20261008_0003`。生命周期状态为 `PENDING / COMPLETED / CANCELLED`，复评结果标签为独立的 `PERSISTING / IMPROVED / WORSENED / RESOLVED / NEW_SIGNS`，避免混淆工作流状态与用户观察。
- `source_episode_id` 和可空且唯一的 `result_episode_id` 都使用受限外键；数据库约束禁止 source/result 相同并校验状态字段一致性。
- 创建时间必须带时区并归一为 UTC；Today 查询使用客户端时区偏移区分当天到期和逾期，且始终按 pet 隔离。
- 完成复评在同一数据库事务中复用完整 Episode 聚合创建服务，重新保存原始输入、Observation、OwnerInterpretation 和人工 SafetyCheck，创建 `FOLLOW_UP` EvidenceReference，再设置 result、outcome 和 completed_at。失败时全部回滚，source Episode 不变。
- 已完成或取消的 Follow-up 不能再次完成；只有 PENDING 可取消。有关联复评历史的 Episode 后端返回 `EPISODE_HAS_FOLLOW_UPS`，前端同时持续说明并禁用删除入口。
- Episode 详情返回发起的 Follow-up 及作为结果的 Follow-up，Timeline 可双向进入相关详情；Today 成功完成后移除待办并打开新 Episode。

### 修改文件

- `backend/alembic/versions/20261008_0003_episode_follow_ups.py`
- `backend/app/domain/enums.py`
- `backend/app/models/entities.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/episode.py`
- `backend/app/schemas/follow_up.py`
- `backend/app/services/follow_ups.py`
- `backend/app/services/timeline.py`
- `backend/app/api/routes/follow_ups.py`
- `backend/app/api/routes/episodes.py`
- `backend/app/api/router.py`
- `backend/tests/test_follow_ups.py`
- `frontend/src/types.ts`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/pages/Today.tsx`
- `frontend/src/pages/Timeline.tsx`
- `frontend/src/App.test.tsx`
- Phase 1 开发留痕文档

### 测试发现与修复

- 新的前端自定义时间测试最初使用“运行时当前时间 + 1 小时”，在测试进程日期与浏览器模拟日期不一致时产生假失败。改为明确的未来时间，只消除环境不确定性，仍保留过去时间被拒绝和成功提交的功能断言。
- 详情初版虽由后端阻止删除复评历史，但前端仍允许进入删除确认。复审后增加持续说明并禁用删除按钮，让限制在操作前可见。
- 完成复评响应需立即包含新建的 `FOLLOW_UP` EvidenceReference；服务在事务中同步更新关系集合，避免仅依赖下一次数据库重载。

### AI Code Review 与已知边界

复审覆盖状态转换、宠物隔离、时区、事务边界、source 不变性、Safety 重做、Evidence 完整性和删除保护。未发现 Observation 与 OwnerInterpretation 混合、自动医疗判断、跨宠物读取或部分完成写入。

- Today 只展示到期和逾期 PENDING 项；未来项目保留在 Episode 详情中，不制造通知或后台任务。
- Follow-up 可以提前通过后端接口完成，但当前 Today UI 只开放可行动项目；本阶段没有推送和后台调度。
- 人工产品验收仍未执行；没有 commit，也没有 push。

### Slice 4 人工验收

2026-10-08 已由用户在真实浏览器完成主路径：创建原 Episode、安排到期复评、Today 打开复评、分开填写原始输入/Observation/Owner Interpretation、重新完成人工 Safety Check并保存。数据库复核确认 source Episode `1` 保持不变，result Episode `2` 新建，Follow-up 为 `COMPLETED / IMPROVED`，并存在 `FOLLOW_UP -> source_episode_id` EvidenceReference。原记录与结果记录可双向导航，删除保护可见。Slice 4 人工验收通过。

## 2026-10-08 — Slice 5：Observation Plan 审计与实施计划

### 审计发现

- 现有 `observation_plans` 保存 pet、状态、起止时间、目标及旧版 `items_to_observe` JSON；已有基础 list/create/patch API。
- `episode_plan_links` 已能把 Episode 关联计划，完整记录创建和 Timeline `plan_id` 筛选已有测试。
- 当前没有规范化 `ObservationPlanItem`、计划详情聚合、明确状态转换、关联 Episode 列表或删除策略。
- Today 仍显示静态计划占位，Understand 没有真实计划选择器，Timeline 详情未展示计划入口。

### 实施方案

- 新增 `20261008_0004`，建立排序明确的 `observation_plan_items`，保留旧 JSON 读取兼容；新写入同步结构化项目。
- 状态只允许 `DRAFT -> ACTIVE -> COMPLETED/CANCELLED`，终态不再修改；日期必须带时区，结束时间不得早于开始时间。
- 计划详情返回项目及关联 Episode 摘要；Episode 只能关联同宠物计划。有关联记录的计划保留历史，不物理删除。
- Today 展示 ACTIVE 且处于日期范围内的计划；支持查看、完成和二次确认取消。Understand 提供真实计划选择；Timeline 详情显示计划关联和进入计划详情入口。
- 不实现提醒、推送、后台调度、AI 分析或自动完成。
- 测试覆盖迁移、状态转换、宠物隔离、关联完整性、Today 状态、创建/完成/取消、Understand 关联和错误重试。

### Slice 5 实现与 Review

- 新增 migration `20261008_0004` 与 `ObservationPlanItem`，项目按 plan 内唯一 `sort_order` 排序，计划删除时级联项目；旧 `items_to_observe` 保留并可在创建时转换为结构化项目。
- 新增计划详情读取；list/detail 均加载结构化项目。状态转换限制为 `DRAFT -> ACTIVE/CANCELLED`、`ACTIVE -> COMPLETED/CANCELLED`，终态不可再次修改。
- Today 使用真实 ACTIVE 计划，覆盖 loading、empty、error/retry、创建、完成和二次确认取消；不包含通知或后台调度。
- Understand 加载真实 ACTIVE 计划选择器，完整 Episode 创建继续由后端校验同宠物后写入 EpisodePlanLink；Timeline 详情展示计划关联。
- Review 发现专项测试原先把跨宠物计划关联预期为 404，实际契约为更明确的 `409 PLAN_PET_MISMATCH`；测试改为锁定真实隔离语义，没有弱化断言。
- 未发现 Observation/Interpretation 合并、自动判断、跨宠物关联或终态反复修改。没有 commit、没有 push。

### Slice 5 人工验收

2026-10-09 用户已在真实浏览器完成计划创建、结构化观察项目展示、Understand 关联计划创建 Episode、Timeline 详情显示 `关联计划 #1`、完成计划，以及取消计划二次确认。数据库复核确认 Episode `3` 通过 EpisodePlanLink 关联 Plan `1`；Plan `1` 为 `COMPLETED`，临时 Plan `2` 为 `CANCELLED`。完成或取消后均从 Today 活动计划区域消失，历史 Episode 未删除。Slice 5 人工验收通过。

## Phase 1 最终收尾 — 2026-10-09

### Veterinary Escalation 审计

- 现有后端已具备人工建立、按 Episode 列表和通用 PATCH 骨架，状态枚举为 `OPEN`、`SHARED_WITH_VET`、`CLOSED`。
- 原实现允许任意合法枚举间跳转，也允许直接建立终态记录；Timeline 仅展示状态，没有人工分享或关闭入口。
- Episode 普通编辑继续明确排除 SafetyCheck 与 VeterinaryEscalation，避免静默改写安全历史；本次不需要数据库变化或新 migration。

### 实际实现

- 人工 VeterinaryEscalation 只能以 `OPEN` 建立。
- 状态转换限制为 `OPEN -> SHARED_WITH_VET/CLOSED`、`SHARED_WITH_VET -> CLOSED`；`CLOSED` 为终态，禁止状态回退或内容重写。
- 统一错误新增 `INVALID_VETERINARY_ESCALATION_TRANSITION` 与 `VETERINARY_ESCALATION_CLOSED`，不存在记录继续使用 `VETERINARY_ESCALATION_NOT_FOUND`。
- Timeline 的持续 Safety 区域新增“标记已分享给兽医”和“关闭升级”；操作失败保留原状态并提供页面内重试反馈，关闭后不再显示状态操作。
- 前端 EvidenceReference 类型补齐已由 Follow-up 实际使用的 `FOLLOW_UP`，使 TypeScript 契约与后端一致。

### AI Code Review

- 复审状态转换、终态保护、普通 Episode 编辑边界、页面持续 Safety 提示、错误反馈、测试删除情况、污染与密钥模式。
- Review 发现：初版前端在 PATCH 成功后额外刷新 Episode；若刷新失败会把成功操作误报为失败。修复为直接使用 PATCH 返回的 VeterinaryEscalation 更新当前聚合，随后重新执行完整前端测试与 build。
- 未发现 Observation/Interpretation 合并、自动医疗判断、自动风险评分、测试删除或弱化、密钥进入变更的问题。

### 修改文件

- `backend/app/api/routes/resources.py`
- `backend/tests/test_resources.py`
- `frontend/src/api.ts`
- `frontend/src/types.ts`
- `frontend/src/pages/Timeline.tsx`
- `frontend/src/App.test.tsx`
- Phase 1 README、Scope、Implementation Log 与 Test Results

### 未完成项与风险

- Veterinary Escalation 与移动/桌面核心流程仍需用户最终人工验收。
- 当前状态只记录枚举与人工摘要，没有独立状态变更时间线；Phase 1 按既定最小模型保留此限制。
- SQLite 的并发与时区能力仍弱于未来 PostgreSQL；既有 Starlette TestClient/httpx 弃用警告仍待依赖升级阶段处理。
- 没有 commit，没有 push；全部 Phase 1 修改继续保持未提交。

### Phase 1 最终人工验收

2026-10-09 用户在真实浏览器完成 Veterinary Escalation 生命周期验收：人工风险记录从 `OPEN` 转为 `SHARED_WITH_VET`，再转为 `CLOSED`；关闭后状态操作消失，Safety Check、Evidence 与“不进行诊断、不替代兽医”提示继续保留。

用户随后使用浏览器设备模拟在 `400 x 640` 窄屏下检查 Today、Understand、Timeline 与 Us。四个主页面均保持单列/适配布局，内容可滚动，Timeline 卡片无横向溢出，底部导航保持独立且未遮挡主页面操作。结合此前桌面浏览器验收，Phase 1 人工产品验收通过。

尚未建立 Phase 1 Git 基线；继续等待用户明确授权 commit，且不得 push。
