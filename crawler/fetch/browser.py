"""2단계: Playwright 헤드리스 크로미움.

브라우저는 실행 1회에 한 번만 띄우고(lazy), 사이트마다 context를 따로 만들어 재사용합니다.
처음 쓰기 전에 `python -m playwright install chromium` 이 필요합니다.
"""

from ..errors import FetchError
from .types import FetchResult, Tier

TIMEOUT_MS = 30_000
SETTLE_MS = 1_500   # JS 렌더링 대기


class BrowserPool:
    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._contexts: dict[str, object] = {}

    def _ensure_browser(self):
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
        return self._browser

    def _context(self, site: str, cookies: dict[str, str] | None, user_agent: str | None, url: str):
        ctx = self._contexts.get(site)
        if ctx is None:
            kwargs = {"locale": "ko-KR"}
            if user_agent:
                kwargs["user_agent"] = user_agent
            ctx = self._ensure_browser().new_context(**kwargs)
            if cookies:
                ctx.add_cookies([{"name": k, "value": v, "url": url} for k, v in cookies.items()])
            self._contexts[site] = ctx
        return ctx

    def fetch(self, site: str, url: str, cookies: dict[str, str] | None = None,
              user_agent: str | None = None) -> FetchResult:
        try:
            ctx = self._context(site, cookies, user_agent, url)
            page = ctx.new_page()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                page.wait_for_timeout(SETTLE_MS)
                html = page.content()
                status = resp.status if resp else 0
                ua = page.evaluate("navigator.userAgent")
            finally:
                page.close()
            got_cookies = {c["name"]: c["value"] for c in ctx.cookies()}
        except Exception as e:
            first_line = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            raise FetchError(f"playwright 실패: {first_line}") from e
        return FetchResult(html=html, status=status, tier=Tier.PLAYWRIGHT, cookies=got_cookies, user_agent=ua)

    def close(self) -> None:
        for ctx in self._contexts.values():
            try:
                ctx.close()
            except Exception:
                pass
        self._contexts.clear()
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._pw:
            self._pw.stop()
            self._pw = None
