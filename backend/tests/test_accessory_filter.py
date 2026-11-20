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


def test_DB_점검에서_잘못_걸렸던_본품():
    """scripts/audit_prices.py가 소모품으로 잘못 잡았던 실제 상품 이름"""
    real = [
        ("삼성전자 AI Q9000 AF60F17D11GRS", 1475000),
        ("삼성전자 뮤직 스튜디오5 HW-LS50H/ LS51H", 392660),
        ("삼성전자 3.1.2ch 사운드바 Q600H HW-Q600H/KR", 699000),
        ("창홍 스마트TV 4K CH431UHD Google M9GPW1 120Hz 구글 5", 419000),
        ("삼성전자 비스포크 AI DW80H73Y1UZ + NZ63DB607CFH", 1499000),
        ("삼성전자 비스포크 키친핏 RR70H39G10 + RZ70H32UN0 + RQ70H32S10", 2609000),
        ("LG전자 오브제컬렉션 컨버터블 X323MEF + Y323MEF + Z323MEF", 2436470),
        ("다이슨 에어랩 오리진+ 멀티 스타일러 앤 드라이어 + 라운드볼륨브러쉬", 421700),
        ("제우스 빔프로젝터 4K 오토 단초점 가정용 ZEUS L1300+전용가방", 339000),
        ("[예약판매]삼성 비스포크 식기세척기 인덕션세트 14인용+3구 DW80H73 NZ63DB607CFH", 2099000),
        ("루니스 히팅패드 4면 D1905Q", 47900),
        ("신일 전기히터 사무실 발난로 파티션히터 다리 온열기 접이식 난로 히팅패드", 57900),
        ("LG전자 휘센 오브제컬렉션 듀얼호스 PQ08FDWBS", 791540),
        ("신일 선풍기 아기 무소음 스탠드형 거실 리모컨", 99000),
        ("스탠드 선풍기 가정용 저소음 아기방 리모컨 초미풍 5엽 35cm", 49700),
        ("한경희 저소음 스탠드 선풍기 가정용 거실 사무실 원룸 리모컨 발터치 14인치", 39900),
        ("삼성 사운드바 9.1.4ch HW-Q930H/KR Q 시리즈 고품질 사운드", 1390000),
    ]
    for name, price in real:
        assert not is_accessory(name, price), name


def test_진짜_소모품은_여전히_거른다():
    assert is_accessory("로보락 S7 MaxV Ultra, S8 Plus, S8 Pro Ultra 호환 더스트백", 7150)
    assert is_accessory("로보락 S9 MaxV Ultra 전용 울트라도크 거름망", 8300)
    assert is_accessory("로보락 S9 MaxV Ultra 호환 물걸레 + 사이드 물걸레 세트", 23410)
    assert is_accessory("신일 선풍기 리모컨", 9900)          # 품목 이름이 있어도 싸고 리모컨으로 끝남
    assert is_accessory("에어컨 필터 1+1", 12000)
