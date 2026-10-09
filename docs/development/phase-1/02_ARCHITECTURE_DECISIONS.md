# Phase 1 Architecture Decisions

## 1. 延续 Episode 聚合，不重复建 Observation 根对象

现有 `Episode` 继续作为一次记录的聚合根。`Observation`、`OwnerInterpretation`、`VeterinaryEscalation`、Follow-up 关系和计划关联都围绕 Episode 建立。Phase 1 不新增与现有含义重复的顶层记录表。

## 2. 组合写入使用事务型应用服务

新增“创建完整记录”用例，在一个事务内完成：

```text
Episode
  + Observation[]
  + OwnerInterpretation[]
  + SafetyCheck
  + optional VeterinaryEscalation
  + optional ObservationPlan link
  + EvidenceReference[]
```

原有细粒度端点可保留兼容，但前端主流程只调用组合端点，避免半条记录。

## 3. 结构化上下文使用明确列与受控值

高频、需要筛选或未来计算的字段使用明确列或子实体；仅低频开放补充信息保留 JSON。不得把全部 Phase 1 数据继续塞入 `Episode.context`。

建议新增或调整：

- Episode：`updated_at`、`duration_seconds?`、`frequency_count?`、`intensity?`、`location?`、`trigger_context?`
- Observation：`created_at`、`updated_at`、`unit?`、`measured_value?`
- OwnerInterpretation：`created_at`、`updated_at`
- EpisodePlanLink：关联 Episode 与 ObservationPlan

具体迁移以实现前模型评审为准；旧 `context` 保留向后兼容。

## 4. Follow-up 使用 Episode 自引用关系

新增 `EpisodeFollowUp` 关联表，而不是覆盖原 Episode：

```text
id
source_episode_id
result_episode_id (unique, nullable until completion)
scheduled_at
status: PENDING | COMPLETED | CANCELLED
outcome: PERSISTING | IMPROVED | WORSENED | RESOLVED | NEW_SIGNS
completed_at?
created_at
```

预约尚未填写结果时允许 `result_episode_id` 为空；完成时引用一个新的 Episode。一个复评只能完成一次，生命周期状态与用户主动选择的结果标签分别保存。

## 5. Observation Plan 项目规范化

现有 `items_to_observe` JSON 在迁移中保留读取兼容，同时引入 `ObservationPlanItem`：

```text
id
plan_id
label
description?
sort_order
is_required
created_at
```

Phase 1 不做提醒调度；只保存计划、项目、状态与 Episode 关联。

## 6. 最小 EvidenceReference

Phase 1 仅为人工记录建立对象级引用：

```text
EvidenceReference
- id
- episode_id
- source_type: RAW_OWNER_INPUT | OBSERVATION | OWNER_INTERPRETATION | FOLLOW_UP
- source_id?
- field_path
- observed_at
- recorded_at
- created_at
```

它不代表系统产生了 Claim，也不赋予任何内容更高真实性。Phase 2 才设计 AnalysisRun、Claim、Uncertainty 与 UserConfirmation。

## 7. Safety Check 保持人工显式输入

新增版本化的人工 Safety Check 结果，至少保存：选择的危险信号、自由文本、确认时间和结果。只有用户明确选择风险时创建/更新 VeterinaryEscalation。Phase 1 不实现关键词规则、自动分类或医学结论。

## 8. 编辑与删除边界

- 编辑 Episode 时不可更换 `pet_id`；需要跨宠物纠错时删除并重建。
- `happened_at`、结构化上下文、Observation 与 Interpretation 可编辑。
- 没有 Follow-up 时，删除 Episode 级联其聚合从属对象；一旦 Episode 作为复评 source 或 result，删除必须被明确阻止并返回冲突，不能静默破坏历史关系。
- API 使用完整资源更新或明确子资源端点，不接受无法审计含义的任意 JSON patch。

## 9. Timeline 查询

在现有稳定分页上增加可选筛选：`pet_id`、`from`、`to`、`episode_type`、`plan_id`。排序继续采用 `happened_at DESC, id DESC`。详情响应返回双镜头内容、安全状态、计划和复评链接。

## 10. 前端层级

- Understand：分步记录页，保存前展示人工 Safety Check。
- Timeline：列表、筛选、原位概要展开；完整详情使用层级页面。
- Today：快速记录、待复评、当前 Observation Plan。
- Us：仍作为长期资料入口，不在 Phase 1 扩张成分析仪表盘。

随着详情与编辑层级增加，Phase 1 允许引入轻量路由；若引入必须记录选型理由并保持四个一级 Tab 稳定。
