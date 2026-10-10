"""커뮤니티 목록에 찍힌 시각·숫자 문자열을 공통 형식으로 바꾸는 헬퍼.

국내 커뮤니티는 전부 KST 기준으로 표시하므로, 여기서 UTC ISO8601로 변환합니다.
사이트 파일에서 시각/숫자를 직접 파싱하지 말고 반드시 이 함수들을 사용하세요.
"""

import re
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# 미래 시각으로 계산되면 하루 전으로 보정할 때의 허용 오차 (서버 시계 차이 대비)
_FUTURE_TOLERANCE = timedelta(minutes=10)


def now_kst() -> datetime:
    return datetime.now(KST)


def to_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_kst(text: str, now: datetime | None = None) -> str | None:
    """목록에 표시된 KST 시각 문자열을 UTC ISO8601로 변환합니다. 인식 못 하면 None.

    지원 형식:
        "16:46", "16:46:12"                 → 오늘 (미래면 어제)
        "2026.10.09", "26.10.09", "2026-10-09", "2026/10/09"  (+ 선택적 " 16:46[:12]")
        "10.09", "10-09", "10/09"           → 올해 (미래면 작년)
        "3분 전", "2시간 전", "1일 전", "방금"
    """
    if not text:
        return None
    s = text.strip()
    now = (now or now_kst()).astimezone(KST)

    if s in ("방금", "방금 전"):
        return to_utc_iso(now)

    m = re.fullmatch(r"(\d+)\s*(초|분|시간|일)\s*전", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        delta = {"초": timedelta(seconds=n), "분": timedelta(minutes=n),
                 "시간": timedelta(hours=n), "일": timedelta(days=n)}[unit]
        return to_utc_iso(now - delta)

    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if m:
        h, mi, sec = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        dt = now.replace(hour=h, minute=mi, second=sec, microsecond=0)
        if dt - now > _FUTURE_TOLERANCE:
            dt -= timedelta(days=1)
        return to_utc_iso(dt)

    m = re.fullmatch(r"(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})\.?(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?", s)
    if m:
        y = int(m.group(1))
        if y < 100:
            y += 2000
        dt = datetime(y, int(m.group(2)), int(m.group(3)),
                      int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0), tzinfo=KST)
        return to_utc_iso(dt)

    m = re.fullmatch(r"(\d{1,2})[.\-/](\d{1,2})\.?(?:\s+(\d{1,2}):(\d{2}))?", s)
    if m:
        dt = datetime(now.year, int(m.group(1)), int(m.group(2)),
                      int(m.group(3) or 0), int(m.group(4) or 0), tzinfo=KST)
        if dt - now > _FUTURE_TOLERANCE:
            dt = dt.replace(year=now.year - 1)
        return to_utc_iso(dt)

    return None


def parse_count(text: str | None) -> int | None:
    """ "1,234", "53만", "1.2만", "3.4k", "12" → 정수. 숫자가 없으면 None."""
    if text is None:
        return None
    s = text.strip().replace(",", "").replace(" ", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(만|천|[kK])?", s)
    if not m:
        return None
    num = float(m.group(1))
    mult = {"만": 10_000, "천": 1_000, "k": 1_000, "K": 1_000}.get(m.group(2) or "", 1)
    return int(round(num * mult))
