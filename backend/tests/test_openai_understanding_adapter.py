from types import SimpleNamespace

import httpx2
import openai
import pytest
from pydantic import SecretStr, ValidationError

import app.services.understanding_adapter as adapter_module
from app.core.config import Settings, settings
from app.schemas.analysis import UnderstandingInput
from app.services.understanding_adapter import (
    AdapterError,
    OpenAIResponsesAdapter,
    QwenChatCompletionsAdapter,
    get_text_understanding_adapter,
)


def understanding_input() -> UnderstandingInput:
    return UnderstandingInput.model_validate({
        "episode_id": 21,
        "pet_id": 7,
        "raw_owner_input": "Mochi paused at the doorway.",
        "observations": [{"id": 31, "description": "Paused for 25 seconds", "behavior_type": "pause"}],
        "owner_interpretations": [{"id": 41, "interpretation": "I wonder if she was uncertain"}],
        "safety_status": "NORMAL",
        "evidence": [{
            "key": "evidence:51",
            "source_type": "RAW_OWNER_INPUT",
            "field_path": "raw_owner_input",
            "observed_at": "2026-10-09T01:30:00Z",
            "recorded_at": "2026-10-09T01:31:00Z",
            "excerpt": "Mochi paused at the doorway.",
        }],
    })


def valid_output() -> dict:
    return {
        "contract_version": "understanding-output/v1",
        "claims": [{
            "claim_type": "behavior_hypothesis",
            "statement": "One possible explanation is that the pause related to the immediate context.",
            "confidence_label": "LOW",
            "evidence": [{"evidence_key": "evidence:51", "role": "SUPPORTS"}],
            "uncertainties": [{"kind": "LIMITED_OBSERVATION", "description": "Only one short episode was recorded."}],
        }],
    }


class FakeResponses:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def fake_client(result=None, error=None):
    endpoint = FakeResponses(result, error)
    return SimpleNamespace(responses=endpoint), endpoint


def fake_chat_client(result=None, error=None):
    endpoint = FakeResponses(result, error)
    return SimpleNamespace(chat=SimpleNamespace(completions=endpoint)), endpoint


def adapter(client) -> OpenAIResponsesAdapter:
    return OpenAIResponsesAdapter(
        api_key="test-key-never-sent",
        model="configured-model",
        timeout_seconds=7,
        max_output_tokens=900,
        client=client,
    )


def response_error(error_type, status=500):
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    if error_type in (openai.APITimeoutError,):
        return error_type(request)
    if error_type in (openai.APIConnectionError,):
        return error_type(request=request)
    response = httpx2.Response(status, request=request)
    if error_type is openai.APIResponseValidationError:
        return error_type(response=response, body={})
    return error_type("provider error", response=response, body={})


def test_responses_parse_uses_structured_output_and_no_tools_or_storage():
    result = SimpleNamespace(output_parsed=valid_output(), model="resolved-model-2026-10-01", status="completed", output=[])
    client, endpoint = fake_client(result=result)
    provider = adapter(client)

    output = provider.analyze(understanding_input())

    assert output.claims[0].confidence_label.value == "LOW"
    call = endpoint.calls[0]
    assert call["model"] == "configured-model"
    assert call["text_format"].__name__ == "UnderstandingOutput"
    assert call["store"] is False
    assert call["max_output_tokens"] == 900
    assert "tools" not in call
    assert "test-key-never-sent" not in call["input"]
    assert "not observed fact" in call["instructions"]
    assert "Do not diagnose" in call["instructions"]
    assert "observation or behavior itself" in call["instructions"]
    assert "Match the natural language" in call["instructions"]
    assert "never as supporting evidence" in call["instructions"]
    assert provider.descriptor.prompt_contract_version == "text-understanding/v3-provider-neutral"
    assert provider.descriptor.model_version == "resolved-model-2026-10-01"


@pytest.mark.parametrize(("error_type", "expected_code", "status"), [
    (openai.AuthenticationError, "MODEL_AUTHENTICATION_FAILED", 401),
    (openai.PermissionDeniedError, "MODEL_PERMISSION_DENIED", 403),
    (openai.APITimeoutError, "MODEL_TIMEOUT", 0),
    (openai.RateLimitError, "MODEL_RATE_LIMITED", 429),
    (openai.APIConnectionError, "MODEL_NETWORK_ERROR", 0),
    (openai.APIResponseValidationError, "MODEL_OUTPUT_INVALID", 500),
    (openai.BadRequestError, "MODEL_REQUEST_REJECTED", 400),
    (openai.InternalServerError, "MODEL_PROVIDER_UNAVAILABLE", 500),
])
def test_provider_errors_map_to_stable_safe_codes(error_type, expected_code, status):
    client, _endpoint = fake_client(error=response_error(error_type, status or 500))
    with pytest.raises(AdapterError) as caught:
        adapter(client).analyze(understanding_input())
    assert caught.value.code == expected_code
    assert "provider error" not in caught.value.message


@pytest.mark.parametrize(("response", "expected_code"), [
    (SimpleNamespace(output_parsed=None, model="m", status="incomplete", output=[]), "MODEL_OUTPUT_INCOMPLETE"),
    (SimpleNamespace(output_parsed=None, model="m", status="completed", output=[SimpleNamespace(content=[SimpleNamespace(type="refusal")])]), "MODEL_REFUSED"),
    (SimpleNamespace(output_parsed=None, model="m", status="completed", output=[]), "MODEL_OUTPUT_INVALID"),
])
def test_unusable_provider_outputs_are_rejected(response, expected_code):
    client, _endpoint = fake_client(result=response)
    with pytest.raises(AdapterError) as caught:
        adapter(client).analyze(understanding_input())
    assert caught.value.code == expected_code


def test_sdk_pydantic_parse_failure_maps_to_invalid_output():
    validation_error = ValidationError.from_exception_data(
        "UnderstandingOutput",
        [{"type": "json_invalid", "loc": (), "input": "not-json", "ctx": {"error": "expected value"}}],
    )
    client, _endpoint = fake_client(error=validation_error)

    with pytest.raises(AdapterError) as caught:
        adapter(client).analyze(understanding_input())

    assert caught.value.code == "MODEL_OUTPUT_INVALID"
    assert "not-json" not in caught.value.message


@pytest.mark.parametrize(("error", "expected_code"), [
    (openai.LengthFinishReasonError(completion=SimpleNamespace(usage=None)), "MODEL_OUTPUT_INCOMPLETE"),
    (openai.ContentFilterFinishReasonError(), "MODEL_REFUSED"),
])
def test_structured_output_finish_errors_are_mapped(error, expected_code):
    client, _endpoint = fake_client(error=error)
    with pytest.raises(AdapterError) as caught:
        adapter(client).analyze(understanding_input())
    assert caught.value.code == expected_code


def test_adapter_factory_requires_both_key_and_model(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "openai_model", "configured-model")
    assert get_text_understanding_adapter().descriptor.adapter_name == "disabled"
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "openai_model", None)
    assert get_text_understanding_adapter().descriptor.adapter_name == "disabled"


def test_configured_factory_builds_zero_retry_timeout_client(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(adapter_module, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings, "openai_model", "configured-model")
    monkeypatch.setattr(settings, "openai_timeout_seconds", 9.0)
    monkeypatch.setattr(settings, "openai_max_output_tokens", 1000)
    monkeypatch.setattr(settings, "openai_base_url", None)
    monkeypatch.setattr(settings, "model_provider", "openai")

    provider = get_text_understanding_adapter()

    assert provider.descriptor.adapter_name == "openai-responses"
    assert captured == {"api_key": "test-key", "timeout": 9.0, "max_retries": 0}


def test_configured_factory_supports_qwen_compatible_responses_endpoint(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(adapter_module, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("qwen-test-key"))
    monkeypatch.setattr(settings, "openai_model", "qwen3.8-flash")
    monkeypatch.setattr(settings, "openai_base_url", "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(settings, "model_provider", "qwen")
    monkeypatch.setattr(settings, "openai_timeout_seconds", 12.0)
    monkeypatch.setattr(settings, "openai_max_output_tokens", 1200)

    provider = get_text_understanding_adapter()

    assert isinstance(provider, QwenChatCompletionsAdapter)
    assert provider.descriptor.adapter_name == "qwen-openai-chat-completions"
    assert provider.descriptor.model_provider == "qwen"
    assert provider.descriptor.model_name == "qwen3.8-flash"
    assert captured == {
        "api_key": "qwen-test-key",
        "base_url": "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        "timeout": 12.0,
        "max_retries": 0,
    }


def test_qwen_chat_parse_uses_json_schema_contract_and_disables_thinking():
    result = SimpleNamespace(
        model="qwen3.8-flash-2026-09-01",
        choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(parsed=valid_output(), refusal=None),
        )],
    )
    client, endpoint = fake_chat_client(result=result)
    provider = QwenChatCompletionsAdapter(
        api_key="test-key-never-sent",
        model="qwen3.8-flash",
        timeout_seconds=60,
        max_output_tokens=1600,
        model_provider="qwen",
        client=client,
    )

    output = provider.analyze(understanding_input())

    assert output.claims[0].confidence_label.value == "LOW"
    call = endpoint.calls[0]
    assert call["response_format"] is not None
    assert call["response_format"].__name__ == "UnderstandingOutput"
    assert call["extra_body"] == {"enable_thinking": False}
    assert "tools" not in call
    assert "max_tokens" not in call
    assert "max_completion_tokens" not in call
    assert "test-key-never-sent" not in call["messages"][1]["content"]
    assert provider.descriptor.model_version == "qwen3.8-flash-2026-09-01"


@pytest.mark.parametrize(("finish_reason", "refusal", "parsed", "expected_code"), [
    ("length", None, None, "MODEL_OUTPUT_INCOMPLETE"),
    ("content_filter", None, None, "MODEL_REFUSED"),
    ("stop", "declined", None, "MODEL_REFUSED"),
    ("stop", None, None, "MODEL_OUTPUT_INVALID"),
])
def test_qwen_chat_unusable_outputs_are_rejected(finish_reason, refusal, parsed, expected_code):
    result = SimpleNamespace(
        model="qwen3.8-flash",
        choices=[SimpleNamespace(
            finish_reason=finish_reason,
            message=SimpleNamespace(parsed=parsed, refusal=refusal),
        )],
    )
    client, _endpoint = fake_chat_client(result=result)
    provider = QwenChatCompletionsAdapter(
        api_key="test-key",
        model="qwen3.8-flash",
        timeout_seconds=60,
        max_output_tokens=1600,
        model_provider="qwen",
        client=client,
    )

    with pytest.raises(AdapterError) as caught:
        provider.analyze(understanding_input())

    assert caught.value.code == expected_code


def test_settings_load_standard_key_and_relapaw_model_without_exposing_secret(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-value")
    monkeypatch.setenv("RELAPAW_OPENAI_MODEL", "configured-model")
    monkeypatch.setenv("RELAPAW_OPENAI_BASE_URL", "https://compatible.example/v1")
    monkeypatch.setenv("RELAPAW_MODEL_PROVIDER", "qwen")

    loaded = Settings(_env_file=None)

    assert loaded.openai_api_key is not None
    assert loaded.openai_api_key.get_secret_value() == "secret-test-value"
    assert loaded.openai_model == "configured-model"
    assert loaded.openai_base_url == "https://compatible.example/v1"
    assert loaded.model_provider == "qwen"
    assert "secret-test-value" not in repr(loaded)
