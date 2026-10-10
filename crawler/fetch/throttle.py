"""도메인별 요청 간격 제어.

같은 도메인에 대한 모든 요청(단계 전환 재시도 포함) 사이에
최소 간격 + 랜덤 지터를 두어 일정한 패턴으로 찍히지 않게 합니다.
간격은 사이트의 request_delay(초)를 기준으로 합니다.
"""

import random
import time
from urllib.parse import urlparse

JITTER_RATIO = (0.3, 1.0)   # request_delay의 30~100%를 추가로 무작위 대기

_last_request: dict[str, float] = {}


def wait(url: str, min_interval: float) -> float:
    """해당 도메인의 직전 요청 이후 충분히 지나지 않았으면 잠시 대기. 실제 대기 시간(초)을 반환."""
    host = urlparse(url).hostname or url
    target = min_interval * (1 + random.uniform(*JITTER_RATIO))
    slept = 0.0
    last = _last_request.get(host)
    if last is not None:
        slept = max(0.0, target - (time.monotonic() - last))
        if slept:
            time.sleep(slept)
    _last_request[host] = time.monotonic()
    return slept
