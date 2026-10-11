# Scope and Acceptance

## 自动验收

- [x] Token 覆盖颜色、排版、间距、圆角、阴影、布局、焦点和动效。
- [x] Button 支持 primary/secondary/quiet/danger 与 busy/disabled。
- [x] Surface 支持 default/subtle/emphasis。
- [x] StatusNotice 支持 neutral/info/success/warning/danger，且角色可明确选择。
- [x] Understanding 的 provenance、blocked、error、completed 和决定保存失败迁移到统一 primitive。
- [x] 键盘 `:focus-visible` 清晰可见；触控控件最小高度至少 44px。
- [x] 360px 窄屏使用单列 notice/action、较小页面边距和可换行操作区；桌面视口保持 720px 可读行长。
- [x] reduced-motion 保持可用。
- [x] frontend Vitest、production build、backend pytest、Alembic current/check 与 `git diff --check` 通过。

## 人工验收

- [x] Today、Understand、Timeline、Episode、Us 的基础组件在可用性和状态层级上保持一致。
- [x] loading、empty、error、blocked、stale 和 completed 不只靠颜色区分。
- [x] 键盘 Tab 可见焦点，不被底部导航遮挡。
- [x] 窄屏、当前应用壳与宽桌面视口无明显横向溢出或正文遮挡。
