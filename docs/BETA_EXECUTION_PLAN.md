# Relapaw invited Beta execution plan

Status: **ACTIVE**<br>
Last updated: 2026-10-21<br>
Authoritative branch: `post-competition`<br>
Milestone commit: `da28a074890ed1d78764dc27577143c9876a75af`

This file is the durable implementation plan for moving the local demo to an invited
Beta. A checked box is not evidence by itself: every completed row must link to code,
an automated test, a command result, or an explicitly external review item in
`BETA_ACCEPTANCE_MATRIX.md`.

## Invariants

- Observation, Owner Interpretation, model Claim, user confirmation, and long-term
  fact remain distinct records.
- Medical Safety precedes interpretation. A non-`NORMAL` result blocks every model
  call and keeps the veterinary escalation visible.
- AI output never mutates an Observation, Baseline, or long-term fact automatically.
- No real user or pet content is sent to an external model during implementation or
  verification.
- Cross-tenant resources return the same `404` shape as absent resources; anonymous
  business requests return `401`.
- Production configuration fails closed when identity, database, transport, secrets,
  or AI qualification requirements are not satisfied.

## Delivery stages

| Stage | State | Exit gate |
|---|---|---|
| Baseline and evidence system | COMPLETE | Constraints read; baseline commands and gaps recorded; matrix exists |
| P0-1 identity and tenancy | COMPLETE | Session lifecycle, CSRF, ownership chain, two-user IDOR matrix, multi-pet UI |
| P0-2 privacy and lifecycle | COMPLETE | Consent, inventory, export/delete/retention, immutable audit and Episode deletion |
| P0-3 AI and medical safety | COMPLETE | Unqualified AI absent/blocked; non-NORMAL pre-call block; versioned review structure |
| P0-4 production baseline | IN PROGRESS | PostgreSQL migrations, environment gates, observability, backup/restore, CI/rollback |
| P1 manual memory and baseline input | COMPLETE | AI-off manual path, controlled categories/units, raw input preserved |
| Final Beta readiness | BLOCKED BY EXTERNAL EVIDENCE | Local regression/build/report complete; approvals, PostgreSQL/restore/deploy and independent reviews remain |

## P0-1 decisions

1. Business authorization uses an internal `User.id`, never an email, provider token,
   request body owner ID, or client role.
2. Identity provider behavior is behind an `IdentityAdapter`. Local and test adapters
   are allowed; production must explicitly select a reviewed adapter and cannot fall
   back to a development identity.
3. Browser sessions use an opaque random token in an HttpOnly cookie. Only a keyed
   digest is stored. Logout, absolute expiry, idle expiry, account state changes, and
   token rotation are enforced server-side.
4. Cookie-authenticated writes require an allowed Origin and a session-bound CSRF
   token. CORS is an exact allow-list with credentials.
5. Pet is the tenant root. Every pet-derived resource is authorized through a query
   constrained by `Pet.owner_user_id`; nested cross-pet references are rejected.
6. Existing demo rows are never silently assigned to a real user. Migration handling
   is an explicit, revision-pinned operator command that assigns only `DISABLED`
   quarantine identities; it is never an application-startup action or real-account
   assignment.

## Working protocol per stage

For each stage: document decisions, implement, add focused tests, inspect the complete
diff independently, fix findings, run focused and full regression suites, then update
the matrix with exact evidence. External veterinary, legal, cloud, and operator review
items remain clearly marked and do not prevent implementation of their interfaces and
fail-closed gates.
