# Medical safety and AI qualification register

Status: **NOT APPROVED FOR PRODUCTION**<br>
Selected medical content: `medical-safety/v1`<br>
Selected model qualification: `NOT_QUALIFIED`

## Medical safety review

The executable source is `backend/app/domain/medical_safety.py`. It contains only
owner-selected urgent routing signals and the instruction to contact a veterinarian;
it does not contain diagnoses or treatment advice. Its signal keys are tested against
the API enum so UI/API content cannot silently drift.

Changing `RELAPAW_MEDICAL_REVIEW_STATUS` alone cannot approve this content. Record the
following directly in the executable manifest and review the resulting change:

| Field | Required value |
|---|---|
| Version reviewed | Exact manifest version |
| Reviewer | Licensed veterinarian name |
| Credential | License/credential and jurisdiction |
| Review time | UTC timestamp |
| Approval reference | Immutable review ticket or signed artifact |
| Scope/limitations | Species, locale, wording and escalation limitations |

## Model qualification

`RELAPAW_AI_ENABLED=true` is insufficient by design. Runtime access also requires
`RELAPAW_MODEL_QUALIFICATION=QUALIFIED` and an ID present in the repository's
`MODEL_QUALIFICATIONS` registry. The record must exactly match provider, model, base
URL, prompt contract and input/output contracts. The supporting evaluation must also
cover safety blocking, evidence grounding, invalid-output handling, latency and cost.
The registry is intentionally empty until such evidence is externally approved.

Until those external reviews exist, capabilities report AI unavailable, normal
episodes return `MODEL_NOT_QUALIFIED` if an operator accidentally enables the raw
switch, and every non-`NORMAL` Safety Check is blocked before any adapter invocation.
