from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


DATASET_VERSION = "relapaw-demo/v1-observe-review-baseline"
SCHEMA_REVISION = "20261012_0008"
SYNTHETIC_PET_NAME = "CanCan12"
RECORDED_MODEL_VERSION = "recorded-demo/v1"


@dataclass(frozen=True)
class EpisodeSpec:
    days_ago: int
    episode_type: str
    raw_owner_input: str
    observation: str
    interpretation: str
    duration_seconds: int
    intensity: int
    safety_result: str = "NORMAL"
    danger_signals: tuple[str, ...] = ()


EPISODES = (
    EpisodeSpec(13, "post_walk_recovery", "CanCan12 散步后约 2 分钟恢复平静。", "呼吸逐渐放缓，能正常饮水。", "这是平时的恢复速度。", 120, 2),
    EpisodeSpec(10, "post_walk_recovery", "CanCan12 散步后约 3 分钟恢复平静。", "张口呼吸约 3 分钟，随后恢复。", "天气较暖时偶尔如此。", 180, 2),
    EpisodeSpec(8, "post_walk_recovery", "CanCan12 散步后约 2 分半恢复。", "胸腹起伏逐渐减弱。", "看起来与平时接近。", 150, 2),
    EpisodeSpec(5, "post_walk_recovery", "CanCan12 散步回来后呼吸较急。", "张口呼吸、胸部起伏明显，持续约 3 分钟。", "我担心这次和平时不同。", 180, 3),
    EpisodeSpec(2, "resting_behavior", "CanCan12 午后在窗边安静休息。", "侧卧休息，呼吸均匀。", "这是它常见的午休状态。", 900, 1),
    EpisodeSpec(0, "urgent_breathing", "CanCan12 突然持续呼吸困难，我已准备联系兽医。", "静止时仍明显费力呼吸。", "这不是它平时的状态。", 240, 5, "ESCALATE_TO_VET", ("breathing_difficulty",)),
)


def normalized_base_now(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("base_now must include a timezone offset")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def happened_at(base_now: datetime, days_ago: int) -> datetime:
    return normalized_base_now(base_now) - timedelta(days=days_ago)

