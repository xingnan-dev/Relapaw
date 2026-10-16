# 比赛提交就绪检查表

更新时间：2026-10-16

用途：统一判断“已有证据”“待制作材料”和“阻断提交的门禁”。本文件不代表项目已经进入 Release Candidate，也不替代官方规则。

## 一、当前可直接复现的证据

| 证据 | 位置或命令 | 当前结果 |
|---|---|---|
| AI Coding 工具与用途 | `01_AI_TOOLS_AND_PURPOSES.md`、`08_AI_CODING_SUBMISSION_NARRATIVE.md` | 已形成独立说明 |
| 完整开发流程 | `02_AI_CODING_WORKFLOW.md` | 已覆盖需求至交付准备 |
| 人机交互与人工否决 | `03_HUMAN_AI_INTERACTION_CASES.md` | 8 个真实案例 |
| AI 原生方法论 | `04_AI_NATIVE_METHODOLOGY.md` | 已形成独立方法论 |
| 第三方代码与素材 | `05_THIRD_PARTY_ATTRIBUTIONS.md` | 当前工作区已登记，RC 前仍需最终许可证清单 |
| Git 与功能证据 | `06_COMMIT_AND_EVIDENCE_MAP.md` | 已映射既有里程碑；当前工作区尚无获授权 commit |
| 比赛要求对应关系 | `07_COMPETITION_REQUIREMENTS_MATRIX.md` | 已覆盖用户提供截图中的已知要求 |
| 前端自动回归 | `cd frontend; npm test -- --run` | 69 项通过 |
| 前端正式构建 | `cd frontend; npm run build` | 通过 |
| 后端自动回归 | `cd backend; .\.venv\Scripts\python.exe -m pytest` | 114 项通过 |
| 工作区差异检查 | `git diff --check` | 通过 |

## 二、建议演示证据序列

1. 人工提出“多个入口重复、卡片虚假可点击”的真实问题；
2. Codex 审计页面回调、API 与数据能力，先做结构减法；
3. 展示记录中 Observation 与 Interpretation 的分离；
4. 展示 Safety 非 NORMAL 时 Provider 不调用；
5. 展示 Claim、Evidence、Uncertainty 与人工确认/拒绝；
6. 展示一次 AI 生成结果被用户拒绝并驱动 Prompt/契约修复；
7. 展示首次引导视觉版本被连续否决，最终由截图、录屏和自动测试共同验收；
8. 对应展示测试输出、代码差异、Git commit 和第三方来源。

## 三、提交前必须补齐

- [ ] 取得官方完整规则并核对截止时间、提交格式、时长、文件大小、版权和 AI 使用披露格式；
- [x] 完成当前 UI/UX 阶段深层页面、响应式、键盘、触控和视觉人工验收；
- [ ] 按主指引完成生产部署、HTTPS、PostgreSQL、Secret、监控、备份与恢复演练；
- [ ] 取得用户对当前工作区 commit 的明确授权，并把 hash 补入证据地图；
- [ ] 取得单独 push 授权并核对远端版本；
- [ ] 生成最终依赖许可证清单，核对所有图片、字体、图标和数据来源；
- [ ] 建立脱敏的截图/录屏目录，确保不含 API key、个人路径、私人窗口和真实敏感数据；
- [ ] 制作独立 AI Coding 章节，不只把流程嵌入产品说明书；
- [ ] 使用同一 release commit 录制产品 Demo、AI Coding 流程与测试证据；
- [ ] 完成 Release Candidate 总验收并创建经授权的比赛版本标签。

## 四、当前明确不能声称

- 尚不能声称已取得或完整核对官方规则；
- 尚不能声称已完成生产部署、监控或恢复演练；
- 尚不能声称当前未提交 UI/UX 工作已有 Git commit 或远端证据；
- 尚不能声称当前 Qwen/Prompt 组合已通过资格评估；真实结论仍是 `NOT_QUALIFIED`；
- 尚不能把赛后 Phase 4–6 描述为已实现；
- 尚不能把用户参考图片描述为产品素材或拥有其再发布权。

## 五、当前阶段结论

项目已经具备可复现的工程与 AI Coding 过程证据，完整 UI/UX 与品牌精修已通过人工验收，但当前工作区仍未取得 commit/push 授权。下一阶段按主指引进入生产部署与可观测性，再制作最终比赛演示材料和 Release Candidate。
