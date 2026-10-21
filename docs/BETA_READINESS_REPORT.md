# Relapaw invited Beta readiness report

Date: 2026-10-20<br>
Branch: `post-competition`<br>
Starting/current committed HEAD: `5af287eb4f93e91ea4066c155a4a1c8a2b6783f1`<br>
Decision: **NOT READY TO INVITE REAL USERS**

## Implemented and locally verified

- Internal users, invited identity boundary, opaque server sessions, CSRF/Origin
  enforcement, versioned consent and complete Pet-root tenant authorization
- Multi-pet UI isolation, session-expiry recovery, and version-change consent recovery
  without losing mounted drafts
- Tenant-scoped portable export, account deletion grace/revocation/purge, Episode
  redaction, concurrency-safe retention claim and content-free pseudonymous audit trail
- Default-off AI with an exact repository-bound qualification record, durable
  request-id reservation, zero-call non-NORMAL safety block, grounded/versioned
  analysis contracts and veterinarian-reviewable safety manifest
- PostgreSQL-only production configuration gate, exact HTTPS CORS, release identity,
  structured content-free request logs, request IDs and database/schema readiness
- Container/Compose/CI definitions plus backup, restore and rollback procedures
- AI-independent manual long-term memory and controlled comparison labels/units while
  preserving original owner wording and source values

## Current verification evidence

- Backend: `179 passed in 26.21s` using the workspace virtual environment and a
  repository-local pytest temp directory
- Frontend: `81 passed`
- TypeScript plus Vite production build: passed
- Focused migration chain: empty and representative legacy SQLite upgrade to
  `20261020_0014` passed, including multiple legal legacy owner-profile rows
- Compose configuration: parsed successfully with validation-only required variables;
  omission was separately verified to fail closed instead of silently selecting development
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
6. Build/scan the container in CI, deploy behind HTTPS with an explicit trusted proxy,
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
