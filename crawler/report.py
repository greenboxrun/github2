"""콘솔에 찍는 사이트별 결과 표."""

from .models import SiteReport

_WIDTH = 94


def print_table(reports: list[SiteReport]) -> None:
    print()
    print(f"{'site':<12}{'status':<8}{'start':<14}{'tier':<16}{'posts':>6}{'sec':>7}  error")
    print("-" * _WIDTH)
    for r in reports:
        err = r.error or ""
        if r.debug_html:
            err += f" ({r.debug_html})"
        print(f"{r.site:<12}{r.status:<8}{r.start:<14}{(r.tier or '-'):<16}{r.posts:>6}{r.seconds:>7}  {err}")
    ok = sum(r.status == "OK" for r in reports)
    print("-" * _WIDTH)
    print(f"성공 {ok} / 전체 {len(reports)}")
