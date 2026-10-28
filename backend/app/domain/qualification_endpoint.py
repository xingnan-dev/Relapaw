from typing import Any
from urllib.parse import urlsplit


def endpoint_matches_policy(base_url: str, policy: dict[str, Any]) -> bool:
    """Match a qualified endpoint without storing tenant/workspace host prefixes."""
    try:
        parsed = urlsplit(base_url)
    except ValueError:
        return False
    hostname = (parsed.hostname or "").lower()
    suffix = str(policy.get("hostname_suffix", "")).lower()
    expected_path = str(policy.get("path", "")).rstrip("/")
    return bool(
        parsed.scheme == policy.get("scheme", "https")
        and parsed.username is None
        and parsed.password is None
        and parsed.port in (None, 443)
        and suffix.startswith(".")
        and hostname.endswith(suffix)
        and hostname != suffix.removeprefix(".")
        and parsed.path.rstrip("/") == expected_path
        and not parsed.query
        and not parsed.fragment
    )


QWEN_BEIJING_ENDPOINT_POLICY = {
    "scheme": "https",
    "hostname_suffix": ".cn-beijing.maas.aliyuncs.com",
    "path": "/compatible-mode/v1",
}
