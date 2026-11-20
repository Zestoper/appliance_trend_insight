"""다나와 카테고리 거르기 테스트 (실제 다나와 응답에서 확인한 값). 실행: python -m pytest tests/test_danawa_category.py"""
from app.utils.danawa_category import in_category, is_accessory_category, is_appliance_category


def item(*cats):
    return {"categories": list(cats)}


ROBOROCK = item("생활가전", "청소기", "로봇청소기")
ROBOROCK_FILTER = item("생활가전", "청소기", "청소용품")
CARRIER_BAG = item("패션잡화", "여행가방", "캐리어")
CARRIER_SET = item("패션잡화", "가방", "캐리어/여행가방", "캐리어세트")
SSD = item("PC 주요 부품", "SSD", "내장형 SSD")
LAPTOP = item("디지털 완제품", "노트북", "삼성전자")
MICRO_SD = item("디카", "메모리/리더기", "메모리카드")
KIMCHI = item("주방가전", "김치냉장고", "뚜껑형")
NO_INFO = {"title": "예전 HTML 파싱 결과"}


def test_가전이_아닌_상품은_제외():
    for it in (CARRIER_BAG, CARRIER_SET, SSD, LAPTOP, MICRO_SD):
        assert not is_appliance_category(it)
    for it in (ROBOROCK, ROBOROCK_FILTER, KIMCHI, NO_INFO):
        assert is_appliance_category(it)


def test_소모품_카테고리():
    assert is_accessory_category(ROBOROCK_FILTER)
    assert not is_accessory_category(ROBOROCK)
    assert not is_accessory_category(KIMCHI)
    assert not is_accessory_category(NO_INFO)


def test_품목_카테고리():
    assert in_category(ROBOROCK, "로봇청소기")
    assert not in_category(ROBOROCK_FILTER, "로봇청소기")
    assert in_category(KIMCHI, "냉장고")
    assert not in_category(CARRIER_BAG, "에어컨")
    assert not in_category(SSD, "에어컨")
    assert in_category(NO_INFO, "에어컨")          # 정보가 없으면 판단하지 않음
    assert in_category(ROBOROCK, None)             # 품목을 안 받으면 판단하지 않음


def test_다나와_검색어에서_평수_떼기():
    from app.services.danawa_search import _danawa_query
    assert _danawa_query("캐리어 21평 에어컨") == "캐리어 에어컨"
    assert _danawa_query("21평 에어컨") == "에어컨"
    assert _danawa_query("삼성 18평형 스탠드 에어컨") == "삼성 스탠드 에어컨"
    assert _danawa_query("로보락 S9 MaxV Ultra") == "로보락 S9 MaxV Ultra"
    assert _danawa_query("21평") == "21평"     # 다 지워지면 원래 검색어
