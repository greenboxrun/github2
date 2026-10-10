"""사이트별 세션 상태를 result/.cache/sessions/{site}.json 에 저장합니다.

- cookies / user_agent : 브라우저 단계(Playwright·FlareSolverr)에서 얻은 값. 다음 실행에 request 단계로 재사용.
  cf_clearance 같은 쿠키는 UA+IP에 묶이므로 반드시 UA도 같이 씁니다.
- last_tier            : 직전에 성공한 단계. 다음 실행은 여기서부터 시작해 헛시도를 줄입니다.
- runs_since_reset     : last_tier로 건너뛴 횟수. 일정 횟수마다 처음 단계부터 다시 시도해
                         사이트 차단이 풀렸으면 가벼운 단계로 돌아갑니다.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..paths import SESSION_DIR
from ..timeutil import now_utc_iso
from .types import Tier


@dataclass
class SessionState:
    cookies: dict[str, str] = field(default_factory=dict)
    user_agent: str | None = None
    last_tier: str | None = None
    runs_since_reset: int = 0
    updated_at: str | None = None

    @property
    def last_tier_enum(self) -> Tier | None:
        return Tier.from_label(self.last_tier) if self.last_tier else None

    def forget_cookies(self) -> None:
        """만료됐을 수 있는 쿠키+UA를 버립니다. 다음 요청은 쿠키 없이 나갑니다."""
        self.cookies, self.user_agent = {}, None

    def remember_success(self, tier: Tier, skipped: bool) -> None:
        """성공한 단계를 기억합니다. 기억값 때문에 단계를 건너뛰었으면 카운트를 올리고, 아니면 0으로."""
        self.runs_since_reset = self.runs_since_reset + 1 if skipped else 0
        self.last_tier = tier.label

    def reset_memory(self) -> None:
        """전부 실패했을 때 호출. 다음 실행은 처음 단계부터 다시 시도합니다."""
        self.last_tier, self.runs_since_reset = None, 0


def _path(site: str) -> Path:
    return SESSION_DIR / f"{site}.json"


def load(site: str) -> SessionState:
    try:
        return SessionState(**json.loads(_path(site).read_text(encoding="utf-8")))
    except FileNotFoundError:
        return SessionState()
    except (ValueError, TypeError):
        return SessionState()  # 깨진 캐시는 무시


def save(site: str, state: SessionState) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    state.updated_at = now_utc_iso()
    _path(site).write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def clear(site: str) -> None:
    _path(site).unlink(missing_ok=True)
