# AI Code Review

日期：2026-10-11

## 审查范围

- Design token 与全局控件基础样式；
- Button、Surface、StatusNotice primitive；
- Understanding 状态迁移；
- 响应式、键盘焦点、live region 和测试；
- Phase 3、数据与业务边界。

## 结论

未发现未关闭的高危或中危问题。实现保持原生 HTML 语义、零新增依赖和渐进迁移，没有改变 Phase 2 状态机、Safety 门禁或人工决定。

## 审查发现

1. **静态 notice 默认 live region**：StatusNotice 初始默认 `role=status`，会让模型来源和历史卡片在加载时被读屏器重复播报。
2. **Safety 文案重复**：统一组件加入标题后，旧正文仍包含同一前缀，造成视觉和测试重复。

两项均已修复并增加回归测试。剩余硬编码样式属于渐进兼容范围，完整品牌精修阶段再统一，不阻断本阶段。

## 剩余风险

- jsdom 不能验证真实浏览器的视觉对比、换行、滚动和焦点可见性，仍需人工验收。
- 本阶段只把 Understanding 迁移为示范；其他页面仍混用 legacy 类，后续应渐进迁移，避免一次性重写。
- 颜色 token 已形成语义层，但尚未以专用对比度工具进行数值审计。
