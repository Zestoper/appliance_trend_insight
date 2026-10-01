"""사용자 질문 → 구조화된 조건(카테고리·가격대·브랜드·가구·의도) 추출기.

LLM을 부르지 않고 정규식 + 별칭 사전 + 한글 자모 유사도만으로 처리한다.
  1) normalize      : 소문자 · 특수문자 정리 · 공백 제거본 생성
  2) 별칭 사전       : 에어콘→에어컨 · 로청→로봇청소기 같은 흔한 오타/줄임말 치환
  3) 자모 유사도     : 사전에 없는 오타(냉잔고)를 자모 편집거리로 가장 가까운 카테고리에 매칭
  4) 가격/가구/의도  : 정규식과 키워드 규칙
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# ── 카테고리 · 별칭 ───────────────────────────────────────────────

_FALLBACK_CATEGORIES = [
    "에어컨", "냉장고", "세탁기", "건조기", "공기청정기", "로봇청소기", "식기세척기",
    "TV", "에어프라이어", "전기밥솥", "전자레인지", "가습기", "제습기", "선풍기",
]

# 표준 카테고리명 → 사용자들이 실제로 쓰는 다른 표현 (오타·줄임말·영문)
CATEGORY_ALIASES: dict[str, list[str]] = {
    "에어컨": ["에어콘", "애어컨", "에어컨디셔너", "냉난방기", "벽걸이에어컨", "스탠드에어컨"],
    "냉장고": ["냉장구", "냉장꼬", "김치냉장고", "김냉"],
    "세탁기": ["세탁끼", "드럼세탁기", "통돌이"],
    "건조기": ["의류건조기", "건조끼"],
    "세탁건조기": ["워시콤보", "세탁건조기일체형", "올인원세탁기"],
    "공기청정기": ["공청기", "공기정화기", "공기청정"],
    "로봇청소기": ["로청", "로봇청소", "로보청소기", "로봇 청소기"],
    "식기세척기": ["식세기", "식기세척", "식척기"],
    "TV": ["티비", "tv", "텔레비전", "테레비", "티브이", "텔레비젼"],
    "에어프라이어": ["에어후라이어", "에어프라이기", "에프"],
    "전기밥솥": ["밥솥", "압력밥솥", "전기압력밥솥"],
    "전자레인지": ["전자렌지", "렌지"],
    "가습기": ["가습끼"],
    "제습기": ["제습끼"],
    "선풍기": ["써큘레이터", "서큘레이터"],
    "전기히터": ["히터", "온풍기"],
    "커피머신": ["커피메이커", "에스프레소머신", "캡슐커피"],
    "믹서기": ["블렌더", "믹서"],
    "전기포트": ["커피포트", "주전자"],
}

BRAND_ALIASES: dict[str, list[str]] = {
    "삼성": ["삼성", "samsung", "비스포크", "bespoke"],
    "LG": ["lg", "엘지", "오브제", "휘센", "트롬", "퓨리케어", "디오스", "코드제로"],
    "위니아": ["위니아", "딤채"],
    "캐리어": ["캐리어"],
    "쿠쿠": ["쿠쿠", "cuckoo"],
    "쿠첸": ["쿠첸"],
    "다이슨": ["다이슨", "dyson"],
    "로보락": ["로보락", "roborock"],
    "에코백스": ["에코백스", "ecovacs"],
    "드리미": ["드리미", "dreame"],
    "샤오미": ["샤오미", "xiaomi", "미지아"],
    "위닉스": ["위닉스", "winix"],
    "코웨이": ["코웨이", "coway"],
    "필립스": ["필립스", "philips"],
    "신일": ["신일"],
    "SK매직": ["sk매직", "에스케이매직"],
}


def _categories() -> list[str]:
    try:
        from app.config import CATEGORY_RULES
        cats = list(CATEGORY_RULES.keys())
        return cats or _FALLBACK_CATEGORIES
    except Exception:
        return _FALLBACK_CATEGORIES


# ── 한글 자모 분해 + 편집거리 (오타 대응) ─────────────────────────

_CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_JONG = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"


def to_jamo(text: str) -> str:
    """'냉장고' → 'ㄴㅐㅇㅈㅏㅇㄱㅗ' (한 글자 오타가 자모 1~2개 차이로 작아진다)"""
    out = []
    for ch in text:
        code = ord(ch) - 0xAC00
        if 0 <= code < 11172:
            out.append(_CHO[code // 588])
            out.append(_JUNG[(code % 588) // 28])
            jong = _JONG[code % 28]
            if jong != " ":
                out.append(jong)
        else:
            out.append(ch)
    return "".join(out)


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _similarity(a: str, b: str) -> float:
    ja, jb = to_jamo(a), to_jamo(b)
    longest = max(len(ja), len(jb)) or 1
    return 1 - _edit_distance(ja, jb) / longest


# ── 정규화 ────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """소문자 · 특수문자 정리 · 연속 공백 1칸 · 한자 제거"""
    text = text.lower().strip()
    text = re.sub(r"[一-鿿]", "", text)
    text = re.sub(r"[!?.·…\"'“”‘’()\[\]{}<>]", " ", text)   # ~ 는 가격 범위(30~50만원)에 쓰여서 남긴다
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _nospace(text: str) -> str:
    return re.sub(r"\s+", "", text)


# ── 카테고리 · 브랜드 찾기 ────────────────────────────────────────

def find_category(text: str) -> tuple[str | None, bool]:
    """(카테고리, 오타보정여부) 반환. 공백을 지운 문장에서 찾으므로 띄어쓰기는 무시된다."""
    ns = _nospace(text)
    cats = _categories()

    # 1) 정확히 포함 — 긴 이름부터 (세탁건조기가 세탁기보다 먼저 잡히도록)
    candidates: list[tuple[str, str]] = []
    for cat in cats:
        candidates.append((cat.lower().replace(" ", ""), cat))
        for alias in CATEGORY_ALIASES.get(cat, []):
            candidates.append((alias.lower().replace(" ", ""), cat))
    candidates.sort(key=lambda x: len(x[0]), reverse=True)
    for word, cat in candidates:
        if word and word in ns:
            return cat, False

    # 2) 오타 — 3글자 이상 이름만 자모 유사도로 비교 (짧은 단어는 오탐이 많다)
    best: tuple[float, str | None] = (0.0, None)
    for word, cat in candidates:
        n = len(word)
        if n < 3 or not re.search(r"[가-힣]", word):
            continue
        for size in (n - 1, n, n + 1):
            for i in range(0, max(len(ns) - size + 1, 0)):
                score = _similarity(ns[i:i + size], word)
                if score > best[0]:
                    best = (score, cat)
    if best[0] >= 0.8:
        return best[1], True
    return None, False


def find_brand(text: str) -> str | None:
    """'LG 말고 삼성은?'처럼 말고·빼고가 붙은 브랜드는 건너뛰고, 원하는 브랜드를 고른다."""
    ns = _nospace(text)
    found: list[tuple[int, str]] = []
    for brand, aliases in BRAND_ALIASES.items():
        for a in aliases:
            a = a.replace(" ", "")
            idx = ns.find(a)
            if idx == -1:
                continue
            after = ns[idx + len(a): idx + len(a) + 3]
            if re.match(r"(말고|빼고|제외|아닌)", after):
                continue
            found.append((idx, brand))
            break
    return min(found)[1] if found else None


def find_excluded_brand(text: str) -> str | None:
    """'삼성 빼고' · 'LG 말고' 처럼 빼달라는 브랜드"""
    ns = _nospace(text)
    for brand, aliases in BRAND_ALIASES.items():
        for a in aliases:
            if re.search(re.escape(a.replace(" ", "")) + r"(말고|빼고|제외|아닌)", ns):
                return brand
    return None


# ── 가격 ──────────────────────────────────────────────────────────

_KOR_DIGIT = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}
_KOR_UNIT = {"십": 10, "백": 100, "천": 1000}


def _kor_small(s: str) -> int | None:
    """'사십' → 40, '백오십' → 150, '천' → 1000 (만 단위 앞부분)"""
    if not s:
        return None
    total, cur = 0, 0
    for ch in s:
        if ch in _KOR_DIGIT:
            cur = _KOR_DIGIT[ch]
        elif ch in _KOR_UNIT:
            total += (cur or 1) * _KOR_UNIT[ch]
            cur = 0
        else:
            return None
    return total + cur


_NUM = r"\d+(?:\.\d+)?"


def _to_won(num: str, unit: str | None) -> int:
    n = float(num.replace(",", ""))
    if unit and unit.startswith("만"):
        return int(n * 10_000)
    if unit and unit.startswith("천"):
        return int(n * 1_000)
    return int(n)


def _replace_korean_numbers(text: str) -> str:
    """'사십만원' → '40만원' 처럼 한글 숫자를 아라비아 숫자로 바꿔 정규식이 잡게 한다."""
    def repl(m: re.Match) -> str:
        v = _kor_small(m.group(1))
        return f"{v}만" if v else m.group(0)
    return re.sub(r"([일이삼사오육칠팔구십백천]+)만", repl, text)


def extract_price(text: str) -> tuple[int | None, int | None]:
    """질문에서 (최소가, 최대가) 원 단위 추출. 없으면 (None, None).

    40만원짜리/정도/쯤   → 근처 ±15%
    40만원대             → 40만 ~ 49.9만
    40만원 이하/까지/안  → ~40만
    40만원 이상/넘는     → 40만 ~
    30~50만원            → 30만 ~ 50만
    """
    t = _replace_korean_numbers(text.replace(",", ""))
    t = re.sub(r"(\d)\s+(만|천|원)", r"\1\2", t)   # '40 만 원' → '40만원'
    t = re.sub(r"(만|천)\s+원", r"\1원", t)

    # 범위: 30~50만원 / 30만~50만원 / 30만원에서 50만원
    m = re.search(rf"({_NUM})\s*(만|천)?\s*원?\s*(?:~|-|에서|부터)\s*({_NUM})\s*(만원|만|천원|천|원)", t)
    if m:
        unit_hi = m.group(4)
        unit_lo = m.group(2) or unit_hi
        lo, hi = _to_won(m.group(1), unit_lo), _to_won(m.group(3), unit_hi)
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi

    m = re.search(rf"({_NUM})\s*(만원|만|천원|천|원)(대)?\s*(짜리|정도|쯤|내외|안팎|선|대)?\s*"
                  r"(이하|까지|안으로|안에서|안쪽|미만|아래|이내|밑|이상|넘는|넘게|초과|부터|위로)?", t)
    if not m:
        return None, None

    won = _to_won(m.group(1), m.group(2))
    if m.group(2) == "원" and won < 10_000:   # '3원' 같은 무의미한 값
        return None, None
    is_dae = bool(m.group(3)) or m.group(4) == "대"
    mod = m.group(5)

    if mod in ("이하", "까지", "안으로", "안에서", "안쪽", "미만", "아래", "이내", "밑"):
        return None, won
    if mod in ("이상", "넘는", "넘게", "초과", "부터", "위로"):
        return won, None
    if is_dae:
        step = 100_000 if won < 1_000_000 else 1_000_000
        return won, won + step
    return round(won * 0.85), round(won * 1.15)


# ── 가구 · 의도 ───────────────────────────────────────────────────

def extract_household(text: str) -> int | None:
    ns = _nospace(text)
    if re.search(r"혼자|자취|1인|일인|원룸|싱글|오피스텔", ns):
        return 1
    if re.search(r"신혼|2인|둘이|두명|부부|커플", ns):
        return 2
    m = re.search(r"([3-9])인(가구|가족)?", ns)
    if m:
        return int(m.group(1))
    if re.search(r"가족|애들|아이들|대가족", ns):
        return 4
    return None


_INTENT_RULES: list[tuple[str, str]] = [
    ("compare", r"vs|비교|차이|뭐가나|어떤게나|어느게나|중에뭐|중에어떤|둘중"),
    ("timing", r"언제|타이밍|시기|몇월|세일기간|할인기간|사는시기|살때"),
    # 전력효율·소음·디자인처럼 '특정 성능'을 묻는 질문도 상품 목록(템플릿)이 아니라 LLM 설명이 필요하다
    ("review", r"후기|리뷰|장단점|단점|장점|어때|어떰|괜찮아|쓸만|만족|불만|고장|소음|조용|전기세|전기요금|"
               r"전력|효율|에너지|등급|소비전력|절전|디자인|설치|기능|성능|내구성|용량|크기|사이즈"),
    ("recommend", r"추천|뭐사|뭘사|뭐살|골라|살까|사야|사고싶|가성비|좋은거|괜찮은거|입문"),
    ("price", r"얼마|가격|최저가|시세|싸게|저렴|할인"),
]


# 직전 상품에 대해 이어 묻는 걸로 볼 수 있는 표현
_FOLLOWUP_KW = (r"후기|리뷰|장단점|단점|장점|쓸만|고장|소음|조용|전기세|전기요금|용량|크기|사이즈|"
                r"전력|효율|에너지|등급|소비전력|절전|디자인|색상|설치|기능|성능|내구성|as|a/s|보증|"
                r"비교|차이|언제|타이밍|추천|다른거|다른제품|더싼|더저렴|싼거|저렴한거|비싼거|"
                r"좋은건|좋은걸|좋은거|나은건|나은거|괜찮은건|어떤게|어떤거|뭐가좋|제일|가장|1위|순위|"
                r"가격|얼마|최저가|그거|이거|저거|그중|그럼|이중|여기서")


# 직전에 보여준 상품을 기준으로 하는 상대 표현
_CHEAPER_KW = r"더싼|더저렴|싼거|싼걸|싼제품|저렴한거|저렴한걸|저렴한제품|가격낮은|더낮은|싸게나온|덜비싼"
_PRICIER_KW = r"더비싼|비싼거|비싼걸|고급|프리미엄|더좋은|상위모델|하이엔드|돈더"
_MORE_KW = r"다른거|다른걸|다른제품|다른모델|더보여|더추천|또있|더있|말고"


def detect_intent(text: str, has_price_range: bool) -> str:
    ns = _nospace(text)
    for intent, pattern in _INTENT_RULES:
        if re.search(pattern, ns):
            if intent == "price" and has_price_range:
                return "recommend"   # '40만원 이하 가격 냉장고' 는 사실상 추천 요청
            return intent
    return "recommend" if has_price_range else "other"


# ── 결과 ──────────────────────────────────────────────────────────

@dataclass
class QueryConditions:
    raw: str
    normalized: str
    category: str | None = None
    category_corrected: bool = False
    brand: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    household: int | None = None
    intent: str = "other"
    extras: dict = field(default_factory=dict)

    @property
    def is_structured(self) -> bool:
        """카테고리를 알아냈으면 조건 기반(템플릿/캐시)으로 처리할 수 있다."""
        return self.category is not None

    def cache_key(self, target: str) -> str:
        """표현이 달라도 조건이 같으면 같은 키 → 같은 캐시를 쓴다.
        단 조건만으로 답이 정해지는 추천·가격 질문만 조건 키를 쓴다. 비교·후기 같은 질문은
        '소음 후기'와 '고장 후기'처럼 조건이 같아도 묻는 게 달라서 질문 문장으로 키를 만든다."""
        if self.is_structured and self.intent in ("recommend", "price"):
            parts = [self.intent, self.category, self.brand or "-",
                     str(self.min_price or 0), str(self.max_price or 0), str(self.household or 0)]
            if self.extras.get("exclude_brand"):
                parts.append("nb" + self.extras["exclude_brand"])
            if self.extras.get("exclude"):
                import hashlib
                ex = "|".join(sorted(self.extras["exclude"]))
                parts.append("ex" + hashlib.md5(ex.encode("utf-8")).hexdigest()[:8])
            return f"chat:v1:{target}:" + ":".join(parts)
        return f"chat:v1:{target}:q:{_nospace(self.normalized)[:200]}"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_context(self) -> dict:
        """프론트에 돌려줬다가 다음 질문 때 다시 받는 '대화 맥락' (원문은 빼고 조건만)"""
        ctx = {k: getattr(self, k) for k in
               ("category", "brand", "min_price", "max_price", "household", "intent")}
        ctx["exclude_brand"] = self.extras.get("exclude_brand")
        return ctx


def _apply_relative(cond: QueryConditions, prev: dict, said_price: bool) -> None:
    """'더 싼 거' · '더 비싼 거' · '다른 거'를 직전에 보여준 상품 가격·목록 기준으로 바꾼다.
    prev에는 직전 답변의 shown_min / shown_max / shown_titles 가 들어 있다."""
    ns = _nospace(cond.normalized)
    shown = prev.get("shown_titles") or []
    relative = None
    if not said_price and re.search(_CHEAPER_KW, ns):
        relative = "cheaper"
        if prev.get("shown_min"):
            cond.min_price, cond.max_price = None, int(prev["shown_min"]) - 1
    elif not said_price and re.search(_PRICIER_KW, ns):
        relative = "pricier"
        if prev.get("shown_max"):
            cond.min_price, cond.max_price = int(prev["shown_max"]) + 1, None
    elif re.search(_MORE_KW, ns):
        relative = "more"
    if relative:
        cond.extras["relative"] = relative
        # '다른 거'는 지금까지 보여준 상품을 전부 빼고, '더 싼/비싼 거'는 가격 범위만 옮긴다
        cond.extras["exclude"] = shown if relative == "more" else []
        if cond.intent not in ("recommend", "price") or relative != "more":
            cond.intent = "recommend"


def parse_query(query: str, context: dict | None = None) -> QueryConditions:
    """context = 직전 질문에서 뽑은 조건. "100만원대는?"처럼 카테고리 없이 이어 묻는 질문은
    직전 조건(냉장고 · 3인)을 이어받고 새로 말한 것(가격)만 바꾼다."""
    norm = normalize(query)
    category, corrected = find_category(norm)
    lo, hi = extract_price(norm)
    cond = QueryConditions(
        raw=query,
        normalized=norm,
        category=category,
        category_corrected=corrected,
        brand=find_brand(norm),
        min_price=lo,
        max_price=hi,
        household=extract_household(norm),
        intent=detect_intent(norm, lo is not None or hi is not None),
    )

    prev = context or {}
    prev_cat = prev.get("category")
    is_followup = bool(prev_cat) and (cond.category is None or cond.category == prev_cat)
    if is_followup:
        # 가격·브랜드·가구를 새로 말했거나 '장단점·후기·비교·언제'처럼 상품에 대한 질문이면 이어 묻기로 본다.
        # '어때'처럼 아무 데나 붙는 말만 있으면("오늘 날씨 어때") 새 질문으로 본다.
        has_new_info = (lo is not None or hi is not None or cond.brand or cond.household
                        or find_excluded_brand(norm))
        product_question = re.search("|".join([_FOLLOWUP_KW, _CHEAPER_KW, _PRICIER_KW, _MORE_KW]), _nospace(norm))
        if cond.category or has_new_info or product_question:
            cond.extras["followup"] = cond.category is None
            # LLM으로 넘어갈 때 "앞에서 본 제품 중에 뭐가 나아?"에 답할 수 있게 직전 상품명을 넘긴다
            cond.extras["prev_shown"] = (prev.get("shown_titles") or [])[-3:]
            cond.category = cond.category or prev_cat
            excluded = find_excluded_brand(norm)
            if not excluded and not cond.brand:
                excluded = prev.get("exclude_brand")   # '삼성 빼고' 는 다음 질문에도 유지
            if excluded:
                cond.extras["exclude_brand"] = excluded
            if not cond.brand and prev.get("brand") != excluded:
                cond.brand = prev.get("brand")
            cond.household = cond.household or prev.get("household")
            if lo is None and hi is None:
                cond.min_price, cond.max_price = prev.get("min_price"), prev.get("max_price")
            if cond.intent == "other":
                cond.intent = prev.get("intent") if prev.get("intent") in ("recommend", "price") else "recommend"
            _apply_relative(cond, prev, lo is not None or hi is not None)

    # "3인 냉장고"처럼 카테고리만 말하고 의도가 없으면 추천으로 본다
    if cond.category and cond.intent == "other":
        cond.intent = "recommend"
    return cond
