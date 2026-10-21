# Relapaw invited Beta acceptance matrix

Status: **ACTIVE / NOT READY**<br>
Last updated: 2026-10-20

Evidence states:

- `VERIFIED`: direct current code plus successful relevant verification.
- `INFERRED`: implementation evidence exists but the required end-to-end scope has not
  been exercised.
- `UNABLE TO VERIFY`: required external decision, reviewer, infrastructure, or runtime
  is unavailable.
- `NOT IMPLEMENTED`: current code contradicts or lacks the requirement.

| ID | Requirement | State | Current evidence / next proof |
|---|---|---|---|
| BASE-01 | Correct branch and starting HEAD | VERIFIED | Read-only check: `post-competition`, `5af287eb4f93e91ea4066c155a4a1c8a2b6783f1` |
| BASE-02 | Repository instructions applied | VERIFIED | No `AGENTS.md` at workspace root, `.agents`, or `E:\` on 2026-10-20 |
| BASE-03 | Backend regression | VERIFIED | Workspace venv with repository-local temp: `179 passed in 26.21s` on 2026-10-20 |
| BASE-04 | Frontend test/type/build | VERIFIED | `81 passed`; `tsc -b && vite build` succeeded on 2026-10-20 |
| AUTH-01 | Anonymous business APIs return 401 | VERIFIED | Route-policy test plus anonymous API tests; only health and auth challenge are public |
| AUTH-02 | Login, restoration, rotation, logout, expiry, revocation tested | VERIFIED | `test_login_restore_rotation_logout_expiry_and_revocation`; disabled users rejected |
| AUTH-03 | Session cookie, Origin and CSRF controls | VERIFIED | Opaque keyed hashes, one-use challenge, Origin/CSRF adversarial backend tests and frontend header test |
| AUTH-04 | Every Pet and derived resource is tenant-scoped | VERIFIED | Route-policy guard and authorized root queries cover all business routes; nested IDOR matrix passes |
| AUTH-05 | Two users cannot cross-access any resource type | VERIFIED | Pet/Episode/children/Plan/FollowUp/Escalation/Analysis/Claim/Memory/Baseline probes return uniform 404 without mutation |
| AUTH-06 | Multi-pet switch does not mix data | VERIFIED | Authorized pet list, keyed page remount, stored-ID revalidation, switch and dirty-draft confirmation tests |
| AUTH-07 | Production identity/email adapter selected and operational | UNABLE TO VERIFY | Adapter boundary and fail-closed production behavior exist; provider/domain/mail decision remains external |
| PRIV-01 | Versioned consent record and data inventory | VERIFIED | Version-matched adult affirmation, duplicate-race verification, active-session re-consent UI with preserved draft, and `PRIVACY_DATA_INVENTORY.md`; final legal approval remains external |
| PRIV-02 | Portable account export | VERIFIED | Tenant-scoped JSON covers live source/derived records and retained follow-up lifecycle after source redaction while excluding identity subject and session secrets |
| PRIV-03 | Account deletion and session revocation | VERIFIED | Confirmed request immediately revokes sessions; tested due purge removes only requesting account while retaining content-free audit |
| PRIV-04 | Retention policy is executable and tested | VERIFIED | `app.jobs.privacy_retention` applies account grace/audit expiry; due-account rows use skip-locked claims and actual delete counts; real multi-worker PostgreSQL remains OPS-01 |
| PRIV-05 | Episode deletion plus pseudonymous audit closure | VERIFIED | Content/derived redaction, inaccessible tombstone, pending follow-up cancellation, baseline invalidation and content-free audit are tested; audit rows are append-only by application convention with explicit retention purge, not claimed DB-immutable |
| SAFE-01 | Unqualified AI default-off in UI and API | VERIFIED | `QUALIFIED` must match provider/model/base URL and all contracts in an approved repository record; current registry is empty and raw-switch adversarial test makes zero adapter calls |
| SAFE-02 | Non-NORMAL blocks every model call before adapter invocation | VERIFIED | Missing Safety Check and both non-NORMAL states tested; safety block precedes feature/qualification gates and adapter call count remains zero |
| SAFE-03 | Versioned, veterinarian-reviewable knowledge structure | VERIFIED | `medical-safety/v1` executable manifest, enum-drift test, review register and production approval gate exist; actual veterinarian approval remains external |
| OPS-01 | PostgreSQL empty and representative upgrade migration | UNABLE TO VERIFY | Psycopg runtime and CI PostgreSQL round trip are configured; local Docker daemon/PostgreSQL unavailable, so real dialect evidence remains outstanding |
| OPS-02 | Environment, HTTPS, CORS and secret fail-closed gates | VERIFIED | Production rejects non-PostgreSQL, HTTP/local CORS, weak (<32) pepper, unidentified release, draft legal policy, unreviewed manifest and unmatched model qualification |
| OPS-03 | Redacted structured logs, health/readiness and monitoring | INFERRED | JSON events use route templates (unmatched paths are fixed), validated request IDs and DB/schema readiness are tested; external collection/alerts remain unavailable |
| OPS-04 | Backup/restore, deploy and rollback baseline | INFERRED | Non-root container, production-variable-required PostgreSQL Compose and runbook exist; migration remains an explicit one-off; real image/restore rehearsal requires infrastructure |
| OPS-05 | CI runs backend/frontend/type/build/migration/security gates | INFERRED | Workflow covers tests, production build, PostgreSQL migration round trip, dependency consistency and container build; hosted execution not run here |
| P1-01 | Manual long-term memory works with AI disabled | VERIFIED | `MANUAL` candidates use controlled categories, exact owner wording, no Claim/model, and the same explicit include/withdraw lifecycle; API and UI tests pass |
| P1-02 | Comparable behavior categories and units preserve raw input | VERIFIED | Optional controlled category/unit fields drive aggregation while original behavior label, unit and narrative remain unchanged; compatibility and comparison tests pass |
| FINAL-01 | Independent repository security, lineage, frontend/backend and migration review | VERIFIED | Three independent read-only code-review passes completed; all repository-solvable P0/P1 findings were fixed and covered before full regression; external infrastructure review remains separately UNABLE TO VERIFY |
| FINAL-02 | Full tests and production build pass | VERIFIED | Backend `179 passed`; frontend `81 passed`; TypeScript and Vite production build passed; no external calls |
| FINAL-03 | Beta readiness report and clean Git state recorded | VERIFIED | `BETA_READINESS_REPORT.md` records NOT READY decision, exact external blockers and current intentional uncommitted implementation state |

## External review items (not implementation excuses)

- Select and approve a production identity/email delivery adapter, deployment region,
  and operator account after interfaces and local verification exist.
- Legal review of final Terms, Privacy Notice, retention promises, and deletion timing.
- Licensed veterinarian approval of any medical knowledge content before activation.
- Named Beta owner, incident/support channel, backup operator, and invitation pause
  authority before sending invitations.
