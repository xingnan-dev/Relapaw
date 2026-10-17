# Relapaw 本地演示操作手册

适用范围：比赛现场或本机离线演示。数据完全合成，运行时 AI 默认关闭；本手册不用于公网部署。

## 1. 首次准备

需要 Windows PowerShell、Node.js/npm，以及已经安装好依赖的 `backend/.venv`。在仓库根目录执行：

```powershell
.\scripts\demo.ps1 start
```

启动器会依次构建前端、迁移独立演示数据库、写入并校验固定合成数据，然后只在 `127.0.0.1:8000` 启动单一服务。浏览器打开：

```text
http://127.0.0.1:8000/
```

如果 8000 已被占用，启动器不会终止占用进程。可显式选择其他端口：

```powershell
.\scripts\demo.ps1 start -Port 8123
```

## 2. 演示前检查

```powershell
.\scripts\demo.ps1 verify
```

通过意味着：迁移版本、manifest、合成宠物、Episode、Safety、Evidence、录制分析、基线及正在运行的服务能力契约均一致。界面应显示“合成演示数据”，运行时 AI 为关闭状态。

主演示建议顺序：

1. 查看 CanCan12 时间线与结构化观察；
2. 打开历史录制 AnalysisRun，说明 Claim、Evidence、Uncertainty 与人工复核；
3. 查看 7 日基线及来源；
4. 打开紧急呼吸 Episode，展示 Safety 优先于 AI 的边界。

## 3. 重置与停止

需要恢复固定数据时：

```powershell
.\scripts\demo.ps1 reset
```

`reset` 会先验证并停止本启动器创建的进程，只删除 `backend/.demo` 中白名单内的数据库、manifest、PID 和日志文件，然后重新迁移、seed、verify。重置后服务保持停止，再执行 `start`。

演示结束：

```powershell
.\scripts\demo.ps1 stop
```

重复 `start` 或 `stop` 是安全的。脚本使用 PID、Python 绝对路径、进程启动时间以及服务健康/能力合约确认身份；身份不匹配时拒绝停止进程，需要人工检查，不能删除 PID 后盲目结束进程。

## 4. 常见故障

- **端口已占用**：使用 `-Port 8123` 等未占用端口；不要结束来源不明的进程。
- **缺少 `backend/.venv`**：先按 README 完成后端依赖安装。
- **前端构建失败**：确认 Node.js/npm 与 `frontend/node_modules` 已准备好，再重新执行 `start`。
- **verify 失败**：执行 `reset` 重建合成数据；它不会修改默认开发数据库 `backend/relapaw.db`。
- **启动健康检查失败**：查看 `backend/.demo/server.stderr.log`；日志不应包含密钥或完整用户输入。
- **PID 不匹配**：保留现场状态，检查 `backend/.demo/server.pid.json` 与任务管理器，不让脚本终止未知进程。

## 5. 数据与安全边界

- 仅使用 `backend/.demo/relapaw-demo.db`；
- 不需要账号、邮箱、OTP、云服务或真实 API Key；
- 不发送模型网络请求；
- 不录入真实人物、主人或宠物资料；
- 服务只监听回环地址，不对局域网或公网开放；
- `frontend/dist`、数据库、manifest、日志和 PID 均为可重建产物，不提交 Git。
