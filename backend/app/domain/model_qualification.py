"""Repository-bound model qualification records.

Entries may only be added after the matching provider/model/contracts have passed
the documented evaluation and the approval evidence is available for review.
An environment variable alone can never create a qualification.
"""

from hashlib import sha256
from pathlib import Path
from typing import Final

from app.domain.qualification_endpoint import QWEN_BEIJING_ENDPOINT_POLICY, endpoint_matches_policy


QUALIFICATION_ID: Final = "qwen-beijing-20261026-v7-guidance-v4"
CONTRACTS: Final = [
    {
        "purpose": "text_understanding",
        "prompt": "text-understanding/v7-verbatim-fact-extraction",
        "input": "understanding-input/v1",
        "output": "understanding-output/v2",
    },
    {
        "purpose": "assistant_guidance",
        "prompt": "assistant-guidance/v4-versioned-claim-citations",
        "input": "assistant-guidance-input/v1",
        "output": "assistant-guidance-output/v4",
    },
]
EVIDENCE_MANIFEST: Final = [
    {"path": "evals/qwen_beijing_qualification_run_20261026_v3.json", "sha256": "6cba6958f2923419f3eb9b510de59a9c9b8860963de79fbd171d7308613484fd"},
    {"path": "evals/qwen_beijing_qualification_run_20261026_v4.json", "sha256": "2168f3afeb6675184806fd14c288df80a94ca22e77645656ee6212cffaa71831"},
]


MODEL_QUALIFICATIONS: Final[dict[str, dict[str, object]]] = {
    QUALIFICATION_ID: {
        "manifest_version": "model-qualification/v1",
        "status": "APPROVED",
        "provider": "qwen",
        "model": "qwen3.7-plus-2026-05-26",
        "endpoint_policy": QWEN_BEIJING_ENDPOINT_POLICY,
        "contracts": CONTRACTS,
        "knowledge_set_version": "controlled-education/2026-10-25-v1",
        "evidence_manifest": EVIDENCE_MANIFEST,
        "approved_at": "2026-10-26T00:00:00Z",
    }
}


def evidence_files_match(record: dict[str, object]) -> bool:
    backend_root = Path(__file__).resolve().parents[2]
    evidence = record.get("evidence_manifest")
    if not isinstance(evidence, list) or not evidence:
        return False
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            return False
        path = backend_root / str(item["path"])
        try:
            digest = sha256(path.read_bytes()).hexdigest()
        except OSError:
            return False
        if digest != item["sha256"]:
            return False
    return True


def repository_qualification_matches(
    qualification_id: str | None, *, provider: str, model: str, base_url: str,
    knowledge_set_version: str,
) -> bool:
    record = MODEL_QUALIFICATIONS.get(qualification_id or "")
    return bool(
        record
        and record.get("status") == "APPROVED"
        and record.get("provider") == provider
        and record.get("model") == model
        and record.get("contracts") == CONTRACTS
        and record.get("knowledge_set_version") == knowledge_set_version
        and endpoint_matches_policy(base_url, record.get("endpoint_policy", {}))
        and evidence_files_match(record)
    )
