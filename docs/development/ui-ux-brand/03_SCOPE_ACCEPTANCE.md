# Scope and Acceptance

## Slice 1：品牌基础与应用壳

- [x] 冻结品牌关键词、色彩、排版、图形与中文文案原则。
- [x] 扩展 token 和 primitive，统一按钮、卡片、badge、section 与状态反馈。
- [x] 完成手机、720px 和宽桌面应用壳及一级导航。
- [x] 不改变路由行为、页面状态或 API 调用。

## Slice 2：核心记录路径

- [x] 精修 Today、记录流程、Timeline 与 Episode Detail。
- [x] Observation、Owner Interpretation、Safety 与 Follow-up 层级明确。
- [x] 长列表、编辑、删除和失败保态在各视口可用。

## Slice 3：AI 理解与长期记忆路径

- [x] 精修 Understand、Claim/Evidence/Uncertainty、Analysis history。
- [x] 精修 Memory Candidate、Baseline 窗口、指标和来源下钻。
- [x] 模型来源、人工决定、stale、insufficient-data 与 `NOT_QUALIFIED` 边界清晰可见。

## Slice 4：Onboarding、Us 与全局状态

- [x] 精修 Splash、Onboarding、Pet Setup 与 Us。
- [x] 统一 loading、empty、error、blocked、success、warning 和撤回状态。
- [x] 完成长文案、空数据、错误数据和低密度场景。

## 阶段出口

- [x] 360px、720px、宽桌面无明显遮挡、横向溢出或大面积无效留白。
- [x] Chrome/Edge、键盘、焦点、触控目标、对比度和 reduced-motion 验收通过。
- [x] 核心路径截图回归、前端测试、后端测试和 production build 通过。
- [x] AI Code Review、修复、完整回归和人工验收完成。
- [x] 第三方资产来源、密钥、构建产物和 Git 范围检查通过；最终依赖许可证清单保留到 RC。
- [ ] commit 与 push 分别获得用户明确授权。

人工验收于 2026-10-16 完成。阶段关闭不代表完成生产部署；图片压缩、最终许可证清单、PostgreSQL、监控与恢复演练继续由后续阶段处理。
