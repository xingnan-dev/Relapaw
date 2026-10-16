# Requirements

## 目标

1. 建立柔雾、水彩、梦境感但仍可信可读的 Relapaw 品牌语言，强化“Observation ≠ Interpretation”与“Beyond the Paw. The Bond.”。
2. 统一 Today、Understand、Timeline、Episode Detail、Baseline、Us、Onboarding 和 Pet Setup 的页面层级、导航、操作与反馈。
3. 同时适配约 360px 手机、720px 应用宽度与宽桌面；桌面不再出现大面积无意义留白，移动端不产生横向溢出或底部遮挡。
4. 保留并加强 Safety、Evidence、Uncertainty、模型来源、用户确认/拒绝和 `NOT_QUALIFIED` 边界，不用视觉精简隐藏重要状态。
5. 将 loading、empty、error、blocked、stale、success、warning、insufficient-data 和 withdrawn/active 等状态统一到可复用组件与文案层级。
6. 保持键盘可达、清晰焦点、至少 44px 触控目标、合理对比度、reduced-motion 和语义化 HTML。
7. 建立可重复的页面截图与视口验收矩阵，并保证现有自动测试、build 和业务行为不回退。

## 非目标

- 不修改 API、数据库、migration、后端服务或业务状态机。
- 不重新授予当前 Provider/模型/Prompt 组合资格，不隐藏 `NOT_QUALIFIED`。
- 不接入 RAG、Agent、多模态、自动医疗判断、部署或监控。
- 不引入大型组件库或为视觉效果增加不必要的运行时依赖。
- 不伪造用户评价、宠物数据、模型结果或比赛证据。

## 现状审计摘要

- 已有 CSS token、Button、Surface、StatusNotice、响应式窄屏规则和 reduced-motion 基线。
- 应用壳固定为 720px 单列，宽屏两侧留白大，缺少桌面信息布局策略。
- 页面大量混用 legacy class、原生 button/card 和 primitive，视觉层级与交互反馈不一致。
- 中英文标题、枚举值、技术字段和用户语言混杂，尚无统一产品文案规则。
- 导航使用字符符号作为图标，品牌标识仍是文字，缺少正式图形语言。
- 长 Timeline、Analysis、Baseline 来源列表已经可滚动，但缺少页面级密度、折叠和阅读节奏规范。
- 当前测试重心是功能与语义；尚无稳定的页面截图回归基线。

## 人工视觉方向反馈

- 用户拒绝首版深绿、硬边框与扁平单色图标方向。
- 用户提供的参考图偏好为低饱和粉紫、薄荷、雾蓝和柔黄光的水彩叠染、半透明纸张与手绘线条质感。
- 实现只提取配色、材质和光影特征，不复制参考图中的具体构图、符号或资产。
- 第二张参考进一步明确：需要让水彩晕染、粉笔擦痕、植物/动物手稿与局部发光成为可见的氛围层，不能只停留在柔和配色。
