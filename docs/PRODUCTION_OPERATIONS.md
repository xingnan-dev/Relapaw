# Relapaw invited Beta production operations baseline

Status: implementation-ready; requires named operator, infrastructure and rehearsal

## Release gate

1. CI must pass backend tests, frontend tests/build, PostgreSQL migration round trip,
   dependency checks and container build.
2. Use an immutable image tag and set `RELAPAW_DEPLOYMENT_VERSION` to the same release.
3. Supply PostgreSQL, exact HTTPS CORS origin, a 32+ character rotated session pepper,
   approved legal versions and a veterinarian-approved in-repository medical manifest.
   Keep AI off unless the selected qualification ID exactly binds provider, model,
   base URL and prompt/input/output contracts in `model_qualification.py`.
   Provide `RELAPAW_DATABASE_URL` through the deployment secret manager as an encoded
   DSN. Validate Compose only with `docker compose config --quiet`; never print or
   archive the rendered configuration because it contains the database credential.
4. Run migrations as a one-off job before shifting traffic. For a fresh empty Beta
   database, run `alembic upgrade head`. For an explicitly approved legacy demo
   database, first take and verify a backup plus row counts, upgrade only to
   `20261020_0009`, run
   `python -m app.demo.assign_legacy_owner --allow-legacy-demo-data`, verify every
   legacy row is assigned only to a `DISABLED` quarantine user, and then upgrade to
   `head`. Stop on any unexpected count or non-disabled assignment. Never run this
   helper automatically or use it to assign data to a real account.
5. Require `/health` for process liveness and `/ready` for database connectivity plus
   exact schema revision. Never route Beta traffic while readiness is 503.
6. Terminate TLS at a controlled ingress. If forwarded headers are required, configure
   Uvicorn with the ingress's exact trusted proxy addresses; never trust `*`.

## Backup and restore

- Take encrypted PostgreSQL custom-format backups with `pg_dump --format=custom`.
- Store them in a separate access-controlled account/region with automatic expiry;
  do not place backups in the repository or application container.
- Default operational proposal: daily backups, 14-day rotation. This duration remains
  pending legal/operator approval and must match the Privacy Notice.
- At least before invitations and after every schema change, restore the latest backup
  into an isolated empty PostgreSQL instance using `pg_restore --clean --if-exists`.
- After restore: run `alembic upgrade head`, run `python -m app.jobs.privacy_retention`,
  verify `/ready`, tenant isolation smoke tests, row counts and a sampled export.
- A backup is not considered valid until an isolated restore rehearsal succeeds and
  its release, checksum, duration and operator are recorded.

## Rollback

Application rollback uses the previous immutable image. Database rollback is decided
per migration: prefer a forward fix once writes have occurred. Before a destructive
schema downgrade, pause invitations/writes, take a verified backup, inspect the exact
Alembic downgrade and obtain operator approval. Never run `downgrade base` against a
Beta database; the CI round trip is only for an empty disposable database.

## Monitoring and incident minimum

- Collect JSON request events by request ID, route template, status, duration,
  environment and deployment version. Request bodies, query strings, cookies,
  authorization data, email, resource IDs, unmatched paths and pet content must never
  enter logs.
- Alert on readiness failure, sustained 5xx rate, latency, database exhaustion,
  retention-job failure and identity delivery failure.
- The named Beta owner must be able to pause new invitations immediately. Publish an
  incident/support contact before inviting users.

## External evidence still required

- Managed PostgreSQL endpoint and migration rehearsal
- encrypted backup destination and successful restore record
- HTTPS ingress/proxy configuration and cookie verification
- monitoring/alert destination and on-call owner
- legal, veterinarian and model qualification approvals
