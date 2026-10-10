"""커뮤니티 목록에 찍힌 시각·숫자 문자열을 공통 형식으로 바꾸는 헬퍼.

국내 커뮤니티는 전부 KST 기준으로 표시하므로, 여기서 UTC ISO8601로 변환합니다.
사이트 파일에서 시각/숫자를 직접 파싱하지 말고 반드시 이 함수들을 사용하세요.
"""

import re
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# 미래 시각으로 계산되면 하루 전으로 보정할 때의 허용 오차 (서버 시계 차이 대비)
_FUTURE_TOLERANCE = timedelta(minutes=10)

_JUST_NOW = ("방금", "방금 전")
_RELATIVE_RE = re.compile(r"(\d+)\s*(초|분|시간|일)\s*전")
_RELATIVE_UNIT_SECONDS = {"초": 1, "분": 60, "시간": 3600, "일": 86400}
_CLOCK_RE = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?")
_FULL_DATE_RE = re.compile(r"(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})\.?(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?")
_SHORT_DATE_RE = re.compile(r"(\d{1,2})[.\-/](\d{1,2})\.?(?:\s+(\d{1,2}):(\d{2}))?")
_COUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(만|천|[kK])?")
_COUNT_UNIT = {"만": 10_000, "천": 1_000, "k": 1_000, "K": 1_000}


def now_kst() -> datetime:
    return datetime.now(KST)


def to_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_utc_iso() -> str:
    return to_utc_iso(datetime.now(timezone.utc))


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
    for parse_one in (_just_now, _relative, _clock, _full_date, _short_date):
        dt = parse_one(s, now)
        if dt is not None:
            return to_utc_iso(dt)
    return None


def _just_now(s: str, now: datetime) -> datetime | None:
    return now if s in _JUST_NOW else None


def _relative(s: str, now: datetime) -> datetime | None:
    m = _RELATIVE_RE.fullmatch(s)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    return now - timedelta(seconds=n * _RELATIVE_UNIT_SECONDS[unit])


def _clock(s: str, now: datetime) -> datetime | None:
    m = _CLOCK_RE.fullmatch(s)
    if not m:
        return None
    h, mi, sec = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    dt = now.replace(hour=h, minute=mi, second=sec, microsecond=0)
    if dt - now > _FUTURE_TOLERANCE:
        dt -= timedelta(days=1)
    return dt


def _full_date(s: str, now: datetime) -> datetime | None:
    m = _FULL_DATE_RE.fullmatch(s)
    if not m:
        return None
    y = int(m.group(1))
    if y < 100:
        y += 2000
    return datetime(y, int(m.group(2)), int(m.group(3)),
                    int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0), tzinfo=KST)


def _short_date(s: str, now: datetime) -> datetime | None:
    m = _SHORT_DATE_RE.fullmatch(s)
    if not m:
        return None
    dt = datetime(now.year, int(m.group(1)), int(m.group(2)),
                  int(m.group(3) or 0), int(m.group(4) or 0), tzinfo=KST)
    if dt - now > _FUTURE_TOLERANCE:
        dt = dt.replace(year=now.year - 1)
    return dt


def parse_count(text: str | None) -> int | None:
    """ "1,234", "53만", "1.2만", "3.4k", "12" → 정수. 숫자가 없으면 None."""
    if text is None:
        return None
    s = text.strip().replace(",", "").replace(" ", "")
    m = _COUNT_RE.search(s)
    if not m:
        return None
    num = float(m.group(1))
    mult = _COUNT_UNIT.get(m.group(2) or "", 1)
    return int(round(num * mult))
