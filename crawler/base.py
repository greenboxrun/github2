"""사이트 크롤러의 공통 부모 클래스.

사이트 파일(crawler/sites/<site>.py)은 이 클래스를 상속해 **설정값과 parse()만** 작성합니다.
네트워크 요청·단계 전환·재시도·저장은 전부 공통 코드(fetch/chain.py, storage.py)가 처리합니다.
"""

from abc import ABC, abstractmethod

from .errors import ValidationError
from .fetch.types import Tier
from .models import Post

# Cloudflare 등 흔한 차단/챌린지 페이지 문구. 사이트별로 block_markers에 추가 가능.
COMMON_BLOCK_MARKERS = [
    "Just a moment...",
    "cf-browser-verification",
    "challenge-platform",
    "Attention Required! | Cloudflare",
]

REQUIRED_FIELDS = ("post_id", "title", "url")


class BaseSite(ABC):
    name: str = ""                     # 사이트 키 = 파일명 = result/temp/<name>.json
    display_name: str = ""             # 사람이 읽는 이름 (예: "펨코")
    list_urls: list[str] = []          # 수집할 목록 페이지
    start_tier: Tier = Tier.REQUEST    # 확정적으로 막히는 사이트만 높여서 헛시도를 줄입니다
    min_posts: int = 5                 # 페이지당 이보다 적게 나오면 차단/구조 변경으로 판단
    block_markers: list[str] = []      # 사이트 전용 차단 페이지 문구
    request_delay: float = 3.0         # 같은 도메인 요청 사이 최소 간격(초). 실제로는 +30~100% 랜덤 지터

    @abstractmethod
    def parse(self, html: str, page_url: str) -> list[Post]:
        """목록 HTML → Post 리스트. 네트워크 접근 금지(순수 함수).

        셀렉터가 맞지 않으면 ParseError를 던지세요.
        """

    def all_block_markers(self) -> list[str]:
        return [*COMMON_BLOCK_MARKERS, *self.block_markers]

    def validate(self, posts: list[Post]) -> None:
        """parse() 결과가 정상인지 공통 검사. 이상하면 ValidationError."""
        self._check_count(posts)
        for post in posts:
            self._check_post(post)
        self._check_created_at(posts)

    def _check_count(self, posts: list[Post]) -> None:
        if len(posts) < self.min_posts:
            raise ValidationError(f"게시물 {len(posts)}건 (최소 {self.min_posts}건 필요)")

    def _check_post(self, post: Post) -> None:
        missing = [f for f in REQUIRED_FIELDS if not getattr(post, f)]
        if missing:
            raise ValidationError(f"필수값 누락 {missing}: {post}")
        if post.site != self.name:
            raise ValidationError(f"site 값 불일치: {post.site!r} != {self.name!r}")

    @staticmethod
    def _check_created_at(posts: list[Post]) -> None:
        if all(post.created_at is None for post in posts):
            raise ValidationError("created_at을 하나도 파싱하지 못함 (시각 형식 변경 의심)")
