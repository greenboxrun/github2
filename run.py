"""커뮤니티 수집 진입점 — 이 파일 하나로 전체/일부 사이트를 실행하고 점검합니다.

    python run.py                       # 등록된 전체 사이트 수집
    python run.py fmkorea clien         # 일부만
    python run.py fmkorea --tier request   # 특정 단계만, 캐시 쿠키 없이 (디버깅)
    python run.py --test                # 테스트: 쿠키(세션 캐시) 초기화 후 start_tier부터 수집
    python run.py --test fmkorea        # 일부만 테스트
    python run.py --list                # 등록된 사이트 목록

끝나면 사이트별 결과 표를 출력하고 result/report.json 에 저장합니다. 실패가 있으면 종료코드 1.
"""

import argparse
import logging
import sys
import time

from crawler import storage
from crawler.fetch import session_cache
from crawler.fetch.browser import BrowserPool
from crawler.fetch.chain import ChainFailure, FetchChain
from crawler.fetch.types import Tier
from crawler.models import Post
from crawler.sites import SITES

log = logging.getLogger("run")


def crawl_site(site, chain: FetchChain, force: Tier | None) -> dict:
    t0 = time.perf_counter()
    row = {"site": site.name, "status": "FAIL", "start": site.start_tier.label, "tier": None, "posts": 0,
           "seconds": 0.0, "error": None, "debug_html": None, "attempts": []}
    posts: dict[str, Post] = {}
    try:
        for url in site.list_urls:  # 요청 간격은 chain 내부 throttle이 도메인별로 관리
            page_posts, _, attempts, _ = chain.run(site, url, force)
            row["attempts"] += [dict(a.to_dict(), url=url) for a in attempts]
            row["tier"] = attempts[-1].tier  # 성공한 시도의 표시 이름 (예: request+cookie)
            for p in page_posts:
                posts.setdefault(p.post_id, p)  # 여러 페이지에 걸친 중복 제거
        storage.save_site(site.name, list(posts.values()))
        row.update(status="OK", posts=len(posts))
    except ChainFailure as f:
        row["attempts"] += [a.to_dict() for a in f.attempts]
        row["error"] = str(f)
        if f.html:
            row["debug_html"] = str(storage.dump_debug(site.name, f.html).relative_to(storage.ROOT))
    except Exception as e:  # 사이트 코드의 예상 못 한 버그도 다른 사이트를 막지 않게
        log.exception("[%s] 예기치 못한 오류", site.name)
        row["error"] = f"{type(e).__name__}: {e}"
    row["seconds"] = round(time.perf_counter() - t0, 1)
    return row


def print_table(rows: list[dict]) -> None:
    print()
    print(f"{'site':<12}{'status':<8}{'start':<14}{'tier':<16}{'posts':>6}{'sec':>7}  error")
    print("-" * 94)
    for r in rows:
        err = r["error"] or ""
        if r["debug_html"]:
            err += f" ({r['debug_html']})"
        print(f"{r['site']:<12}{r['status']:<8}{r['start']:<14}{(r['tier'] or '-'):<16}{r['posts']:>6}{r['seconds']:>7}  {err}")
    ok = sum(r["status"] == "OK" for r in rows)
    print("-" * 94)
    print(f"성공 {ok} / 전체 {len(rows)}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows 콘솔 한글 깨짐 방지
        stream.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description="커뮤니티 게시물 수집기")
    ap.add_argument("sites", nargs="*", help="실행할 사이트 키 (생략 시 전체)")
    ap.add_argument("--tier", choices=[t.label for t in Tier], help="이 단계만, 캐시 쿠키 없이 사용")
    ap.add_argument("--test", action="store_true", help="쿠키(세션 캐시) 초기화 후 start_tier부터 수집")
    ap.add_argument("--list", action="store_true", help="등록된 사이트 목록")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    if args.list:
        for key, cls in SITES.items():
            print(f"{key:<12}{cls.display_name:<8}start={cls.start_tier.label:<13}{cls.list_urls[0]}")
        return 0

    unknown = [s for s in args.sites if s not in SITES]
    if unknown:
        print(f"알 수 없는 사이트: {unknown}. 등록된 사이트: {list(SITES)}", file=sys.stderr)
        return 2
    targets = [SITES[k]() for k in (args.sites or SITES)]

    if args.test:
        # 캐시 쿠키 덕분에 통과하는 것을 배제하고, 설정된 start_tier부터 실제로 수집되는지 확인
        for site in targets:
            session_cache.clear(site.name)
        log.info("세션 캐시 초기화: %s", ", ".join(s.name for s in targets))

    force = Tier.from_label(args.tier) if args.tier else None
    browser = BrowserPool()
    try:
        chain = FetchChain(browser)
        rows = [crawl_site(s, chain, force) for s in targets]
    finally:
        browser.close()

    storage.save_report(rows)
    path, total = storage.merge_all()
    print_table(rows)
    print(f"병합: {path.relative_to(storage.ROOT)} ({total}건), 리포트: {storage.REPORT_PATH.relative_to(storage.ROOT)}")
    return 0 if all(r["status"] == "OK" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
