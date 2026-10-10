"""사이트 단위 실행: 목록 URL들을 순회해 게시물을 모으고 SiteReport로 정리합니다.

단계 전환은 fetch/chain.py, 저장은 storage.py가 맡고 여기서는 사이트 경계에서 예외를 격리합니다.
한 사이트의 예외가 다른 사이트 실행을 막지 않도록 여기서 모두 잡습니다.
"""

import logging
import time
from collections.abc import Iterable

from . import storage
from .base import BaseSite
from .fetch.browser import BrowserPool
from .fetch.chain import ChainFailure, FetchChain
from .fetch.types import Tier
from .models import Post, SiteReport
from .paths import ROOT

log = logging.getLogger(__name__)


def run_sites(sites: Iterable[BaseSite], force: Tier | None) -> list[SiteReport]:
    """사이트들을 차례로 수집합니다. 브라우저는 실행 1회에 하나만 띄웠다가 끝나면 닫습니다."""
    browser = BrowserPool()
    try:
        chain = FetchChain(browser)
        return [crawl_site(site, chain, force) for site in sites]
    finally:
        browser.close()


def crawl_site(site: BaseSite, chain: FetchChain, force: Tier | None) -> SiteReport:
    t0 = time.perf_counter()
    report = SiteReport(site=site.name, start=site.start_tier.label)
    posts: dict[str, Post] = {}
    try:
        for url in site.list_urls:  # 요청 간격은 chain 내부 throttle이 도메인별로 관리
            page = chain.run(site, url, force)
            report.attempts += [{**a.to_dict(), "url": url} for a in page.attempts]
            report.tier = page.attempts[-1].tier
            for p in page.posts:
                posts.setdefault(p.post_id, p)  # 여러 페이지에 걸친 중복 제거
        storage.save_site(site.name, list(posts.values()))
        report.status, report.posts = "OK", len(posts)
    except ChainFailure as f:
        report.attempts += [a.to_dict() for a in f.attempts]
        report.error = str(f)
        if f.html:
            report.debug_html = str(storage.dump_debug(site.name, f.html).relative_to(ROOT))
    except Exception as e:  # 사이트 코드의 예상 못 한 버그도 다른 사이트를 막지 않게
        log.exception("[%s] 예기치 못한 오류", site.name)
        report.error = f"{type(e).__name__}: {e}"
    report.seconds = round(time.perf_counter() - t0, 1)
    return report
