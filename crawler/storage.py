"""결과 파일 저장.

result/temp/<site>.json : 사이트별 결과. 성공할 때마다 기존 파일을 지우고 새로 저장.
                          실패하면 건드리지 않아 직전 정상 데이터가 남습니다.
result/all.json         : temp/*.json 전체 병합본
result/report.json      : 마지막 실행의 사이트별 성공/실패 리포트
result/debug/<site>.html: 실패했을 때 받아온 원본 HTML
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Post

ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "result"
TEMP_DIR = RESULT_DIR / "temp"
DEBUG_DIR = RESULT_DIR / "debug"
ALL_PATH = RESULT_DIR / "all.json"
REPORT_PATH = RESULT_DIR / "report.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_site(site: str, posts: list[Post]) -> Path:
    path = TEMP_DIR / f"{site}.json"
    _write_json(path, {
        "site": site,
        "collected_at": _utc_now(),
        "count": len(posts),
        "posts": [p.to_dict() for p in posts],
    })
    return path


def merge_all() -> tuple[Path, int]:
    """temp 폴더의 사이트별 결과를 하나로 합칩니다."""
    posts, sites = [], {}
    for f in sorted(TEMP_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        sites[data["site"]] = {"collected_at": data["collected_at"], "count": data["count"]}
        posts.extend(data["posts"])
    _write_json(ALL_PATH, {"merged_at": _utc_now(), "count": len(posts), "sites": sites, "posts": posts})
    return ALL_PATH, len(posts)


def save_report(rows: list[dict]) -> Path:
    _write_json(REPORT_PATH, {"run_at": _utc_now(), "sites": rows})
    return REPORT_PATH


def dump_debug(site: str, html: str) -> Path:
    path = DEBUG_DIR / f"{site}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path

