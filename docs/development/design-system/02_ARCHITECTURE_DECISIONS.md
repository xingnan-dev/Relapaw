# Architecture Decisions

## DS-001：Token 使用 CSS custom properties

Token 放在全局 `:root`，语义命名优先于具体颜色命名。组件只消费语义 token，便于后续品牌精修而不改变业务 JSX。

## DS-002：保留原生 HTML 控件

Button 组件仍输出原生 `button`，Surface 输出语义可选的容器元素，StatusNotice 显式选择 `status` 或 `alert`。不建立隐藏语义的复杂抽象。

## DS-003：状态由文字、ARIA 与视觉共同表达

颜色仅作辅助；每个重要状态必须有可读文本。异步完成使用 `role=status`，需要用户注意的错误使用 `role=alert`，Safety 阻断保持明确文案。

## DS-004：渐进迁移

本轮先建立 primitive 并迁移 Understanding 核心状态；既有页面继续使用兼容类名。后续页面可以逐步迁移，不进行高风险的一次性重写。

## DS-005：零新增运行时依赖

使用 React、TypeScript 和原生 CSS；减少供应链与 bundle 风险，并保持现有测试结构。
