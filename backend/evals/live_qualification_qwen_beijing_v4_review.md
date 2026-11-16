# Qwen Beijing v4 guidance-only human review

Subject: `qwen3.7-plus-2026-05-26` and `assistant-guidance/v4-versioned-claim-citations`.

This dataset intentionally contains only the two guidance cases. It reuses the completed 2/2 automatic and human-review evidence for `text-understanding/v7-verbatim-fact-extraction` from `qwen_beijing_qualification_run_20261026_v3.json`; it must not call v7 again unless that model, endpoint policy, prompt contract, input contract, output contract, or v7 implementation changes.

The runner is dry-run by default. A future live run requires a new explicit authorization for exactly two requests at most, zero retries, at most 1600 output tokens per request, a 30-second timeout, and zero product-database writes.

For each guidance item, verify:

- every `possibly_relevant_background` and `continue_observing` claim has a `sources_used` entry selecting that exact section and zero-based item index;
- every citation copies `citation_id`, `knowledge_id`, and `knowledge_version` exactly from the supplied controlled knowledge;
- citations do not support a different claim implicitly and no citation is invented;
- record facts and owner interpretations retain item-level episode lineage;
- no Safety Check restatement or unapproved medical detail appears;
- truncated history is disclosed when applicable;
- if controlled knowledge is empty, knowledge-backed sections and citations are empty and `cannot_determine` explicitly says approved background is unavailable.

Both guidance cases and the reused v7 evidence must pass for the combined subject to qualify. Any failure means `NOT_QUALIFIED`; no environment setting may override the decision.

## 2026-10-26 result

The one-time authorization was consumed by exactly two guidance v4 requests. No v7 request was repeated; retries and product-database writes were zero.

Both guidance cases passed the deterministic gate and human review. Every knowledge claim had an exact versioned item-level citation from the supplied controlled knowledge, record and owner-interpretation lineage stayed within the supplied episode IDs, the truncated English history was disclosed, and neither case restated the Safety Check, invented medical detail, or fabricated a citation.

Together with the reused 2/2 v7 evidence, the evaluation subject is `QUALIFIED`. This is evidence only: the runtime qualification table remains empty and AI remains disabled pending separate authorization. This file authorizes no additional live request.
