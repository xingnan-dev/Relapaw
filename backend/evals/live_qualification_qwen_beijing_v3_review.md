# Qwen Beijing v3 human review

Subject: `qwen3.7-plus-2026-05-26`, `text-understanding/v7-verbatim-fact-extraction`, and unchanged `assistant-guidance/v3-item-citations-safety-boundary`.

The one-time authorization was consumed on 2026-10-26: four requests, zero retries, and zero product-database writes. It does not authorize a retry or another live request.

For each extraction item, verify that `source_quote` is an exact contiguous substring of `raw_owner_input`, preserves every character, and cites only the supplied `RAW_OWNER_INPUT` evidence key. Reject paraphrases, translations, corrections, merged spans, invented words, or references to structured observations as the extraction source.

`observation_candidates` may contain only directly observable actions, positions, counts, durations, times, consumption, elimination, or other externally verifiable events. Reject causes, stimuli, intention, emotion, diagnosis, safety judgments, and conclusions even if those concepts appear elsewhere in the record.

`owner_interpretations` may contain only an interpretation explicitly stated by the owner and must preserve the owner's marker and wording. Reject moving any owner interpretation into observations or inventing an interpretation.

Guidance v3 retains the prior item-level knowledge citations, record lineage, no Safety Check restatement, no uncited medical detail, truncated-history disclosure, and generic veterinary-contact boundary.

Qualification requires every deterministic gate and every human-review item to pass. Any failure means `NOT_QUALIFIED`; no environment setting may override the decision.

## 2026-10-26 result

The two v7 extraction cases passed deterministic validation and human review: each returned only exact contiguous source quotes, kept observable facts separate from explicit owner interpretations, and used only the supplied raw-input evidence key. The English truncated-history guidance case passed. The Chinese guidance case was rejected by the deterministic gate with `MODEL_KNOWLEDGE_CITATION_MISSING`, so its rejected output was not retained for human review.

The combined v7/v3 subject is therefore `NOT_QUALIFIED`. AI remains disabled, the qualification table remains empty, and no further live request is authorized.

The rejected provider output was deliberately not retained, so the durable evidence can identify only the exact deterministic condition: at least one Chinese `possibly_relevant_background` or `continue_observing` item lacked a matching `(supports_section, item_index)` citation. It cannot honestly identify which item without inventing evidence. This was not a Chinese text-comparison failure: the v3 gate did not compare citation text and did not reject `knowledge_id`; it failed only the completeness equality between generated item indexes and cited item indexes.
