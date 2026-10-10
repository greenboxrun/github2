"""1단계: curl_cffi로 바로 요청. 가장 빠르고 가벼움.

일반 requests는 TLS 지문 때문에 쉽게 막혀서, 크롬을 흉내 내는 curl_cffi를 씁니다.
FlareSolverr가 얻어 둔 쿠키+UA가 있으면 같이 실어 보내 챌린지를 건너뜁니다.
"""

from curl_cffi import requests as cr

from ..errors import FetchError
from .types import FetchResult

TIMEOUT_SEC = 20
ACCEPT_LANGUAGE = "ko-KR,ko;q=0.9,en;q=0.8"


def fetch(url: str, cookies: dict[str, str] | None = None, user_agent: str | None = None) -> FetchResult:
    headers = {"Accept-Language": ACCEPT_LANGUAGE}
    if user_agent:
        headers["User-Agent"] = user_agent
    try:
        resp = cr.get(url, impersonate="chrome", headers=headers, cookies=cookies or None,
                      timeout=TIMEOUT_SEC, allow_redirects=True)
    except Exception as e:  # curl_cffi는 다양한 예외를 던지므로 한 곳에서 감쌉니다.
        raise FetchError(f"request 연결 실패: {e}") from e

    return FetchResult(
        html=resp.text,
        status=resp.status_code,
        cookies=dict(resp.cookies),
        user_agent=user_agent,
    )
