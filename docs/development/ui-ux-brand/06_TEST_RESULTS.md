# Test Results

## 2026-10-15 — 产品结构收口 Slice 1

- `frontend`: `npm test -- --run` → 4 个测试文件、63 项测试全部通过。
- `frontend`: `npm run build` → TypeScript 与 Vite production build 通过。
- `git diff --check` → 通过。
- 新增/更新覆盖：记录页标题、纯展示日期栏、被动复评空状态、移除错误 Baseline 跳转、移除“关系足迹/生活事件”重复入口、保留宠物档案与说明内容。
- 本轮没有修改后端、数据库迁移、API 或模型适配器；后端完整回归保留到 UI/UX 阶段关闭门禁统一执行。
- Chrome headless 真实渲染验收：390×844 与 1440×1000 下 Today、Record、Us 均满足 `scrollWidth === clientWidth`，无横向溢出。
- DOM 交互清单确认：Today 空状态不再包含“从足迹安排复评”或“日常的变化”按钮；Us 不再包含“关系足迹”和“生活事件”按钮；最近七天不再产生按钮节点。
- 视觉复核确认：移动端底部导航未遮挡当前首屏内容，桌面端记录表单双栏、Today 主行动/空状态和 Us 三块底部信息层级正常。
- 额外复验首次 Onboarding 在 390×844 下可正常换行、无横向溢出；未发现需要修复的新增阻断项。

## 2026-10-13 — Slice 1 自动检查

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 59 passed |
| 前端 production build | passed |
| 后端全量测试 | 114 passed |
| TypeScript | production build 中通过 |
| 新增运行时依赖 | 0 |
| `git diff --check` | passed |

自动检查证明组件契约、导航行为、业务测试和构建没有回退。360px、720px 与宽桌面的真实浏览器视觉效果仍需人工验收。

## 2026-10-15 — 当前工作区回归

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 60 passed |
| 前端 production build | passed |
| 后端全量测试 | 114 passed |
| `git diff --check` | passed |
| Chrome 360×800 | 一级页面无横向溢出；移动底栏正常 |
| Chrome 720×960 | Onboarding 与每日开场构图正常 |
| Chrome 1440×1000 | 桌面侧栏与一级页面正常；开场标题修复后复验通过 |

本轮截图为本地验收临时产物，不纳入仓库。Edge、键盘完整遍历、深层业务状态和长数据场景仍需继续验收，不能据此关闭整个阶段。

## 2026-10-15 — 四方向视觉变体

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 60 passed |
| 前端 production build | passed |
| `git diff --check` | passed |
| Chrome 1425px 宽桌面 | 四方向 2×2 对比、文字层级与手机画板均正常 |
| Chrome 375px 宽移动端 | 单列布局正常，无横向溢出 |

对比页使用独立路由与作用域样式，不替换当前生产首页。四个方向共享同一组 Today 内容，以减少内容差异对视觉判断的干扰。

## 2026-10-15 — 一级页面差异化重构

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 60 passed |
| 前端 production build | passed |
| `git diff --check` | passed |
| Chrome 820×920 | Understand、Timeline、Us 均使用桌面侧栏；三页差异化构图正常 |
| 页面宽度 | `scrollWidth === clientWidth`（820px） |

本轮重点解决用户截图中的底栏遮挡、页面模板化、英文内部类型直接暴露、表单工具感与情感层级不足。

## 2026-10-15 — 自然陪伴手账版

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 60 passed |
| 前端 production build | passed |
| `git diff --check` | passed |
| Chrome 820×920 | Today、Understand、Timeline、Us 主视觉与线稿正常 |
| Chrome 375px | `scrollWidth === clientWidth` |

初次 820px 验收发现 Today 主卡过窄、Timeline 标题被压成竖排；响应式调整后重新截图复验通过。

## 2026-10-15 — 抽象伙伴与手作温度

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 60 passed |
| 前端 production build | passed |
| `git diff --check` | passed |
| 本地服务 | `http://127.0.0.1:5173/` 返回 200 |
| Edge 自动截图 | GPU 进程在当前 Windows 环境异常退出，未生成截图 |

代码原生 SVG、响应式样式与现有业务测试均通过；本轮自动截图受本机 Edge GPU 进程限制，实际视觉效果通过正在运行的本地热更新页面交由人工继续验收。

## 2026-10-15 — 小动物字迹与图标精修

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 60 passed |
| 前端 production build | passed |
| `git diff --check` | passed |
| 本地服务 | `http://127.0.0.1:5173/` 返回 200 |

本轮仅调整字体角色、配色层次、导航 SVG 与关键区域排版，不改变数据和交互契约。

## 2026-10-15 — “我们”信息卡交互修订

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 63 passed |
| 前端 production build | passed |
| `git diff --check` | passed |

新增自动化覆盖：宠物档案原地展开、切换卡片时自动收起、记录原则与数据隐私说明可展开。此次修改只改变本地展示状态，不新增 API 或持久化行为。

## 2026-10-15 — 手账贴画试点

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 63 passed |
| 前端 production build | passed |
| `git diff --check` | passed |

贴画使用代码原生 SVG 和纯 CSS 材质效果，没有增加外部图片、字体或运行时依赖；装饰层设置为不可交互，不影响原有表单与折叠卡操作。

人工反馈后的纸页拼贴修订继续通过 63 项前端测试、production build 与 `git diff --check`。

## 2026-10-16 — 核心记录闭环与异常恢复

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 64 passed |
| 前端 production build | passed |
| 后端全量测试 | 114 passed |
| `git diff --check` | passed |

新增/更新覆盖：步骤导航、保存后直达新 Episode、候选创建后的目标分区导航、观察计划加载失败与重试、重试期间草稿保留。当前结果证明自动化与构建无回退；本轮工作仍未取得 commit/push 授权。

## 2026-10-16 — 阶段关闭回归

| 检查 | 结果 |
| --- | --- |
| 前端测试 | 5 个测试文件、69 项通过 |
| 前端 production build | passed |
| 后端全量测试 | 114 passed |
| `git diff --check` | passed |
| 400×640 首次引导与建档 | 人工验收通过，三页与主要操作无需额外滚动 |
| 一级页面与深层状态 | 人工验收通过，无已知遮挡、错误重复跳转或虚假可点击卡片 |
| 焦点、步骤语义与触控目标 | 原生控件／`aria-current` 保留，关键触控目标达到或扩展至 44px |
| reduced motion | 翻页和通用动画均提供降级规则 |

正式构建只包含产品入口；三个视觉研究路由改为仅在开发环境动态加载。清理后正式 CSS 约 87.85 KB、JS 约 314.55 KB，分别低于清理前约 106.01 KB 与 330.64 KB。用户已完成最终浏览器检查并确认当前视觉可接受。
