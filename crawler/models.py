"""모든 사이트가 공통으로 반환하는 게시물 형식."""

from dataclasses import asdict, dataclass


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
