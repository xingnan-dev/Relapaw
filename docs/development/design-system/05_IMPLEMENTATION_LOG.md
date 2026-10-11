# Implementation Log

## 2026-10-11 — 编码前审计

- 现有 UI 已有绿色基调和基本卡片/按钮样式，但颜色、间距、圆角与阴影以硬编码散落在单一 CSS 文件中。
- loading/error/blocked/success 已有可读文案，类名与容器结构不统一，缺少复用组件契约。
- 控件最小高度为 42px，尚未达到本阶段采用的 44px 触控基线。
- 已支持 `prefers-reduced-motion`，但没有统一 `:focus-visible` 规则。
- 应用壳固定最大宽度 720px；窄屏表单已有单列回退，宽屏仍需可读行长和安全区规则。
- 本阶段采用渐进迁移，不修改业务逻辑、API、数据模型或 Phase 2 状态机。

## 2026-10-11 — 实现

- 在 `:root` 增加语义颜色、间距、圆角、阴影、焦点、布局、控件尺寸和动效 token。
- 全局原生 button/input/textarea/select 统一到 44px 控件基线，并增加高对比 `:focus-visible`。
- 新增零依赖 Button、Surface、StatusNotice primitive，保留原生 button 和显式 ARIA role。
- Understanding 迁移模型来源、Safety blocked、Provider 错误、completed、历史读取失败、失败运行和决定保存失败状态。
- 增加 420px 窄屏规则：缩小页面横向 padding、notice/action 单列、Claim 与页面操作可换行。
- 保留旧 CSS 类作为渐进兼容层，没有一次性重写 Today、Timeline、表单或导航。

## 明确未做

- 未修改任何 API、业务状态、数据库、migration 或 Provider 调用。
- 未引入 CSS framework、组件库、图标库或新运行时依赖。
- 未进行最终品牌、Logo、插画或完整页面视觉精修。
