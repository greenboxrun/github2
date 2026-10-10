"""모든 사이트가 공통으로 반환하는 게시물 형식과, 실행 리포트의 사이트별 행."""

from dataclasses import asdict, dataclass, field


@dataclass
class Post:
    site: str                  # 사이트 키 (파일명과 동일, 예: "fmkorea")
    post_id: str               # 사이트 내부 글 번호
    title: str
    url: str                   # 절대 URL
    created_at: str | None     # UTC ISO8601, 예: "2026-10-10T03:12:00Z"
    comment_count: int | None
    view_count: int | None
    like_count: int | None     # 추천 기능이 없는 사이트는 None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SiteReport:
    """사이트 하나의 실행 결과. result/report.json 의 sites 항목 한 줄."""
    site: str
    status: str = "FAIL"                 # "OK" | "FAIL"
    start: str = ""                      # 설정된 start_tier 이름
    tier: str | None = None              # 성공한 단계 (예: "playwright", "request+cookie")
    posts: int = 0
    seconds: float = 0.0
    error: str | None = None
    debug_html: str | None = None        # 실패 시 원본 HTML 경로 (result/ 기준 상대 경로)
    attempts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
