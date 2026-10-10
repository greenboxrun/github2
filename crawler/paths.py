"""프로젝트 경로를 한곳에서 정의합니다. 결과·캐시 위치를 바꿀 때는 이 파일만 수정하세요."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "result"
TEMP_DIR = RESULT_DIR / "temp"             # 사이트별 결과 (<site>.json)
DEBUG_DIR = RESULT_DIR / "debug"           # 실패 시 받은 원본 HTML (<site>.html)
ALL_PATH = RESULT_DIR / "all.json"         # temp 전체 병합본
REPORT_PATH = RESULT_DIR / "report.json"   # 마지막 실행 리포트
SESSION_DIR = RESULT_DIR / ".cache" / "sessions"  # 사이트별 세션 캐시 (<site>.json)
