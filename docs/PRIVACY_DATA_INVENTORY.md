# Relapaw privacy data inventory

Version: `relapaw-data-inventory/v1`<br>
Status: implementation baseline; retention promises and policy text require legal review

Relapaw stores only data needed for an invited owner to keep pet records, review their
history, and control optional derived memory. Runtime AI is off by default. The verified
local flow sends no owner or pet content to an external model.

| Category | Storage | Purpose and source | Export | Deletion |
|---|---|---|---|---|
| Account and identity | `users`, `user_identities`, `identity_invitations` | Access control; provider-verified invited identity | Account status and provider name; provider subject intentionally omitted | Account purge removes account and identity; invitation loses account link |
| Browser security | `user_sessions` | Opaque session digest, CSRF digest, expiry, coarse user-agent summary | Never exported | Revoked immediately on deletion request; removed at account purge |
| Consent | `terms_acceptances` | Version, time and onboarding/version-update source | Included | Removed at account purge |
| Owner preferences | `owner_profiles` | Owner-entered display/interaction preferences | Included | Removed at account purge |
| Pet profile | `pets`, `pet_baselines`, `life_events` | Owner-entered identity, routine and life context | Included | Removed at account purge |
| Observation records | `episodes`, observations, interpretations, safety, evidence and escalation tables | Owner-entered events plus explicitly separated facts, interpretations and safety outputs | Active records included | Episode deletion clears content and derived data, retaining only a minimal inaccessible tombstone where referential integrity requires it |
| Plans and follow-ups | observation plans/items, episode links, follow-ups | Owner-created observation workflow | Included | Removed at account purge; pending follow-ups are cancelled when their source episode is deleted |
| Derived analysis | analysis runs, claims, evidence, uncertainties and confirmations | Versioned deterministic or explicitly enabled model output and owner decisions | Included | Removed with source episode or account |
| Long-term memory | candidates and decisions | Owner-controlled candidate snapshot and include/withdraw history | Included | Removed with source analysis or account |
| Quantitative baselines | snapshots and evidence | Reproducible summaries with source lineage | Included | Snapshots containing a deleted episode are removed; all removed at account purge |
| Security/privacy audit | `audit_events` | Content-free pseudonymous proof of consent, export and deletion operations | Not part of personal-data export | Separate 365-day default retention, then scheduled removal |

## Retention and operational rules

- A deletion request immediately marks the account pending and revokes all sessions.
- Account data is purged after the configured grace period (default 7 days) by
  `python -m app.jobs.privacy_retention`. Re-running the job is safe.
- Audit events contain keyed pseudonyms, event types and bounded metadata—not email,
  pet names, narratives, model inputs or session secrets. The default retention is
  365 days.
- Database backups are not edited in place. Personal data may remain in encrypted,
  access-controlled backups until normal backup rotation expires; restoring a backup
  requires replaying due deletion jobs before reopening service.
- The grace period, audit window, backup rotation, final Terms and Privacy Notice must
  be approved by legal and the named Beta operator before production invitations.

## Third parties

The current local identity adapter and deterministic analysis path have no third-party
content transfer. A production identity/email provider, hosting/database operator, and
any future model processor must be added to this inventory with region, purpose,
fields, retention, contract and deletion behavior before enablement.
