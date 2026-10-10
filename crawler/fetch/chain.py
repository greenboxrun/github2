"""단계별 가져오기 체인: REQUEST → PLAYWRIGHT → FLARESOLVERR.

각 단계는 "HTTP 200 + 차단 문구 없음 + parse/validate 통과"여야 성공으로 인정합니다.
HTML이 와도 파싱 결과가 비면(JS 렌더링, 챌린지 페이지) 다음 단계로 넘어갑니다.

효율화:
1. 캐시된 쿠키+UA가 있으면 REQUEST 단계에 실어 보냄 (FlareSolverr 결과 재사용)
2. 직전에 성공한 단계부터 시작. RECHECK_EVERY회마다 처음 단계부터 다시 시도
"""

import logging
import time
from dataclasses import asdict, dataclass, field

from ..base import BaseSite
from ..errors import CrawlError, FetchError, ParseError, ValidationError
from ..models import Post
from . import flaresolverr, http, session_cache, throttle
from .browser import BrowserPool
from .session_cache import SessionState
from .types import FetchResult, Tier

log = logging.getLogger(__name__)

RECHECK_EVERY = 10
# 리포트에 대표로 보여줄 오류 우선순위: HTML을 받아 파싱까지 간 오류가 더 고칠 단서가 많음
_ERROR_RANK = {FetchError: 0, ParseError: 1, ValidationError: 2}


@dataclass
class Attempt:
    tier: str                  # 단계 이름 (캐시 쿠키를 실은 REQUEST는 "request+cookie")
    ok: bool
    seconds: float
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageResult:
    """url 하나를 성공적으로 가져온 결과. attempts의 마지막 원소가 성공한 시도입니다."""
    posts: list[Post]
    attempts: list[Attempt]


@dataclass
class ChainFailure(Exception):
    """모든 단계 실패. 가장 '진척된' 오류와 그때의 HTML을 담습니다."""
    error: CrawlError
    attempts: list[Attempt] = field(default_factory=list)
    html: str | None = None

    def __str__(self) -> str:
        return f"{type(self.error).__name__}: {self.error}"


def plan_tiers(start: Tier, state: SessionState, force: Tier | None) -> list[Tier]:
    """이번 실행에서 시도할 단계 순서."""
    if force:
        return [force]
    last = state.last_tier_enum
    if last and last > start and state.runs_since_reset < RECHECK_EVERY:
        start = last
    plan = [t for t in Tier if t >= start]
    # 캐시된 쿠키가 있으면 시작 단계와 관계없이 가벼운 REQUEST를 먼저 한 번 시도
    if state.cookies and Tier.REQUEST not in plan:
        plan.insert(0, Tier.REQUEST)
    return plan


def check_response(site: BaseSite, res: FetchResult) -> None:
    if res.status != 200:
        raise FetchError(f"HTTP {res.status}")
    for marker in site.all_block_markers():
        if marker in res.html:
            raise FetchError(f"차단 페이지 감지: {marker!r}")


def attempt_label(tier: Tier, state: SessionState) -> str:
    # 캐시 쿠키를 실어 보낸 REQUEST는 리포트에서 구분되게 표시
    return "request+cookie" if tier is Tier.REQUEST and state.cookies else tier.label


def skipped_by_memory(start: Tier, plan: list[Tier], tier: Tier) -> bool:
    """성공한 단계(tier)보다 가벼운 단계 중 기억값 때문에 건너뛴 게 있었는지."""
    return any(t not in plan for t in Tier if start <= t < tier)


class FetchChain:
    def __init__(self, browser: BrowserPool) -> None:
        self.browser = browser

    def run(self, site: BaseSite, url: str, force: Tier | None = None) -> PageResult:
        """url 하나를 단계별로 시도해 첫 성공 결과를 돌려줍니다. 전부 실패하면 ChainFailure.

        force를 주면 그 단계만, 캐시된 쿠키 없이 깨끗한 상태로 시도하고 캐시도 갱신하지 않습니다.
        (테스트·디버깅에서 "그 단계만으로 진짜 되는지"를 보기 위함)
        """
        state = SessionState() if force else session_cache.load(site.name)
        plan = plan_tiers(site.start_tier, state, force)
        attempts: list[Attempt] = []
        best: tuple[CrawlError, str | None] | None = None

        for tier in plan:
            label = attempt_label(tier, state)
            t0 = time.perf_counter()
            html = None
            try:
                res = self._fetch(tier, site, url, state)
                html = res.html
                check_response(site, res)
                posts = site.parse(res.html, url)
                site.validate(posts)
            except CrawlError as e:
                sec = time.perf_counter() - t0
                attempts.append(Attempt(label, False, round(sec, 2), f"{type(e).__name__}: {e}"))
                log.warning("[%s] %s 실패 (%.1fs): %s", site.name, label, sec, e)
                if best is None or _ERROR_RANK[type(e)] >= _ERROR_RANK[type(best[0])]:
                    best = (e, html)
                # 캐시 쿠키로 시도한 REQUEST가 실패하면 쿠키가 만료된 것일 수 있으므로 비웁니다.
                if tier is Tier.REQUEST and state.cookies:
                    state.forget_cookies()
                continue

            sec = time.perf_counter() - t0
            attempts.append(Attempt(label, True, round(sec, 2)))
            log.info("[%s] %s 성공 (%.1fs, %d건)", site.name, label, sec, len(posts))
            if not force:
                self._remember_success(site, state, res, tier, plan)
            return PageResult(posts, attempts)

        if not force:
            # 전부 실패 → 다음엔 처음부터 다시 시도하도록 기억값 초기화
            state.reset_memory()
            session_cache.save(site.name, state)
        err, html = best
        raise ChainFailure(err, attempts, html)

    def _fetch(self, tier: Tier, site: BaseSite, url: str, state: SessionState) -> FetchResult:
        throttle.wait(url, site.request_delay)
        if tier is Tier.REQUEST:
            return http.fetch(url, cookies=state.cookies, user_agent=state.user_agent)
        if tier is Tier.PLAYWRIGHT:
            return self.browser.fetch(site.name, url, cookies=state.cookies, user_agent=state.user_agent)
        return flaresolverr.fetch(url)

    @staticmethod
    def _remember_success(site: BaseSite, state: SessionState, res: FetchResult,
                          tier: Tier, plan: list[Tier]) -> None:
        # 브라우저 단계에서 얻은 쿠키+UA는 다음 REQUEST 단계에서 재사용
        if tier is not Tier.REQUEST and res.cookies:
            state.cookies, state.user_agent = res.cookies, res.user_agent
        state.remember_success(tier, skipped_by_memory(site.start_tier, plan, tier))
        session_cache.save(site.name, state)
