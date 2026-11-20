"""
모델명으로 검색했을 때 딸려 나오는 소모품 · 부속품을 거른다.
안드로이드 앱(gajeon-app)의 scan/AccessoryFilter.java · ModelNameExtractor.java와 같은 규칙이다.
서버로 옮겨서 웹과 앱이 같은 검색 결과를 받는다.

판단 규칙 (위에서부터 하나라도 맞으면 소모품)
  1) "호환 · 교체용 · 리필 · 정품필터 · 극세 필터" 같은 말이 있다
  2) 서로 다른 모델명이 2개 이상 있다 → "이 모델들에 맞는 부품" (본품 이름에는 자기 모델명 하나)
  3) 제품명이 소모품 단어로 끝난다 (예: "… 스탠드 극세 필터", "… 리모컨 2개입")
     본품은 보통 모델명으로 끝난다 (예: "공기청정기 헤파필터 AX060")
  4) 5만 원 미만인데 소모품 단어가 있다
  5) 소모품 단어가 있고 제품명에 품목 이름(에어컨 등)이 없다
"""
import re

# 이 말이 있으면 거의 확실히 소모품
_STRONG = [
    "호환", "교체용", "교체 필터", "교체필터", "리필", "정품필터", "정품 필터",
    "대체용", "전용 필터", "전용필터", "극세 필터", "극세필터",
]

# 본품 이름에는 잘 안 들어가는 소모품 · 부속품 단어
_WEAK = [
    "필터", "커버", "덮개", "거치대", "받침대", "브라켓", "케이블", "리모컨", "호스",
    "부품", "소모품", "세정제", "세척제", "스티커", "패드", "걸레", "먼지봉투",
    "브러시", "브러쉬", "배터리", "어댑터", "노즐", "트레이",
]

# 품목 이름. 긴 이름을 먼저 검사해야 "세탁건조기"가 "건조기"로 잘못 잡히지 않는다
_CATEGORIES = [
    "세탁건조기", "블루투스 스피커", "헤어스타일러", "헤어드라이어", "공기청정기", "로봇청소기",
    "식기세척기", "에어프라이어", "전자레인지", "전기밥솥", "전기히터", "전기포트",
    "커피머신", "사운드바", "프로젝터", "에어컨", "냉장고", "세탁기", "건조기",
    "가습기", "제습기", "선풍기", "믹서기", "TV",
]

# 제품명 끝에 붙는 수량 표시: 2개입, 10매, 1EA, 3P, 세트, 1+1 …
_QUANTITY = re.compile(r"^(\d+(개입|개|매|EA|P|팩|세트|SET|롤|장)|세트|SET|\d\+\d|\(.*\)|\[.*\])$")
_CHEAP = 50000

# 모델명 판별 (ModelNameExtractor와 같음)
_ALLOWED = re.compile(r"^[A-Z0-9\-_/.]{5,20}$")
_UNIT_ONLY = re.compile(r"^[0-9.,/\-]+(V|HZ|KG|G|W|KW|KWH|L|ML|MM|CM|M|INCH|IN|DB|RPM|EA|P|K)$")
_DATE_LIKE = re.compile(r"^\d{2,4}[.\-/]\d{1,2}([.\-/]\d{1,2})?$")


def _normalize(raw: str) -> str:
    t = raw.strip().upper()
    t = re.sub(r"^[\-_/.]+|[\-_/.]+$", "", t)
    t = re.sub(r"^.*[가-힣]", "", t)      # "모델명AF17B6474"처럼 한글이 붙으면 뒤쪽만
    return t


def _is_model_like(t: str) -> bool:
    if not _ALLOWED.match(t):
        return False
    if not re.search(r"[A-Z]", t) or not re.search(r"[0-9]", t):
        return False
    if _UNIT_ONLY.match(t) or _DATE_LIKE.match(t):
        return False
    return not (t.startswith("HTTP") or t.startswith("WWW"))


def looks_like_model(text: str | None) -> bool:
    """검색어가 모델명처럼 생겼는지 (예: FQ18D7DWAN)."""
    return bool(text) and _is_model_like(_normalize(text))


def detect_category(text: str | None) -> str | None:
    if not text:
        return None
    return next((c for c in _CATEGORIES if c in text), None)


def _contains_weak(text: str) -> bool:
    return any(w in text for w in _WEAK)


def last_meaningful_word(upper_title: str) -> str:
    """수량 표시를 뗀 마지막 단어. 예: "에어컨 스탠드 극세 필터 2개입" → "필터" """
    for w in reversed(upper_title.strip().split()):
        if not _QUANTITY.match(w):
            return w
    return ""


def distinct_model_count(title: str) -> int:
    """제품명 속 서로 다른 모델명 개수. 앞 6글자가 같으면 같은 모델의 변형으로 본다."""
    prefixes: list[str] = []
    for raw in re.split(r"[\s()\[\]{},/]+", title):
        token = _normalize(raw)
        if not _is_model_like(token):
            continue
        prefix = token[:6]
        if prefix not in prefixes:
            prefixes.append(prefix)
    return len(prefixes)


def is_accessory(title: str | None, price: int = 0) -> bool:
    """price: 상품 가격 (모르면 0)"""
    if not title:
        return False
    t = title.upper()
    if any(w in t for w in _STRONG):                     # 1) 강한 신호
        return True
    if distinct_model_count(title) >= 2:                 # 2) 호환 모델명 나열
        return True
    if _contains_weak(last_meaningful_word(t)):          # 3) 소모품 단어로 끝남
        return True
    has_weak = _contains_weak(t)
    if has_weak and 0 < price < _CHEAP:                  # 4) 싼데 소모품 단어가 있음
        return True
    return has_weak and detect_category(title) is None   # 5) 소모품 단어가 있고 본품 이름이 없음
