from types import SimpleNamespace

from pydantic import SecretStr

import app.services.assistant_adapter as adapter_module
from app.core.config import settings
from app.schemas.assistant import AssistantGuidanceInput, AssistantGuidanceOutput
from app.services.assistant_adapter import (
    OpenAIAssistantGuidanceAdapter,
    QwenAssistantGuidanceAdapter,
    get_assistant_guidance_adapter,
)


def guidance_input():
    return AssistantGuidanceInput.model_validate({
        "mode": "RECORD_REVIEW", "pet_id": 7, "species": "cat",
        "current_record": {"episode_id": 1, "happened_at": "2026-10-25T08:00:00Z", "raw_owner_input": "在门口停留。", "observations": ["停留 25 秒"], "owner_interpretations": ["我觉得它在等"], "safety_status": "NORMAL"},
        "recent_records": [], "recent_records_truncated": False,
        "controlled_knowledge": [{"id": "context", "version": "v1", "citation_id": "knowledge:context@v1", "title": "记录情境", "summary": "记录时间和地点", "source_title": "受控指南", "source_locator": "context"}],
    })


def output():
    return {
        "records_show": ["停留 25 秒"], "owner_interpretation": ["我觉得它在等"],
        "possibly_relevant_background": ["一致记录有助比较"], "cannot_determine": ["不能确定原因"],
        "continue_observing": ["继续记录地点"], "contact_vet_when": ["出现紧急情况时联系兽医"],
        "sources_used": [{"citation_id": "knowledge:context@v1", "knowledge_id": "context", "knowledge_version": "v1", "supports_section": "possibly_relevant_background", "item_index": 0}, {"citation_id": "knowledge:context@v1", "knowledge_id": "context", "knowledge_version": "v1", "supports_section": "continue_observing", "item_index": 0}],
        "record_sources": [{"section": "records_show", "item_index": 0, "episode_ids": [1]}, {"section": "owner_interpretation", "item_index": 0, "episode_ids": [1]}],
    }


class Endpoint:
    def __init__(self, result): self.result, self.calls = result, []
    def parse(self, **kwargs): self.calls.append(kwargs); return self.result


def test_openai_guidance_uses_structured_output_without_tools_or_storage():
    endpoint = Endpoint(SimpleNamespace(output_parsed=output(), model="resolved-model"))
    client = SimpleNamespace(responses=endpoint)
    adapter = OpenAIAssistantGuidanceAdapter(api_key="test-only", model="model", timeout_seconds=5, max_output_tokens=700, client=client)
    result = adapter.generate(guidance_input())
    assert result.records_show == ["停留 25 秒"]
    call = endpoint.calls[0]
    assert call["store"] is False and "tools" not in call
    assert "test-only" not in call["input"]
    assert "untrusted data" in call["instructions"]
    assert adapter.descriptor.model_version == "resolved-model"


def test_qwen_guidance_uses_chat_json_schema_and_disables_thinking():
    endpoint = Endpoint(SimpleNamespace(model="resolved-qwen", choices=[SimpleNamespace(message=SimpleNamespace(parsed=output(), refusal=None))]))
    client = SimpleNamespace(chat=SimpleNamespace(completions=endpoint))
    adapter = QwenAssistantGuidanceAdapter(api_key="test-only", model="qwen", timeout_seconds=5, max_output_tokens=700, model_provider="qwen", client=client)
    assert adapter.generate(guidance_input()).cannot_determine
    call = endpoint.calls[0]
    assert call["response_format"].__name__ == "AssistantGuidanceOutput"
    assert call["extra_body"] == {"enable_thinking": False}
    assert "tools" not in call


def test_v4_schema_and_prompt_make_versioned_claim_mapping_explicit():
    schema = AssistantGuidanceOutput.model_json_schema()
    citation = schema["$defs"]["GuidanceCitation"]
    assert set(citation["required"]) == {
        "citation_id", "knowledge_id", "knowledge_version", "supports_section", "item_index",
    }
    assert "same supports_section and zero-based item_index" in adapter_module.SYSTEM_PROMPT
    assert "Copy citation_id, knowledge_id, and knowledge_version exactly" in adapter_module.SYSTEM_PROMPT
    assert "If controlled_knowledge is empty" in adapter_module.SYSTEM_PROMPT
    assert "knowledge:context@v1" in adapter_module._input_prompt(guidance_input())


def test_guidance_factory_is_disabled_without_both_secret_and_model(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "openai_model", "model")
    assert get_assistant_guidance_adapter().descriptor.adapter_name == "disabled"
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test"))
    monkeypatch.setattr(settings, "openai_model", None)
    assert get_assistant_guidance_adapter().descriptor.adapter_name == "disabled"


def test_guidance_factory_uses_qwen_path(monkeypatch):
    captured = {}
    class FakeOpenAI:
        def __init__(self, **kwargs): captured.update(kwargs)
    monkeypatch.setattr(adapter_module, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test"))
    monkeypatch.setattr(settings, "openai_model", "qwen-model")
    monkeypatch.setattr(settings, "openai_base_url", "https://compatible.example/v1")
    monkeypatch.setattr(settings, "model_provider", "qwen")
    adapter = get_assistant_guidance_adapter()
    assert isinstance(adapter, QwenAssistantGuidanceAdapter)
    assert captured["max_retries"] == 0 and captured["api_key"] == "test"
