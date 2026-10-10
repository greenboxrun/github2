"""수집 실패 원인을 단계별로 구분하는 예외.

리포트의 error 열에 클래스 이름이 그대로 찍히므로, 어디를 고쳐야 하는지 바로 알 수 있습니다.
- FetchError      : HTML을 못 받음 (차단, 타임아웃, FlareSolverr 꺼짐 등) → fetch/ 또는 start_tier 확인
- ParseError      : HTML은 받았는데 셀렉터가 안 맞음 → sites/<site>.py 셀렉터 확인
- ValidationError : 파싱은 됐지만 결과가 이상함 (건수 부족, 필수값 누락) → parse() 로직 확인
"""


class CrawlError(Exception):
    pass


class FetchError(CrawlError):
    pass


class ParseError(CrawlError):
    pass


class ValidationError(CrawlError):
    pass
