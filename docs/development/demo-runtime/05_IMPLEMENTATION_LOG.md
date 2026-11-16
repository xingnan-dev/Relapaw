# Batch 1 Implementation Log

日期：2026-10-17

使用工具：OpenAI Codex 桌面工作区代理。

## 实现

- 后端配置增加 `RELAPAW_ENV` 与默认关闭的 `RELAPAW_AI_ENABLED`；
- 新增 `GET /api/v1/capabilities`，只返回环境、合成数据、数据集版本、AI 可用性与固定资格状态；
- AnalysisRun 创建路径在 NORMAL Safety 后检查功能开关；缺失或非 NORMAL Safety 继续使用既有安全语义；
- 前端新增 `CapabilitiesProvider`，失败时使用 AI 关闭的安全默认值；
- Timeline 把能力状态传给 UnderstandingPanel；
- AI 关闭时移除创建/重试以及历史 Claim 决定入口，只读保留模型、Evidence、Uncertainty 与 stale 信息；
- 合成 demo 能力就绪时在应用壳显示数据集标识；
- `.env.example` 记录新的安全默认值。

## 明确未实施

## Batch 2（2026-10-17）

- 新增 `app/demo/dataset_v1.py`，冻结 `relapaw-demo/v1-observe-review-baseline` 合成数据；
- 新增事务化、幂等 seed，生成 1 个合成宠物、6 个相对时间 Episode、Safety/Evidence、1 个录制 AnalysisRun 与 7 日基线；
- 新增原子 manifest 和数据库完整性 verify；
- CLI 仅接受 `demo` 环境、关闭 AI 且数据库精确指向 `backend/.demo/relapaw-demo.db`；
- 新增空库迁移、幂等、回滚、损坏检测测试；
- `.demo` 与批次测试临时产物均被 Git 忽略。

## Batch 3（2026-10-17）

- 配置新增 `RELAPAW_STATIC_DIR`，demo 模式要求它精确指向本仓库 `frontend/dist`；
- 应用工厂在 API 与 `/health` 后挂载静态构建，开发模式未配置时继续保持 API-only；
- 缺目录、相对路径、错误目录或缺 `index.html` 均在应用启动前失败；
- `/api/v1/*` 与 `/health` 保持优先，未知 API 不会返回前端 HTML；
- 真实 `npm run build` 产物已完成同源 root、asset、health 和 API 集成验证。

## Batch 4（2026-10-17）

- 新增 `scripts/demo.ps1`，提供 `start / verify / reset / stop` 唯一入口；
- 所有路径从 `$PSScriptRoot` 解析，数据库与删除目标限制在 `backend/.demo` 白名单；
- 服务仅监听 `127.0.0.1`，不使用 reload，端口冲突时不终止未知进程；
- PID 控制同时验证 PID、Python 路径、启动时间、固定命令记录和 health/capability 合约；
- start/stop 均幂等，reset 重建数据后保持服务停止；
- 新增 `docs/DEMO_OPERATOR_GUIDE.md`，覆盖准备、主演示、Safety 路径、重置、停止和故障处理。

## Batch 5（2026-10-17）

- 完成三次连续 reset、全量回归、主演示和 Safety 路径；
- 人工验收覆盖 360px、720px、1200px、键盘焦点/Enter、Chrome 与 Edge；
- 修复 720px 桌面壳内容区的 Timeline/Us 主视觉文字过窄问题；
- 修复 720px Us 展开卡片时两列重排和跳位问题，改为稳定单列手风琴；
- 修复 360px 引导第三页长标题强制不换行、插图重心偏右的问题；
- 修复 360px 记录页“当时的背景（可选）”图例突出卡片边界的问题；
- 主导航切页时显式重置独立内容滚动区，避免“今天 → 记录”保留旧滚动位置；
- 移除记录页标题区域在切页动画中突出的紫色装饰光晕；
- 统一记录详情返回按钮、眉题与标题的左边线和垂直间距；
- `prefers-reduced-motion` 的全局降速/关闭平滑滚动规则保留并经源码 Review；
- 上述修正逐项由用户在浏览器中复验通过；
- 阶段结束后停止 8123 演示服务并清理 `.demo`、`dist`、日志、PID 与测试临时产物。
