from dataclasses import dataclass, field
from enum import IntEnum


class Tier(IntEnum):
    """가져오기 단계. 숫자가 작을수록 가볍고 빠릅니다."""
    REQUEST = 1        # curl_cffi (브라우저 TLS 지문 흉내)
    PLAYWRIGHT = 2     # 헤드리스 크로미움
    FLARESOLVERR = 3   # Cloudflare 등 챌린지 해결용, 가장 무거움

    @property
    def label(self) -> str:
        return self.name.lower()

    @classmethod
    def from_label(cls, label: str) -> "Tier":
        return cls[label.upper()]


@dataclass
class FetchResult:
    html: str
    status: int
    tier: Tier
    cookies: dict[str, str] = field(default_factory=dict)
    user_agent: str | None = None
