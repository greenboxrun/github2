"""펨코 (fmkorea) — 포텐 터짐 화제순(best2) 목록.

- 단계 확인 (2026-10-10): request → HTTP 430, playwright(헤드리스) → HTTP 430, flaresolverr → 성공.
  그래서 start_tier = FLARESOLVERR.
  FlareSolverr가 얻은 쿠키+UA를 캐시하면 다음 실행부터 request 단계로 통과됩니다 (15.7초 → 0.3초).
- 목록의 시각 열은 '터진날짜'(포텐 간 시각)라 실제 작성 시각과 다를 수 있습니다.
- 표 열 순서: 대상 게시판 | 제목 | 글쓴이 | 터진날짜 | 조회 | 추천
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from ..base import BaseSite
from ..errors import ParseError
from ..fetch.types import Tier
from ..models import Post
from ..timeutil import parse_count, parse_kst

BASE_URL = "https://www.fmkorea.com"

# 셀렉터 — 구조가 바뀌면 여기만 고치세요
SEL_ROW = "table tbody tr:not(.notice)"
SEL_TITLE = "td.title a.hx"
SEL_COMMENT = "td.title a.replyNum"
SEL_TIME = "td.time"
SEL_VIEW = "td.m_no:not(.m_no_voted)"
SEL_LIKE = "td.m_no.m_no_voted"
RE_DOC_ID = re.compile(r"document_srl=(\d+)")


class Fmkorea(BaseSite):
    name = "fmkorea"
    display_name = "펨코"
    list_urls = ["https://www.fmkorea.com/index.php?mid=best2&listStyle=list"]
    start_tier = Tier.FLARESOLVERR
    min_posts = 10

    def parse(self, html: str, page_url: str) -> list[Post]:
        rows = BeautifulSoup(html, "html.parser").select(SEL_ROW)
        if not rows:
            raise ParseError(f"목록 행 없음 ({SEL_ROW})")

        posts = []
        for tr in rows:
            post = self._to_post(tr)
            if post is not None:
                posts.append(post)
        return posts

    def _to_post(self, tr: Tag) -> Post | None:
        link = tr.select_one(SEL_TITLE)
        if not link:
            return None  # 광고/구분 행

        m = RE_DOC_ID.search(link.get("href", ""))
        if not m:
            raise ParseError(f"document_srl 없음: {link.get('href')}")
        doc_id = m.group(1)

        comment = tr.select_one(SEL_COMMENT)
        time_cell = tr.select_one(SEL_TIME)
        view = tr.select_one(SEL_VIEW)
        like = tr.select_one(SEL_LIKE)
        return Post(
            site=self.name,
            post_id=doc_id,
            title=link.get_text(strip=True),
            url=urljoin(BASE_URL, f"/{doc_id}"),
            created_at=parse_kst(time_cell.get_text(strip=True)) if time_cell else None,
            # 댓글이 0개면 replyNum 링크 자체가 없습니다.
            comment_count=parse_count(comment.get_text()) if comment else 0,
            view_count=parse_count(view.get_text()) if view else None,
            like_count=parse_count(like.get_text()) if like else None,
        )
