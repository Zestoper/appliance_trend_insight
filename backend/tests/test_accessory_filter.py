"""앱 AccessoryFilterTest.java와 같은 사례로 서버 필터를 확인한다. 실행: cd backend && python -m pytest tests/test_accessory_filter.py"""
from app.utils.accessory_filter import (
    is_accessory, last_meaningful_word, distinct_model_count, looks_like_model,
)


def test_강한_신호():
    assert is_accessory("FQ18D7 호환 에어컨 필터 2개입")
    assert is_accessory("삼성 무풍 에어컨 교체용 극세필터")
    assert is_accessory("AX034 공기청정기 정품필터")


def test_본품_이름이_없는_소모품():
    assert is_accessory("FQ18D7DWAN 리모컨")
    assert is_accessory("FQ18D7 스탠드 커버 방진덮개")
    assert is_accessory("P70 물걸레 패드 10매")


def test_품목_이름이_있어도_에어컨_필터는_소모품():
    assert is_accessory("LG FQ19D7DWAN FQ18VCDRAN FQ18DBDNAN 스탠드 에어컨 극세 필터")
    assert is_accessory("LG 에어컨 스탠드 극세 필터 ABQ30198703")
    assert is_accessory("LG 정품 FQ18VCDRAN.AKOR FQ19D7DWAN.AKOR 에어컨 스탠드 극세 필터")


def test_소모품_단어로_끝나거나_싸면_소모품():
    assert is_accessory("삼성 에어컨 리모컨 2개입")
    assert is_accessory("삼성 에어컨 실외기 커버 FQ18", 19900)


def test_본품은_거르지_않는다():
    assert not is_accessory("삼성전자 비스포크 AI 무풍클래식 FQ18D7DWAN", 2590000)
    assert not is_accessory("LG전자 휘센 오브제컬렉션 FQ18HDKHA2", 2190000)
    assert not is_accessory("모바 P70 Pro Ultra 로봇청소기", 550900)
    assert not is_accessory("삼성 블루스카이 공기청정기 헤파필터 AX060", 459000)
    assert not is_accessory("LG전자 퓨리케어 360 AS354NS4A (AS354NS4AM)", 699000)


def test_도우미_규칙():
    assert last_meaningful_word("에어컨 스탠드 극세 필터 2개입") == "필터"
    assert distinct_model_count("LG FQ19D7DWAN FQ18VCDRAN FQ18DBDNAN 필터") == 3
    assert distinct_model_count("퓨리케어 AS354NS4A (AS354NS4AM)") == 1


def test_검색어가_모델명인지():
    assert looks_like_model("FQ18D7DWAN")
    assert looks_like_model("rf85c90d1ap")
    assert not looks_like_model("삼성 에어컨")
    assert not looks_like_model("220V")
