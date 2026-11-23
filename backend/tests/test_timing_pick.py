from app.routers.analysis import _is_rental, _pick_tracked

RENTAL = {"id": "9001", "title": "LG전자 LG 스탠바이미2 MAX 32인치 32LX6BPGA 사은품지급 60개월약정 월53700원", "price": 53700}
REAL = {"id": "122632760", "title": "LG전자 스탠바이미2 Max 32LX6BPGA", "price": 1278780}
OTHER = {"id": "555", "title": "LG전자 스탠바이미 27ART10", "price": 899000}


def test_rental_patterns():
    assert _is_rental(RENTAL["title"])
    assert _is_rental("삼성 비스포크 냉장고 월 32,900원 의무사용 5년")
    assert _is_rental("코웨이 정수기 월3만원")
    assert not _is_rental(REAL["title"])
    assert not _is_rental("LG 휘센 에어컨 24개월 무상AS")   # 보증 기간은 렌탈이 아니다


def test_same_id_wins():
    assert _pick_tracked([OTHER, REAL], "122632760", 1278780, set()) is REAL


def test_id_missing_picks_closest_price_not_history():
    # 제품 번호를 못 찾아도 이력 있는 다른 상품(OTHER)으로 넘어가지 않고 앱이 본 가격에 가장 가까운 상품
    real2 = {**REAL, "id": "abc"}
    assert _pick_tracked([OTHER, real2], "122632760", 1278780, {"555"}) is real2


def test_same_id_but_price_far_is_rejected():
    wrong = {**RENTAL, "id": "122632760"}
    assert _pick_tracked([wrong, REAL], "122632760", 1278780, set()) is REAL


def test_no_price_keeps_old_behavior():
    assert _pick_tracked([OTHER, REAL], None, 0, {"122632760"}) is REAL
    assert _pick_tracked([OTHER, REAL], None, 0, set()) is OTHER
