# Phase 1 Scope and Acceptance Criteria

## A. 数据与迁移

- [x] 新增独立 Alembic revision，可从 `20261007_0001` 升级到 Phase 1 head。
- [x] 迁移可在全新数据库和现有 Phase 0.1 数据库上成功执行。
- [x] Episode、Observation、OwnerInterpretation 具备必要审计时间。
- [x] Follow-up、ObservationPlanItem、计划关联、Safety Check 与最小 EvidenceReference 有明确约束和级联策略。
- [x] downgrade 至上一 revision 可在迁移测试数据库执行。

## B. 结构化记录闭环

- [x] 用户可以为当前宠物创建完整 Episode。
- [x] 原始输入、Observation 和 OwnerInterpretation 分开保存与返回。
- [x] 发生时间必须带时区；后端响应统一为 UTC 语义。
- [x] 结构化上下文支持持续时间、频率、强度、地点与触发背景，未知值不伪造为正常。
- [x] 组合创建在任一子对象失败时全部回滚。
- [x] 不存在的宠物或父记录返回统一 404；非法状态返回统一验证错误或冲突错误。

## C. 人工安全边界

- [x] 保存流程包含明确的人工 Safety Check。
- [x] 选择危险信号后显示持续可见的 Veterinary Escalation 提示。
- [x] 用户可以建立、查看和关闭人工 VeterinaryEscalation。
- [x] 文案明确“不做诊断、不替代兽医”。
- [x] 不存在自动医疗判断、自动风险分数或模拟 AI 输出。

## D. Timeline 与记录管理

- [x] Timeline 显示真实已保存 Episode，不使用伪造示例数据。
- [x] 后端支持按宠物、日期范围、类型和计划筛选；当前前端开放日期与类型筛选。
- [x] 分页保持 `happened_at DESC, id DESC` 稳定顺序。
- [x] 详情明确分区展示 Observation 与 Owner Interpretation。
- [x] 用户可以编辑记录并看到后端更新时间。
- [x] 用户可以经二次确认删除记录；关联影响有明确说明。
- [x] loading、empty、content、error/retry 状态齐全。

## E. 复评闭环

- [x] 用户可预约 2 小时、次日、3 天或自定义复评时间。
- [x] Today 显示到期或逾期的待复评项目。
- [x] 用户可记录持续、改善、加重、已消失或新情况。
- [x] 完成复评时创建新的 Episode，并与原 Episode 建立可追溯关系。
- [x] 原记录和复评记录可互相导航，且任何一方都不会被覆盖。

## F. Observation Plan

- [x] 用户可创建、查看、完成和取消 Observation Plan。
- [x] Plan 包含目标、起止时间及排序明确的观察项目。
- [x] Episode 可关联到 Plan，并在 Timeline 详情中显示。
- [x] 不实现后台提醒、推送或自动执行。

## G. Evidence 与未来可计算性

- [x] Slice 1 的原始输入、Observation 与 OwnerInterpretation 可追溯到 Episode、来源对象、字段路径、观察时间和记录时间。
- [x] EvidenceReference 不生成 Claim，不改变原始内容含义。
- [x] 原始记录保留未来 Phase 3 计算所需的时间、来源、值/单位与上下文。
- [x] 不实现 AnalysisRun、模型版本、知识来源或自动 Baseline。

## H. 前端体验与可访问性

- [x] 底部导航不遮挡表单、详情、确认区或键盘焦点。
- [x] Observation 与 Interpretation 不仅依靠颜色区分。
- [x] Safety 提示使用页面内持久区域并可被屏幕阅读器识别。
- [x] 主要动作有文字标签、清晰焦点和足够点击区域。
- [x] 移动宽度和桌面居中容器均可完成核心闭环。

## I. 测试与交付门禁

- [x] 后端覆盖成功、验证、事务回滚、筛选、级联与迁移测试。
- [x] 前端覆盖创建、失败重试、安全分支、编辑删除、复评和计划流程。
- [x] 后端测试、前端测试与前端 build 全部通过。
- [x] 完成 AI Code Review、修复、回归与真实开发留痕。
- [x] 完成人工产品验收。
- [x] 仅在人工授权后建立 Phase 1 Git commit；不得自动 push。

## 人工验收主路径

```text
已有宠物
  -> Today 快速记录
  -> 填写原始描述
  -> 分开填写 Observation / Owner Interpretation
  -> 补充上下文
  -> 完成人工 Safety Check
  -> 保存
  -> Timeline 找到并查看详情
  -> 编辑一次
  -> 安排复评
  -> Today 完成复评
  -> 原记录与复评双向可见
  -> 创建 Observation Plan
  -> 将新记录关联到 Plan
  -> 完成 Plan
```
