import re
from typing import Any, Protocol, runtime_checkable

import openai
from openai import OpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.analysis import AdapterDescriptor, UnderstandingInput, UnderstandingOutput


PROMPT_CONTRACT_VERSION = "text-understanding/v5-grounded-claims"
SYSTEM_PROMPT = """You generate cautious, structured text-understanding proposals for a pet owner's recorded Episode.

Hard boundaries:
- Return only claims that are possible explanations requiring user confirmation. Never present a claim as fact.
- Each claim must explain the Episode's recorded observation or behavior itself. Do not make the owner's decision, concern, wording, or decision to contact a veterinarian the subject of a claim.
- Do not merely restate or summarize the input. A claim must add a cautious, useful interpretation grounded in the recorded Episode.
- Do not diagnose medical, behavioral, or psychological conditions. Do not recommend treatment, medication, dosage, or delaying veterinary care.
- Keep Raw Input, Observation, and Owner Interpretation distinct. Owner Interpretation is the owner's hypothesis, not observed fact. It may only be cited as CONTEXT or LIMITS, never as SUPPORTS.
- Cite only evidence_key values present in the supplied Episode input. Never invent or use outside evidence.
- Every claim must include at least one evidence reference and at least one meaningful uncertainty.
- Use LOW, MEDIUM, or HIGH only as qualitative confidence labels; do not produce numeric probabilities or scores.
- If the evidence is limited or alternatives remain, say so explicitly in uncertainties.
- Match the natural language used by the owner input for all human-readable statements and uncertainty descriptions. Keep enum and contract field values unchanged.
- Context that was not recorded may appear only as explicitly missing or uncertain context, never as supporting evidence or an asserted cause.
- Do not infer an unrecorded sensory trigger, intention, emotion, decision, safety assessment, vigilance cycle, or other internal state from behavior alone. Put such alternatives only in uncertainties.
- Do not make a claim about whether the owner's hypothesis aligns with the observation. Analyze the recorded behavior, not the quality of the owner's interpretation.
- If no useful explanation can be grounded in recorded Evidence without relying on an unrecorded cause or internal state, return an empty claims list instead of speculating.
- The SafetyCheck has already gated this request. Do not reinterpret or downgrade it.
- Do not use external knowledge, retrieval, tools, images, or hidden context. Analyze only the supplied JSON.
"""

_CJK = re.compile(r"[\u3400-\u9fff]")


def _input_prompt(payload: UnderstandingInput) -> str:
    language = "Chinese (zh)" if _CJK.search(payload.raw_owner_input) else "English (en)"
    return (
        f"Required language for every human-readable claim and uncertainty: {language}.\n"
        "Episode input JSON:\n"
        + payload.model_dump_json()
    )


class AdapterError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 503):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@runtime_checkable
class TextUnderstandingAdapter(Protocol):
    @property
    def descriptor(self) -> AdapterDescriptor: ...

    def analyze(self, payload: UnderstandingInput) -> UnderstandingOutput: ...


class DisabledAdapter:
    descriptor = AdapterDescriptor(
        adapter_name="disabled",
        model_provider="none",
        model_name="none",
        model_version="none",
        prompt_contract_version="text-understanding/v1",
    )

    def analyze(self, payload: UnderstandingInput) -> UnderstandingOutput:
        del payload
        raise AdapterError("MODEL_NOT_CONFIGURED", "Text understanding model is not configured")


class OpenAIResponsesAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        base_url: str | None = None,
        model_provider: str = "openai",
        client: Any | None = None,
    ):
        self._model = model
        self._resolved_model = model
        self._model_provider = model_provider
        self._max_output_tokens = max_output_tokens
        client_options: dict[str, Any] = {
            "api_key": api_key,
            "timeout": timeout_seconds,
            "max_retries": 0,
        }
        if base_url:
            client_options["base_url"] = base_url
        self._client = client or OpenAI(**client_options)

    @property
    def descriptor(self) -> AdapterDescriptor:
        return AdapterDescriptor(
            adapter_name="openai-responses",
            model_provider=self._model_provider,
            model_name=self._model,
            model_version=self._resolved_model,
            prompt_contract_version=PROMPT_CONTRACT_VERSION,
        )

    def analyze(self, payload: UnderstandingInput) -> UnderstandingOutput:
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=SYSTEM_PROMPT,
                input=_input_prompt(payload),
                text_format=UnderstandingOutput,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except openai.AuthenticationError as exc:
            raise AdapterError("MODEL_AUTHENTICATION_FAILED", "Model provider authentication failed", 503) from exc
        except openai.PermissionDeniedError as exc:
            raise AdapterError("MODEL_PERMISSION_DENIED", "Model provider denied access", 503) from exc
        except openai.APITimeoutError as exc:
            raise AdapterError("MODEL_TIMEOUT", "Model provider request timed out", 504) from exc
        except openai.RateLimitError as exc:
            raise AdapterError("MODEL_RATE_LIMITED", "Model provider rate limit reached", 503) from exc
        except openai.APIConnectionError as exc:
            raise AdapterError("MODEL_NETWORK_ERROR", "Model provider could not be reached", 503) from exc
        except openai.APIResponseValidationError as exc:
            raise AdapterError("MODEL_OUTPUT_INVALID", "Model provider returned an invalid response", 502) from exc
        except openai.LengthFinishReasonError as exc:
            raise AdapterError("MODEL_OUTPUT_INCOMPLETE", "Model output was incomplete", 502) from exc
        except openai.ContentFilterFinishReasonError as exc:
            raise AdapterError("MODEL_REFUSED", "Model declined to produce an analysis", 422) from exc
        except openai.BadRequestError as exc:
            raise AdapterError("MODEL_REQUEST_REJECTED", "Model provider rejected the request", 502) from exc
        except openai.InternalServerError as exc:
            raise AdapterError("MODEL_PROVIDER_UNAVAILABLE", "Model provider is temporarily unavailable", 503) from exc
        except openai.APIStatusError as exc:
            raise AdapterError("MODEL_PROVIDER_ERROR", "Model provider request failed", 502) from exc
        except openai.APIError as exc:
            raise AdapterError("MODEL_PROVIDER_ERROR", "Model provider request failed", 502) from exc
        except openai.OpenAIError as exc:
            raise AdapterError("MODEL_PROVIDER_ERROR", "Model provider request failed", 502) from exc
        except ValidationError as exc:
            raise AdapterError("MODEL_OUTPUT_INVALID", "Model output did not match the required contract", 502) from exc

        resolved_model = getattr(response, "model", None)
        if isinstance(resolved_model, str) and resolved_model:
            self._resolved_model = resolved_model
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            status = getattr(response, "status", None)
            if status == "incomplete":
                raise AdapterError("MODEL_OUTPUT_INCOMPLETE", "Model output was incomplete", 502)
            if _contains_refusal(response):
                raise AdapterError("MODEL_REFUSED", "Model declined to produce an analysis", 422)
            raise AdapterError("MODEL_OUTPUT_INVALID", "Model output did not match the required contract", 502)
        return UnderstandingOutput.model_validate(parsed)


class QwenChatCompletionsAdapter(OpenAIResponsesAdapter):
    @property
    def descriptor(self) -> AdapterDescriptor:
        return AdapterDescriptor(
            adapter_name="qwen-openai-chat-completions",
            model_provider=self._model_provider,
            model_name=self._model,
            model_version=self._resolved_model,
            prompt_contract_version=PROMPT_CONTRACT_VERSION,
        )

    def analyze(self, payload: UnderstandingInput) -> UnderstandingOutput:
        try:
            response = self._client.chat.completions.parse(
                model=self._model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _input_prompt(payload)},
                ],
                response_format=UnderstandingOutput,
                extra_body={"enable_thinking": False},
            )
        except openai.AuthenticationError as exc:
            raise AdapterError("MODEL_AUTHENTICATION_FAILED", "Model provider authentication failed", 503) from exc
        except openai.PermissionDeniedError as exc:
            raise AdapterError("MODEL_PERMISSION_DENIED", "Model provider denied access", 503) from exc
        except openai.APITimeoutError as exc:
            raise AdapterError("MODEL_TIMEOUT", "Model provider request timed out", 504) from exc
        except openai.RateLimitError as exc:
            raise AdapterError("MODEL_RATE_LIMITED", "Model provider rate limit reached", 503) from exc
        except openai.APIConnectionError as exc:
            raise AdapterError("MODEL_NETWORK_ERROR", "Model provider could not be reached", 503) from exc
        except openai.APIResponseValidationError as exc:
            raise AdapterError("MODEL_OUTPUT_INVALID", "Model provider returned an invalid response", 502) from exc
        except openai.LengthFinishReasonError as exc:
            raise AdapterError("MODEL_OUTPUT_INCOMPLETE", "Model output was incomplete", 502) from exc
        except openai.ContentFilterFinishReasonError as exc:
            raise AdapterError("MODEL_REFUSED", "Model declined to produce an analysis", 422) from exc
        except openai.BadRequestError as exc:
            raise AdapterError("MODEL_REQUEST_REJECTED", "Model provider rejected the request", 502) from exc
        except openai.InternalServerError as exc:
            raise AdapterError("MODEL_PROVIDER_UNAVAILABLE", "Model provider is temporarily unavailable", 503) from exc
        except openai.APIStatusError as exc:
            raise AdapterError("MODEL_PROVIDER_ERROR", "Model provider request failed", 502) from exc
        except openai.APIError as exc:
            raise AdapterError("MODEL_PROVIDER_ERROR", "Model provider request failed", 502) from exc
        except openai.OpenAIError as exc:
            raise AdapterError("MODEL_PROVIDER_ERROR", "Model provider request failed", 502) from exc
        except ValidationError as exc:
            raise AdapterError("MODEL_OUTPUT_INVALID", "Model output did not match the required contract", 502) from exc

        resolved_model = getattr(response, "model", None)
        if isinstance(resolved_model, str) and resolved_model:
            self._resolved_model = resolved_model
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise AdapterError("MODEL_OUTPUT_INVALID", "Model output did not match the required contract", 502)
        choice = choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "length":
            raise AdapterError("MODEL_OUTPUT_INCOMPLETE", "Model output was incomplete", 502)
        if finish_reason == "content_filter":
            raise AdapterError("MODEL_REFUSED", "Model declined to produce an analysis", 422)
        message = getattr(choice, "message", None)
        if message is None or getattr(message, "refusal", None):
            raise AdapterError("MODEL_REFUSED", "Model declined to produce an analysis", 422)
        parsed = getattr(message, "parsed", None)
        if parsed is None:
            raise AdapterError("MODEL_OUTPUT_INVALID", "Model output did not match the required contract", 502)
        return UnderstandingOutput.model_validate(parsed)


def _contains_refusal(response: Any) -> bool:
    for item in getattr(response, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) == "refusal":
                return True
    return False


def get_text_understanding_adapter() -> TextUnderstandingAdapter:
    api_key = settings.openai_api_key
    model = settings.openai_model.strip() if settings.openai_model else ""
    if api_key is None or not api_key.get_secret_value().strip() or not model:
        return DisabledAdapter()
    adapter_class = QwenChatCompletionsAdapter if settings.model_provider.strip().lower() == "qwen" else OpenAIResponsesAdapter
    return adapter_class(
        api_key=api_key.get_secret_value(),
        model=model,
        timeout_seconds=settings.openai_timeout_seconds,
        max_output_tokens=settings.openai_max_output_tokens,
        base_url=settings.openai_base_url.strip() if settings.openai_base_url else None,
        model_provider=settings.model_provider.strip() or "openai",
    )
