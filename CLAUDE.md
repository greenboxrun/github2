# 커뮤니티 크롤링 취합기

국내 커뮤니티 인기글 목록을 공통 형식(`Post`)으로 수집해 JSON으로 저장한다.
사이트는 사용자와 **한 번에 하나씩** 추가한다.

## 대상 사이트 (키 = 파일명 = 결과 json 이름)
| 키 | 이름 | 상태 |
|---|---|---|
| fmkorea | 펨코 | ✅ best2 (start_tier=flaresolverr) |
| theqoo | 더쿠 | 예정 |
| instiz | 인티 | 예정 |
| humoruniv | 웃대 | 예정 |
| mlbpark | 엠팍 | 예정 |
| ppomppu | 뽐뿌 | 예정 |
| bobaedream | 보배 | 예정 |
| inven | 인벤 | 예정 |
| slrclub | SLR | 예정 |
| cook82 | 82쿡 | 예정 (파이썬 모듈명은 숫자로 시작 불가) |
| clien | 클량 | 예정 |

사이트를 추가하거나 URL/start_tier가 바뀌면 이 표도 갱신한다.

## 구조
```
run.py                     # 유일한 진입점: CLI 인자 처리 → runner 실행 → 저장·표 출력
crawler/
  paths.py                 # 프로젝트 경로 한곳 정의 (result/, 세션 캐시 등)
  models.py                # Post (공통 인터페이스), SiteReport (리포트 한 줄)
  base.py                  # BaseSite: 설정값 + parse() + 공통 validate()
  errors.py                # FetchError / ParseError / ValidationError
  timeutil.py              # parse_kst() KST→UTC, parse_count() "1.2만"→12000
  runner.py                # 사이트 단위 실행: 목록 URL 순회, 중복 제거, 사이트 간 예외 격리
  report.py                # 콘솔 결과 표
  storage.py               # result/ 아래 저장
  fetch/
    chain.py               # REQUEST → PLAYWRIGHT → FLARESOLVERR 단계 전환 (계획 → 시도 → 기억)
    types.py               # Tier (단계 enum), FetchResult
    http.py                # 1단계 curl_cffi (크롬 TLS 지문)
    browser.py             # 2단계 Playwright (실행당 브라우저 1개, 사이트별 context)
    flaresolverr.py        # 3단계 FlareSolverr (FLARESOLVERR_URL 환경변수로 주소 변경 가능)
    session_cache.py       # 쿠키+UA, 마지막 성공 단계 기억 (SessionState)
    throttle.py            # 도메인별 요청 간격 (request_delay + 30~100% 랜덤 지터)
  sites/
    __init__.py            # SITES 레지스트리
    <site>.py              # 사이트당 파일 하나
.github/workflows/crawl.yml  # 수동 실행 → 결과를 레포에 커밋 (FlareSolverr 서비스, 세션 캐시는 actions/cache)
result/                    # Actions가 커밋 (.cache/, debug/는 git 제외)
  temp/<site>.json         # 사이트별 결과. 성공 시 삭제 후 새로 저장, 실패 시 기존 파일 유지
  all.json                 # temp 전체 병합
  report.json              # 마지막 실행 리포트 (단계별 시도 내역 포함)
  debug/<site>.html        # 실패 시 받은 원본 HTML
  .cache/sessions/<site>.json
```

## 실행
```bash
pip install -r requirements.txt
python -m playwright install chromium
docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest

python run.py                        # 전체
python run.py fmkorea clien          # 일부
python run.py fmkorea --tier request # 특정 단계만, 캐시 쿠키 없이 (캐시 읽기/쓰기 안 함)
python run.py --test                 # 쿠키 초기화 후 start_tier부터 (아래 참고)
python run.py --list
```
종료코드: 전부 성공 0, 하나라도 실패 1.

## 테스트 (`python run.py --test`)
평소 수집은 캐시 쿠키 덕분에 통과할 수 있어서, 쿠키가 없을 때도 수집되는지는 보장하지 않는다.
테스트 모드는 **대상 사이트의 쿠키(세션 캐시)를 초기화한 뒤 평소와 똑같이** 실행한다.
- 각 사이트에 설정된 `start_tier`부터 시작해, 실패하면 더 무거운 단계로 넘어간다 (평소 체인과 동일)
- 결과(`result/temp`, `all.json`, `report.json`)와 새로 얻은 쿠키는 평소처럼 저장된다
- 표의 `start`(설정값)와 `tier`(실제 성공 단계)가 다르면 start_tier가 맞지 않는 것이다 → 조정
```
site        status  start         tier             posts    sec  error
fmkorea     OK      flaresolverr  flaresolverr        20   12.7
```
사이트를 추가·수정하면 반드시 `python run.py --test <site>`로 확인한다.

## 데이터 형식 (Post)
`site, post_id, title, url(절대), created_at(UTC ISO8601 "…Z"), comment_count, view_count, like_count`
- 목록 페이지에 없는 값은 `None`. 추천 없는 사이트는 `like_count=None`.
- **상세 페이지는 들어가지 않는다** (요청 수 폭증 → 차단 위험).
- 댓글 수 표시가 0일 때 아예 생략되는 사이트는 0으로 넣는다.

## 가져오기 체인 규칙
- 성공 조건: HTTP 200 + 차단 문구 없음 + `parse()`/`validate()` 통과. HTML이 와도 결과가 비면 다음 단계로.
- 브라우저 단계(Playwright/FlareSolverr)가 성공하면 쿠키+UA를 캐시 → 다음 실행은 REQUEST 단계에 실어 먼저 시도.
  (펨코: 1회차 FlareSolverr 15초 → 2회차 request 0.4초 확인)
  리포트·로그에는 캐시 쿠키를 쓴 요청이 `request+cookie`로 표시된다 (쿠키 없는 순수 request와 구분).
- 직전 성공 단계부터 시작하고, 10회마다 처음 단계부터 재확인.
- `start_tier`는 **실제로 막히는 걸 확인한 사이트만** 올린다. 확인 근거를 사이트 파일 docstring에 적는다.
- 같은 도메인 요청은 throttle이 간격을 둔다. 차단이 의심되면 해당 사이트 `request_delay`를 늘린다(기본 3초).

## 사이트 추가 절차
1. 대상 목록 URL을 사용자와 정한다 (보통 베스트/인기글 1페이지).
2. 실제 HTML을 받아 구조를 확인한다. 표 열 순서, 시각 형식, 숫자 형식(만/k/쉼표), 공지·광고 행 구분을 본다.
3. `crawler/sites/<site>.py` 작성 — `crawler/sites/fmkorea.py`를 템플릿으로. **처음엔 `start_tier`를 지정하지 않는다(기본 REQUEST).**
4. **단계 확인은 반드시 가벼운 순서로 하나씩**:
   ```bash
   python run.py <site> --tier request       # 1) 되면 여기서 끝, start_tier 기본값 유지
   python run.py <site> --tier playwright    # 2) 1이 막힐 때만. 되면 start_tier = Tier.PLAYWRIGHT
   python run.py <site> --tier flaresolverr  # 3) 2도 막힐 때만. 되면 start_tier = Tier.FLARESOLVERR
   ```
   - 앞 단계 실패 원인(HTTP 코드, 차단 문구, 빈 결과)을 docstring에 기록하고 다음 단계로 넘어간다.
   - 앞 단계를 확인하지 않고 바로 Playwright/FlareSolverr를 쓰지 않는다 (리소스 낭비).
   - start_tier를 올려도 체인은 쿠키 캐시로 REQUEST를 먼저 시도하므로, 실제 운영은 가능한 한 가벼운 단계로 돈다.
   - 이어서 `--tier` 없이 `python run.py <site>`를 2번 실행해 2회차에 더 가벼운 단계(보통 request)로 내려가는지 확인한다.

   사이트 파일 작성 규칙:
   - docstring: 대상 URL 설명, start_tier 근거, 열 순서, 특이사항
   - 셀렉터는 파일 상단 `SEL_*` 상수로 모은다 (구조 바뀌면 여기만 수정)
   - `parse()`는 순수 함수: 네트워크 접근 금지, 셀렉터 불일치 시 `ParseError`
   - 시각은 `parse_kst()`, 숫자는 `parse_count()`만 사용. 지원 안 되는 형식이면 timeutil에 추가
   - `url`은 가능한 짧은 정식 주소(글 번호 기반)로 만든다
5. `crawler/sites/__init__.py`의 리스트에 클래스 등록.
6. `python run.py <site>` 로 실제 수집 확인 → `result/temp/<site>.json` 값을 사람이 눈으로 검증 (시각 UTC 변환, 조회/추천 열 뒤바뀜 여부).
7. 위 사이트 표 갱신.

테스트용 fixture(저장된 HTML)는 쓰지 않는다. 크롤링은 항상 실시간 데이터로 검증한다.

## 유지보수 흐름
1. `python run.py --test` → FAIL 사이트, 그리고 start와 tier가 다른 사이트 확인.
2. error 열의 예외 종류로 원인 위치 판단:
   - `FetchError` → 차단/타임아웃/FlareSolverr 꺼짐. `report.json`의 attempts로 단계별 결과 확인, 필요하면 start_tier·request_delay 조정
   - `ParseError` → 셀렉터 불일치. `result/debug/<site>.html`을 열어 `SEL_*` 수정
   - `ValidationError` → 건수 부족·필수값 누락·시각 파싱 전부 실패. parse() 로직이나 timeutil 확인
3. 수정 후 `python run.py --test <site>`로 재확인.

## 코드 규칙
- 사이트 파일에는 설정값과 parse()만. 네트워크·재시도·저장 로직은 공통 모듈에.
- 한 사이트의 예외가 다른 사이트 실행을 막으면 안 된다 (run.py에서 사이트 단위로 격리).
- 주석·로그·에러 메시지는 한국어.
