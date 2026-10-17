# Batch 1 Test Results

日期：2026-10-17

## 定向测试

- 后端 capabilities + understanding：18 项通过；
- 前端 CapabilitiesContext + UnderstandingPanel + App：60 项通过；
- production build：通过。

## 完整回归

- 后端：119 项通过；
- 前端：73 项通过；
- TypeScript + Vite production build：通过；
- `git diff --check`：通过。

测试未发送真实 Provider 请求。
## Batch 2 定向测试（2026-10-17）

命令：

```powershell
python -m pytest tests/test_demo_seed.py tests/test_demo_verify.py tests/test_demo_capabilities.py -q
```

覆盖：空库 seed、真实 Alembic fresh migration、幂等、事务回滚、manifest 版本、迁移版本、关键关联、录制结果和基线 lineage。定向结果：13 项通过。

全量后端回归：`127 passed`。`compileall` 与 `git diff --check` 通过。

## Batch 3 定向与回归（2026-10-17）

- 静态托管定向测试：8 项通过；
- 后端全量：`135 passed`；
- 前端全量：`73 passed`；
- `npm run build` 成功；
- 真实 production build 的 `/`、哈希资产、`/health`、Capabilities API 与未知 API 404 集成检查通过。

## Batch 4 Launcher 集成（2026-10-17）

- 从无 `.demo`、无 `dist` 状态完成 start；
- fresh migration、seed、verify、后台单服务启动通过；
- 重复 start、verify、stop、重复 stop 通过；
- reset 后重新 migration/seed/verify 通过，并保持停止；
- 8000 被既有开发服务占用时安全拒绝，既有服务健康未受影响；
- PowerShell 语法与删除白名单契约自动测试通过。
- Batch 4 完成后全量回归：后端 `138 passed`，前端 `73 passed`，production build 成功。

## Batch 5 自动发布回归（2026-10-17）

- 连续三次 reset 成功；dataset version、base date 与数据库大小一致；
- 后端全量 `138 passed`，前端全量 `73 passed`，production build 成功；
- 单服务主演示 API：6 个 Episode、录制 Claim、READY 7 日基线与 30 条 lineage 通过；
- NORMAL Episode 在 AI disabled 下返回 403 且 AnalysisRun 数量不变；
- ESCALATE_TO_VET Episode 返回 `BLOCKED_BY_SAFETY`；
- 静态根页面、health 与 capability 合约通过；
- 源码密钥形态扫描无命中，demo 日志为空且无正文/密钥，运行产物均未被 Git 跟踪；
- `git diff --check` 通过。

人工验收完成：

- 360×680：引导、今天、记录、足迹、我们均通过；
- 720×900：四页面通过，发现并修复 hero 文字挤压与展开卡片跳位后复验通过；
- 1200×900：四页面和展开卡片通过；
- 键盘 Tab 焦点与 Enter 激活通过；
- Chrome 与 Edge 通过；
- reduced motion 由现有媒体查询覆盖并在 Final Review 中确认；
- 360×680 追加复验：引导第三页、记录背景分组、今天到记录跳转、记录页进入效果及详情返回区均通过；
- 最后一轮 UI 修正后前端全量 `73 passed`，production build 成功；
- 用户完成全页面巡检并确认未发现其他明显错误；
- 演示服务停止后确认 8123 端口释放。
