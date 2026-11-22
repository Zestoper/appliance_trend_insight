"""상품명에 품목 이름 없이 라인 이름만 있어도 카테고리를 찾는다. 실행: python -m pytest tests/test_category_alias.py"""
import pytest

from app.config import _CATEGORY_MAP


def detect(text):
    for kw, cat in _CATEGORY_MAP.items():
        if kw in text:
            return cat
    return None


@pytest.mark.parametrize("name,cat", [
    ("삼성전자 비스포크 김치플러스 RQ33DG71J3EW", "냉장고"),
    ("위니아 딤채 스탠드형 WDQ57GTMRWS", "냉장고"),
    ("쿠쿠 김치톡톡 CRS-FWK0410W", "냉장고"),
    ("LG 디오스 김치냉장고 Z493MEE", "냉장고"),
    ("LG 휘센 제습기", "제습기"),   # 품목 이름이 있으면 그쪽이 먼저
])
def test_detect(name, cat):
    assert detect(name) == cat
