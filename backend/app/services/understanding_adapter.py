from typing import Protocol, runtime_checkable

from app.schemas.analysis import AdapterDescriptor, UnderstandingInput, UnderstandingOutput


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


_default_adapter = DisabledAdapter()


def get_text_understanding_adapter() -> TextUnderstandingAdapter:
    return _default_adapter
