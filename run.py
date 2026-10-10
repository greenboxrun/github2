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

from crawler import storage
from crawler.fetch import session_cache
from crawler.fetch.types import Tier
from crawler.paths import REPORT_PATH, ROOT
from crawler.report import print_table
from crawler.runner import run_sites
from crawler.sites import SITES

log = logging.getLogger("run")


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="커뮤니티 게시물 수집기")
    ap.add_argument("sites", nargs="*", help="실행할 사이트 키 (생략 시 전체)")
    ap.add_argument("--tier", choices=[t.label for t in Tier], help="이 단계만, 캐시 쿠키 없이 사용")
    ap.add_argument("--test", action="store_true", help="쿠키(세션 캐시) 초기화 후 start_tier부터 수집")
    ap.add_argument("--list", action="store_true", help="등록된 사이트 목록")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args()


def _print_site_list() -> None:
    for key, cls in SITES.items():
        print(f"{key:<12}{cls.display_name:<8}start={cls.start_tier.label:<13}{cls.list_urls[0]}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows 콘솔 한글 깨짐 방지
        stream.reconfigure(encoding="utf-8")

    args = _parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")

    if args.list:
        _print_site_list()
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
    reports = run_sites(targets, force)

    storage.save_report([r.to_dict() for r in reports])
    path, total = storage.merge_all()
    print_table(reports)
    print(f"병합: {path.relative_to(ROOT)} ({total}건), 리포트: {REPORT_PATH.relative_to(ROOT)}")
    return 0 if all(r.status == "OK" for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
