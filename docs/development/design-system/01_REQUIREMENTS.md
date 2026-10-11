# Requirements

## 目标

1. 以 CSS custom properties 冻结颜色、字体、间距、圆角、边框、阴影、动效和页面宽度。
2. 提供 Button、Surface、StatusNotice 三个最小基础组件，保持原生语义和可组合性。
3. 统一 loading、empty、error、blocked、success、warning、stale 的视觉与 ARIA 语义。
4. 建立清晰的键盘焦点、最小触控面积、disabled 状态和 reduced-motion 规则。
5. 支持窄屏手机、当前 720px 应用壳和更宽桌面视口，不改变四个一级导航。
6. 优先迁移 Phase 2 Understanding，以验证 Safety、模型来源、错误和用户决定层级。

## 非目标

- 不修改 API、数据库、migration 或业务状态机。
- 不进入 Phase 3，不创建长期记忆或量化 Baseline。
- 不进行最终 Logo、插画、字体授权或比赛级品牌精修。
- 不引入大型组件库、CSS framework、图标库或动画依赖。
- 不仅依靠颜色表达 Safety、错误、stale 或用户决定。
