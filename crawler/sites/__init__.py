"""사이트 레지스트리. 새 사이트를 만들면 여기에 한 줄 등록하세요."""

from ..base import BaseSite
from .fmkorea import Fmkorea

SITES: dict[str, type[BaseSite]] = {
    cls.name: cls
    for cls in [
        Fmkorea,
        # Theqoo, Instiz, Humoruniv, Mlbpark, Ppomppu, Bobaedream, Inven, Slrclub, Cook82, Clien
    ]
}
