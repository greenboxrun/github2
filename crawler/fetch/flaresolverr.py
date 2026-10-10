"""3단계: FlareSolverr. 리소스를 많이 쓰므로 앞 단계가 모두 실패했을 때만 호출됩니다.

성공하면 쿠키+UA를 돌려주고, chain이 이를 캐시해 다음부터는 request 단계에서 재사용합니다.

사전 준비:
    docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest
"""

import os

import requests

from ..errors import FetchError
from .types import FetchResult, Tier

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191/v1")
MAX_TIMEOUT_MS = 60_000


def fetch(url: str) -> FetchResult:
    payload = {"cmd": "request.get", "url": url, "maxTimeout": MAX_TIMEOUT_MS}
    try:
        resp = requests.post(FLARESOLVERR_URL, json=payload, timeout=MAX_TIMEOUT_MS / 1000 + 15)
    except requests.RequestException as e:
        raise FetchError(f"FlareSolverr 연결 실패 ({FLARESOLVERR_URL}, 컨테이너 실행 여부 확인): {type(e).__name__}") from e

    # FlareSolverr는 실패해도 HTTP 500과 함께 JSON 본문을 보내므로 본문을 먼저 확인합니다.
    try:
        data = resp.json()
    except ValueError as e:
        raise FetchError(f"FlareSolverr 응답이 JSON이 아님 (HTTP {resp.status_code})") from e
    if data.get("status") != "ok":
        raise FetchError(f"FlareSolverr 요청 실패: {data.get('message')}")

    sol = data["solution"]
    return FetchResult(
        html=sol["response"],
        status=sol["status"],
        tier=Tier.FLARESOLVERR,
        cookies={c["name"]: c["value"] for c in sol.get("cookies", [])},
        user_agent=sol.get("userAgent"),
    )
