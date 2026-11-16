# Relapaw invited Beta readiness report

Date: 2026-10-21<br>
Branch: `post-competition`<br>
Milestone/current committed HEAD: `da28a074890ed1d78764dc27577143c9876a75af`<br>
Working state: post-milestone fixes are intentionally uncommitted<br>
Decision: **NOT READY TO INVITE REAL USERS**

## Implemented and locally verified

- Internal users, invited identity boundary, opaque server sessions, CSRF/Origin
  enforcement, versioned consent and complete Pet-root tenant authorization
- Multi-pet UI isolation, session-expiry recovery, and version-change consent recovery
  without losing mounted drafts, including reauthentication followed by renewed
  consent and recoverable CSRF-bootstrap failure
- Tenant-scoped portable export, account deletion grace/revocation/purge, Episode
  redaction, concurrency-safe retention claim and content-free pseudonymous audit trail
- Default-off AI with an exact repository-bound qualification record, durable
  request-id reservation, zero-call non-NORMAL safety block, grounded/versioned
  analysis contracts and veterinarian-reviewable safety manifest
- PostgreSQL-only production configuration gate, exact HTTPS CORS, release identity,
  structured content-free request logs, request IDs and database/schema readiness
- Container/Compose/CI definitions plus backup, restore and rollback procedures
- AI-independent manual long-term memory and controlled comparison labels/units while
  preserving original owner wording and source values; unconverted unit mismatches
  are rejected before persistence
- Direct Python and frontend dependencies are exact-version pinned, and GitHub Actions
  use commit SHAs; Node, Python and PostgreSQL base images use repository-pinned
  manifest digests. Vite was upgraded to 8.3.4 after a high-severity advisory and the
  resulting dependency audit is clean. Hosted pull/build/scan remains external evidence.

## Current verification evidence

- Backend: `185 passed in 15.94s` using the workspace virtual environment and a
  repository-local pytest temp directory
- Frontend: `87 passed`
- TypeScript plus Vite 8.3.4 production build: passed
- Focused migration chain: empty and representative legacy SQLite upgrade to
  `20261020_0014` passed, including multiple legal legacy owner-profile rows
- Compose configuration: parsed successfully with validation-only required variables;
  runtime mode is fixed to production and the PostgreSQL DSN must be supplied already
  URL-encoded instead of interpolating a raw password
- Docker/WSL host access: **VERIFIED** outside the Codex sandbox. Docker Desktop
  4.86.0 / Engine 29.7.2, Compose 5.3.1 and the `desktop-linux` WSL2 context responded;
  all nine pre-existing containers were stopped and were not changed
- Container definition: **VERIFIED statically**. Digest-pinned build/runtime bases,
  UID 10001 non-root runtime, port 8000, image- and Compose-level `/ready` health
  checks, and build-context exclusions for environment files, databases, logs,
  caches and generated frontend assets are present
- Dependency checks: the final `pip check` reported no broken requirements. An earlier
  successful `npm audit --omit=dev --audit-level=high` reported zero vulnerabilities;
  the final rerun was **UNABLE TO VERIFY** because the npm registry audit endpoint was
  unreachable, and is not counted as a passing run
- Local container build, layer/image inspection, PostgreSQL migration and isolated
  smoke test: **UNABLE TO VERIFY**. Two approved host-level build attempts reached the
  daemon but timed out obtaining anonymous Docker Hub tokens for the pinned Node and
  Python base images. Those bases and the pinned PostgreSQL 17 image were not present
  locally, so no audit image, container, network or volume was created. No unpinned or
  unrelated local image was substituted
- `git diff --check`: no whitespace errors; only expected LF/CRLF warnings
- No external model request, deployment, commit or push was performed

## Blocking external evidence

1. Select, integrate and exercise a production identity/email delivery provider.
2. Obtain legal approval for Terms, Privacy Notice, retention/deletion timing and
   backup rotation; replace draft versions.
3. Obtain licensed veterinarian approval for the exact medical safety manifest.
4. Keep AI disabled, or qualify the exact provider/model/contracts and record its
   immutable qualification ID.
5. Run empty and representative migrations against the selected PostgreSQL service.
6. Restore Docker Hub/approved registry access, build and scan the pinned container,
   then deploy
   behind HTTPS with an explicit trusted proxy,
   and verify Secure/HttpOnly/SameSite cookies end-to-end.
7. Configure monitoring/alerts, name the Beta owner and incident/support channel, and
   prove the invitation-pause procedure.
8. Perform and record an encrypted backup plus isolated restore rehearsal, including
   privacy-retention replay before restored service is opened.
9. Obtain external security/privacy review if required by the release owner. Three
   independent repository code-review passes were completed locally; they do not
   substitute for PostgreSQL or organizational review evidence.

Invitations must remain paused until every blocker has an owner, dated evidence and a
passing entry in `BETA_ACCEPTANCE_MATRIX.md`.
