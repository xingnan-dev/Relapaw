# P0-1 账号、身份与租户边界架构

状态：**实施中；供应商选择仍待外部批准**
版本：1.2
更新日期：2026-10-20
上游依据：[真实产品首发契约](LAUNCH_PRODUCT_SCOPE.md)、[真实产品首发差距审计](LAUNCH_GAP_AUDIT.md)  
本阶段性质：受邀 Beta 的实施基线；当前证据见 `BETA_ACCEPTANCE_MATRIX.md`

## 0. 2026-10-20 实施决定

此前“当前阶段不实施账号”的决定已被受邀 Beta 目标取代。当前仍没有获批的
产品域名、正式发信邮箱或身份供应商，因此实施遵循以下边界：

- 实现内部 User、可替换 `IdentityAdapter`、登录契约和服务端 Session；
- 当前阶段不购买域名，不配置正式邮件发送服务；
- 本地/测试使用一次性、短时且限制尝试次数的 invite challenge adapter；
- staging/production 禁止该本地 adapter，未配置经审核的外部 adapter 时登录 fail-closed；
- 演示数据必须是合成数据或产品负责人明确授权使用的数据；
- 无账号版本不得作为多人共享的真实数据服务公开上线；
- 任何真实邀请发出前，仍须选择并审核实际邮件/身份 adapter、域名和运营流程。

Supabase 仅保留为历史候选，不是当前实现依赖或默认决定。供应商选择须根据部署
地域、邮件能力、成本和隐私要求另行确认，不能改变内部 User、Session 和授权边界。

## 1. 目标与不可变边界

P0-1 的唯一目标是把当前共享数据空间改造成每位受邀用户的私有空间，并提供可验证的登录、退出、会话恢复、宠物切换和逐资源授权。

本阶段不得：

- 改变 Observation、Owner Interpretation、Safety、Evidence、Memory 或 Baseline 的既有业务语义；
- 顺带实现组织、家庭成员、兽医、管理员代看或共享宠物；
- 自建密码存储、密码重置、MFA 或邮件投递基础设施；
- 使用前端传入的 `user_id`、`owner_id` 或 JWT 自定义角色作为最终授权依据；
- 因加入账号而开放 `NOT_QUALIFIED` 的 AI Understanding；
- 把当前开发数据库里的宠物或记录自动归给第一个真实注册用户。

## 2. 冻结的架构决定

### 2.1 身份提供商

实现使用可替换 **Identity Adapter**，产品登录契约只开放**受邀邮箱 challenge**：

- 生产 adapter 必须验证邀请状态；无邀请的邮箱不能自行注册；
- 用户输入邮箱并收到一次性验证码；首发不使用密码，也不开放社交登录；
- 外部 adapter 负责邮箱验证、一次性 challenge、身份主体和安全通知；
- Relapaw 不保存密码、OTP、刷新令牌明文或服务端 Secret 到前端；
- staging 与 production 使用不同的 Supabase 项目、签名密钥、邮件配置和用户池。

选择理由：首批 Beta 人数小且需要控制邀请；适配器边界避免在域名、地域、成本和
隐私要求确认前锁定供应商。当前本地 adapter 不发送邮件、不可用于 staging/production，
只用于验证完整会话和授权链。

如果未来因地域、合规或可用性更换提供商，只允许替换 Identity Adapter。Relapaw 内部 `users.id`、服务端会话、授权规则和业务外键不得依赖 Supabase UUID 的数据库类型或 SDK 行为。

### 2.2 浏览器会话

采用 **Backend-for-Frontend 服务端会话**，不让浏览器 JavaScript 持有长期 Provider token：

```text
浏览器请求邮箱 OTP
→ FastAPI 调用 Identity Adapter / Supabase Auth
→ 用户提交 OTP
→ FastAPI 向 Provider 验证 OTP，并验证返回身份
→ FastAPI 按 (provider, subject) 建立或读取本地 User
→ FastAPI 创建随机不透明 Session
→ 浏览器只收到 HttpOnly Cookie
→ 后续请求由 FastAPI 读取 Session 并注入 CurrentUser
```

Cookie 冻结配置：

- 名称：`__Host-relapaw_session`；
- `Secure=true`（生产和 staging）；
- `HttpOnly=true`；
- `SameSite=Lax`；
- `Path=/`；
- 不设置 `Domain`；
- 生产最大有效期 30 天，闲置 7 天过期；
- 每次成功登录轮换 Session ID，退出、删号开始、账号禁用时立即撤销；
- 数据库只保存 Session token 的密码学哈希，不保存可直接重放的原 token。

本地开发允许单独的非 Secure cookie 配置，但配置名必须显式包含 `DEV`，不得被生产默认值继承。

### 2.3 JWT 与 Provider 验证

Identity Adapter 必须：

- 使用 Supabase 非对称签名密钥；
- 从固定的 HTTPS JWKS 地址获取公钥并受控缓存；
- 固定允许的算法，不接受 token 自报算法扩展；
- 校验签名、`iss`、`aud`、`exp`、`nbf`（如存在）、`sub` 和 OTP 预期用途；
- 拒绝未知 `kid`，刷新一次 JWKS 后仍未知则失败；
- Provider 不可用时不创建本地 Session；
- 不把未验证的 email、role 或 metadata 用于授权。

后端业务授权只使用本地 Session 对应的 `users.id`。Provider 的 `sub` 只用于定位本地身份映射。

### 2.4 CSRF、CORS 与请求边界

因为浏览器使用 Cookie，会同时启用：

- 所有 `POST/PUT/PATCH/DELETE` 校验 `Origin`，只允许当前正式 Web Origin；
- 使用 Session 绑定的 CSRF token；前端从非 HttpOnly 的 CSRF bootstrap 响应读取并放入 `X-CSRF-Token`，服务端做恒定时间比较；
- 登录请求、OTP 申请与验证也执行 Origin 校验、速率限制和通用错误文案；
- CORS 使用精确白名单并允许凭据，不允许 `*`；
- `GET/HEAD/OPTIONS` 不产生业务写入；
- 前端 `fetch` 统一使用 `credentials: "include"`；
- 401 表示未登录或会话过期，403 仅用于已登录但违反非资源型策略；对不属于当前用户的资源统一返回 404，减少 ID 枚举。

### 2.5 授权模型

候选外部 Beta 只有一个业务角色：`OWNER`。角色不进入各资源表，也不从请求体传入。

授权规则只有一条根原则：

> 当前用户只能访问 `pets.owner_user_id == current_user.id` 的宠物，以及能够沿外键链回溯到这些宠物的资源。

首发不引入共享表、ACL、organization_id 或多角色策略。未来若需要家庭共享，必须另行设计，不能把 `owner_user_id` 改造成逗号列表或信任前端角色。

## 3. 数据模型

### 3.1 `users`

| 字段 | 类型 | 规则 |
|---|---|---|
| `id` | UUID | Relapaw 内部主键，服务端生成 |
| `status` | enum | `ACTIVE`、`PENDING_DELETION`、`DISABLED` |
| `created_at` | timestamptz | UTC，不可变 |
| `updated_at` | timestamptz | UTC |
| `last_login_at` | timestamptz nullable | 成功建立会话时更新 |
| `deletion_requested_at` | timestamptz nullable | P0-2 使用 |

不在 `users` 表保存密码、OTP、Provider refresh token 或宠物数据。首发不持久化 email；当前验证邮箱从 Provider 身份读取，仅在会话响应中显示掩码版本。P0-2 如因通知或导出需要持久化邮箱，必须先更新数据清单和隐私说明。

### 3.2 `user_identities`

| 字段 | 类型 | 规则 |
|---|---|---|
| `id` | UUID | 内部主键 |
| `user_id` | UUID FK | → `users.id`，删除账号时级联 |
| `provider` | text | 首发固定 `supabase` |
| `subject` | text | Provider 已验证的 `sub` |
| `created_at` | timestamptz | UTC |
| `last_verified_at` | timestamptz | 最近成功验证 |

唯一约束：`(provider, subject)`。同一身份不能映射到两个用户。首发一个 User 只允许一个 Identity；表结构保留未来安全合并身份的可能，但不实现合并流程。

### 3.3 `user_sessions`

| 字段 | 类型 | 规则 |
|---|---|---|
| `id` | UUID | 服务端主键，不放入 Cookie |
| `user_id` | UUID FK | → `users.id`，级联删除 |
| `token_hash` | bytes/text | 唯一；使用专用 pepper 的安全哈希 |
| `csrf_token_hash` | bytes/text | 与 Session 绑定 |
| `created_at` | timestamptz | UTC |
| `last_seen_at` | timestamptz | 节流更新，避免每请求写库 |
| `expires_at` | timestamptz | 绝对到期时间 |
| `revoked_at` | timestamptz nullable | 非空即拒绝 |
| `user_agent_summary` | text nullable | 截断和最小化，不保存完整指纹 |

只允许保存 Session token 的哈希。日志不得记录 Cookie、CSRF token、OTP 或 Authorization Header。

### 3.4 `terms_acceptances`

该表由 P0-1 建模、P0-2 接入正式文案：

| 字段 | 类型 | 规则 |
|---|---|---|
| `id` | UUID | 主键 |
| `user_id` | UUID FK | → `users.id` |
| `terms_version` | text | 不可空 |
| `privacy_version` | text | 不可空 |
| `accepted_at` | timestamptz | UTC |
| `source` | text | `ONBOARDING` 或未来的版本更新入口 |

唯一约束：`(user_id, terms_version, privacy_version)`。不保存 IP 全值；如发布审核要求保留网络证据，须单独做最小化和期限设计。

### 3.5 `pets` 归属

在 `pets` 增加：

```text
owner_user_id UUID NOT NULL REFERENCES users(id)
```

索引至少包含 `(owner_user_id, created_at, id)`。`owner_user_id` 创建后不可通过普通 Pet update 修改；转移宠物不属于首发。

其他业务表不重复增加 `user_id`，而是沿既有外键链回溯 Pet，避免同一记录出现互相冲突的租户字段。只有确实没有 Pet 根的账号级对象（Session、条款、未来导出任务）直接关联 User。

## 4. 资源授权链

| 资源/API 根 | 所有权路径 | 服务端查询要求 |
|---|---|---|
| Pet | `pet.owner_user_id` | 所有 Pet 查询包含 `owner_user_id=current_user.id` |
| PetBaseline | `pet_baseline.pet_id → pet.owner_user_id` | join/exists 校验 Pet 所属 |
| Episode | `episode.pet_id → pet.owner_user_id` | 不先裸查 Episode 再做可观察错误分支 |
| Observation / OwnerInterpretation / SafetyCheck / EvidenceReference | `…episode_id → episode.pet_id → pet.owner_user_id` | 从授权 Episode 加载或 join 校验 |
| VeterinaryEscalation / FollowUp | `…episode_id → episode.pet_id → pet.owner_user_id` | source 与 result Episode 都必须属于同一 Pet |
| ObservationPlan | `plan.pet_id → pet.owner_user_id` | 关联 Episode 时再验证同一 Pet |
| AnalysisRun / Claim / Confirmation / Uncertainty | `…episode_id → episode.pet_id → pet.owner_user_id` | 即使 AI 关闭，读取历史也必须授权 |
| MemoryCandidate / MemoryDecision | `candidate.pet_id → pet.owner_user_id`，并校验 Claim 来源同一 Pet | 不信任 candidate/claim ID 单独存在 |
| BaselineSnapshot / BaselineEvidence | `snapshot.pet_id → pet.owner_user_id` | evidence 下钻必须继承 Snapshot 授权 |

实现时废弃当前只接收 `db, id` 的通用 `require_pet` / `require_episode` 用法，替换为显式接收 `current_user` 的授权查询。服务层不得绕过授权查询直接通过客户端 ID 读取业务资源。

后台迁移、备份和内部评估属于非用户执行上下文，必须使用独立、显式命名的系统入口；禁止通过伪造一个普通用户跳过授权。

## 5. API 与前端流程

### 5.1 新增会话 API

```text
POST /api/v1/auth/otp/request
POST /api/v1/auth/otp/verify
GET  /api/v1/auth/session
POST /api/v1/auth/logout
GET  /api/v1/auth/csrf
```

规则：

- OTP request 无论邮箱是否受邀都返回同一成功形状，避免枚举；
- request 与 verify 按 IP 摘要和邮箱摘要限速，具体阈值进入实施配置；
- verify 成功才创建本地 User/Identity/Session；
- `GET /auth/session` 只返回内部 User ID、状态、掩码邮箱、条款接受状态和能力开关，不返回 Provider token；
- logout 幂等：无论 Session 是否存在都清 Cookie，并在存在时撤销服务端 Session；
- 所有非 auth 健康检查 API 默认要求 CurrentUser；公开端点白名单只包括 `/health`、OTP request/verify 和必要静态配置。

### 5.2 首次使用

```text
打开应用
→ GET /auth/session
→ 401：显示登录页
→ 输入受邀邮箱，申请 OTP
→ 输入 OTP 并验证
→ Session 已建立但条款未接受：只允许查看并接受当前条款
→ 接受后进入 Onboarding
→ 创建宠物或进入真实空状态
```

Onboarding 完成状态从仅存 localStorage 改为账号级服务端状态；localStorage 只能作为非权威 UI 优化，不能决定是否已接受条款。

### 5.3 宠物切换

- Header 提供当前宠物选择器；无宠物时显示“添加宠物”；
- 选择器只展示当前用户的宠物；
- 当前宠物 ID 可保存在 localStorage，但恢复时必须通过授权 API 重新验证；
- 切换后 Today、Record、Timeline、Us 清除前一只宠物的页面状态和请求结果；
- 进行中的未保存表单切换宠物前必须确认，不能把草稿提交给新宠物；
- API 永远不信任 localStorage，所有 Pet ID 都重新检查所有权。

### 5.4 会话过期

- 读取请求收到 401：清除本地身份状态，跳转登录，并保存安全的返回位置；
- 写入请求收到 401：保留当前表单内存状态，提示重新登录；登录恢复后由用户主动重试，不自动重复写入；
- 403：显示策略禁止，不循环刷新；
- 404：对资源不存在和资源不属于当前用户使用相同用户文案；
- 不把未保存的宠物健康或行为正文放入 URL、日志或通用 telemetry。

## 6. 现有数据迁移策略

### 6.1 环境决定

- 当前 SQLite `relapaw.db` 及现有记录一律认定为开发/演示数据；
- production PostgreSQL 从空业务库开始，不导入当前开发记录；
- staging 使用合成数据，不复制 production 或真实 Beta 正文；
- 不尝试从宠物名称、OwnerProfile 或历史输入猜测真实所有者。

### 6.2 Alembic 两阶段迁移

为保证迁移对非空开发库可执行：

**Migration A：引入身份边界**

1. 创建 `users`、`user_identities`、`user_sessions`、`terms_acceptances`；
2. 为 `pets.owner_user_id` 增加 nullable 字段和索引；
3. 不自动把无归属 Pet 暴露给任何真实用户。

**显式数据处理步骤**

- production preflight 必须断言无归属 Pet 数量为 0；否则停止部署；
- 本地/演示环境通过独立 seed/migration helper 创建 `DISABLED` 的 legacy demo user，并明确把旧 Pet 归档到该用户；
- helper 输出处理数量，需要操作者显式指定 `--allow-legacy-demo-data`；不得在应用启动时自动执行；
- legacy demo user 不能建立 Session，也不会出现在邀请列表。

**Migration B：收紧约束**

1. 验证所有 Pet 均有合法 owner；
2. 将 `owner_user_id` 改为 NOT NULL；
3. 建立外键和最终索引；
4. fresh migration 与代表性非空开发库升级均必须通过。

该设计避免“第一个登录的人继承所有旧数据”，也避免生产迁移静默删除数据。

## 7. 删除与停用边界

P0-1 只实现账号状态与 Session 撤销，不实现完整账号删除；P0-2 接管删除生命周期。

- `ACTIVE`：正常访问；
- `PENDING_DELETION`：立即撤销所有 Session，拒绝普通登录，只允许受控的取消删除流程；
- `DISABLED`：运营安全停用，拒绝登录；不得删除或改归属业务记录；
- 真正 hard delete 必须在 P0-2 确认导出、审计、备份保留和通知规则后实现。

任何状态非 `ACTIVE` 的 User 都不能建立或继续使用 Session。

## 8. 威胁模型与控制

| 威胁 | 控制 |
|---|---|
| 修改 URL/请求体 ID 读取他人数据 | 每个资源沿 Pet→User 授权；不属于当前用户统一 404 |
| 前端伪造 `owner_user_id` | create 时只使用 CurrentUser；schema 禁止该字段；update 不支持转移 |
| Session token 被数据库泄漏后重放 | 数据库仅保存哈希；原 token 只在 HttpOnly Cookie；Secret pepper 独立管理 |
| XSS 读取会话 | HttpOnly；不把 Provider token 放 localStorage；继续执行 CSP/依赖审计 |
| CSRF 写入 | SameSite、Origin 校验、Session 绑定 CSRF token 三层控制 |
| OTP/邮箱枚举与爆破 | 通用响应、邀请名单、速率限制、短时 OTP、Provider 风控和告警 |
| JWT 算法混淆或伪造 | 固定算法/issuer/audience；非对称 JWKS；成熟库验证；拒绝未知 kid |
| 退出后 Cookie 仍可用 | 服务端 Session 撤销 + 清 Cookie；每次请求检查 revoked/expiry/User status |
| 切换宠物导致旧响应串入新页面 | 请求取消或 generation guard；状态以 petId 分区；切换后清空旧页面状态 |
| 日志泄露健康/行为正文 | 日志只记 request ID、user ID 的不可逆摘要、资源类型、状态码与延迟 |
| 系统任务绕过权限被普通路由调用 | 用户与系统执行上下文分离；系统入口不接受浏览器 Cookie，单独鉴权和审计 |

## 9. 验收条件

### 9.1 身份与会话

- 未登录用户除公开白名单外访问任何 `/api/v1` 业务接口均为 401；
- 未受邀邮箱不能创建账号，响应不泄露其是否存在；
- 受邀用户可通过 OTP 登录、刷新页面恢复 Session、主动退出；
- OTP 错误、过期、重复使用、Provider 超时和 JWKS 失败均不创建本地 Session；
- 登录成功轮换 Session；旧 Session token 不再可用；
- 绝对过期、闲置过期、撤销、User 禁用和待删除都会拒绝 Session；
- Cookie 在 staging/production 具有冻结属性，响应和日志不包含 token；
- CSRF 缺失、错误、跨 Origin 请求不能执行写入。

### 9.2 双用户授权矩阵

准备 Alice、Bob 各两只 Pet，以及覆盖全部资源类型的数据。对每个资源执行：

```text
Alice 读取/修改/删除 Alice 的资源 → 按业务规则成功
Alice 使用 Bob 的资源 ID → 404，且 Bob 数据不变化
Bob 使用 Alice 的资源 ID → 404，且 Alice 数据不变化
未登录使用任意资源 ID → 401
```

必须覆盖：Pet、PetBaseline、Episode、Observation、OwnerInterpretation、SafetyCheck、EvidenceReference、VeterinaryEscalation、FollowUp、ObservationPlan、AnalysisRun、Claim、Confirmation、MemoryCandidate、MemoryDecision、BaselineSnapshot 和 BaselineEvidence。

还必须验证：

- 不能把 Alice 的 Episode 关联到 Bob 的 Plan；
- 不能用 Bob 的 Claim 创建 Alice 的 MemoryCandidate；
- 不能从 Alice 的 Snapshot 下钻 Bob 的 Evidence；
- 不能通过分页总数、错误差异或 timing 明显判断另一个 ID 是否存在；
- 创建 Pet 时忽略/拒绝请求体中的 owner 字段并强制使用 CurrentUser。

### 9.3 多宠与前端状态

- 同一用户可创建并切换至少两只 Pet；
- Today、Record、Timeline、Us 只显示当前 Pet 数据；
- localStorage 中放入其他用户的 Pet ID 后，恢复流程清除该值并回到本用户可用状态；
- 切换 Pet 时未保存表单需要确认，不会提交到错误 Pet；
- 慢响应乱序返回时，前一只 Pet 的数据不会覆盖当前页面；
- 401 后表单输入保留，重新登录后由用户主动重试。

### 9.4 迁移与环境

- 空 PostgreSQL 可从 base 升级到 head；
- 含代表性旧数据的开发库可经过显式 legacy helper 再升级；
- 非空 production preflight 会阻断，而不是自动认领旧 Pet；
- staging 与 production 的用户池、Cookie、数据库、Secret 和邮件配置完全隔离；
- 回滚/前滚演练不会产生无 owner 的可访问 Pet；
- 现有领域测试全部通过，新增 auth/authorization 测试进入默认测试套件。

## 10. 实施切片

未来重新批准 P0-1 进入代码阶段后，按以下顺序实施，每片均需测试、Review、回归和人工验收：

1. **Identity foundation**：配置、Identity Adapter、User/Identity/Session 模型和 Migration A；
2. **Server session**：OTP API、Cookie、CSRF、CurrentUser 与会话状态；
3. **Ownership enforcement**：Pet owner、全部资源授权查询与双用户测试；
4. **Frontend auth shell**：登录、OTP、退出、过期恢复与条款门禁占位；
5. **Pet switching**：选择器、状态隔离、未保存表单保护；
6. **Migration closeout**：legacy helper、Migration B、PostgreSQL fresh/upgrade 验证；
7. **Security Review**：IDOR、CSRF、Session、日志脱敏、依赖和配置审计；
8. **Full regression**：后端、前端、build、浏览器、响应式、无障碍与人工验收。

未经用户明确授权，不创建实施 commit；未经独立授权，不 push。

## 11. 外部依据

- [Supabase Auth 官方文档](https://supabase.com/docs/guides/auth)：支持邮件 OTP、邀请与 JWT 会话。
- [Supabase JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys)：非对称签名、JWKS 公钥发现和密钥轮换边界。
- [Supabase JWT 验证](https://supabase.com/docs/guides/auth/jwts)：`iss`、`exp`、`sub` 等声明及 JWKS 验证方式。
- [MDN Secure Cookie 指南](https://developer.mozilla.org/en-US/docs/Web/Security/Practical_implementation_guides/Cookies)：`Secure`、`HttpOnly`、`SameSite` 与 Cookie 前缀约束。

外部资料用于确认身份和浏览器安全机制；Relapaw 的租户模型、会话存储、数据迁移和产品边界由本文件冻结。

## 12. 下一步

当前不继续该方案的实现前 Review。触发条件是：产品负责人决定让多名外部用户共用同一个线上系统。

触发后首先重新确认身份提供商与登录方式，再做**实现前安全与可实施性 Review**，重点验证：

- Supabase OTP 的服务端交换与 Session 建立细节；
- Python JWT/JWKS 库选择和失败行为；
- CSRF bootstrap 契约；
- 全部资源授权链是否遗漏；
- SQLite 开发迁移与 PostgreSQL 生产迁移的兼容性；
- P0-2 删除生命周期是否会推翻 User/Pet 外键决定。

Review 问题修复并经人工确认后，才进入 P0-1 代码实现。
