import os
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

NAVER_SHOP_URL      = "https://openapi.naver.com/v1/search/shop.json"
NAVER_NEWS_URL      = "https://openapi.naver.com/v1/search/news.json"
NAVER_DATALAB_URL   = "https://openapi.naver.com/v1/datalab/search"
YOUTUBE_SEARCH_URL  = "https://www.googleapis.com/youtube/v3/search"

# B2B 공통 상수
B2B_SHOPPING_DISPLAY = int(os.getenv("B2B_SHOPPING_DISPLAY", "100"))
B2B_RAG_CHUNK_LEN    = int(os.getenv("B2B_RAG_CHUNK_LEN", "130"))
B2B_CI_MULTIPLIER    = float(os.getenv("B2B_CI_MULTIPLIER", "1.5"))

# 공공데이터 API
PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")  # data.go.kr 통합 키
KOSIS_API_KEY       = os.getenv("KOSIS_API_KEY", "")        # 통계청 kosis.kr
KEPCO_API_KEY       = os.getenv("KEPCO_API_KEY", "")        # 한전 bigdata.kepco.co.kr

# Groq
GROQ_PRIMARY_MODEL   = os.getenv("GROQ_PRIMARY_MODEL",   "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODEL  = os.getenv("GROQ_FALLBACK_MODEL",  "llama-3.1-8b-instant")
GROQ_CACHE_TTL       = int(os.getenv("GROQ_CACHE_TTL",   "14400"))  # 4시간
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}

_DL_CACHE: dict = {}

_COMMON_BLOCK = ["렌탈", "월렌탈", "렌탈료", "기기변경", "요금제", "개통", "의류", "옷"]

# 카테고리 룰이 없을 때 가전 여부 판단용 폴백 키워드
APPLIANCE_KEYWORDS = [
    "에어컨", "냉난방기", "냉장고", "김치냉장고", "세탁기", "건조기", "세탁건조기",
    "공기청정기", "로봇청소기", "식기세척기", "TV", "텔레비전",
    "에어프라이어", "전기밥솥", "밥솥", "전자레인지", "가습기", "제습기",
    "선풍기", "청소기", "스타일러", "의류관리기", "정수기", "인덕션",
    "전기레인지", "전기오븐", "전기그릴", "전기포트", "블렌더", "믹서기",
    "식품건조기", "안마의자", "공기청정", "히터", "전기히터", "온풍기",
]

CATEGORY_RULES = {
    "에어컨": {
        "must": ["에어컨", "냉난방기"],
        "block": _COMMON_BLOCK + [
            "청소", "세정", "스프레이", "필터", "교체필터", "커버", "탈취",
            "세척", "방향제", "부품", "블레이드", "날개", "팬날개",
            "팬블레이드", "선풍기 블레이드", "소모품",
        ],
        "min_price": 200000,
    },
    "냉장고": {
        "must": ["냉장고"],
        "block": _COMMON_BLOCK + [
            "청소", "탈취", "보관용기", "정리함", "부품", "세제",
            "스티커", "자석", "필터", "정품필터", "소모품", "교체",
        ],
        "min_price": 300000,
    },
    "세탁기": {
        "must": ["세탁기"],
        "block": _COMMON_BLOCK + [
            "청소", "세제", "세탁망", "커버", "부품", "소모품", "필터",
        ],
        "min_price": 250000,
    },
    "건조기": {
        "must": ["건조기"],
        "block": _COMMON_BLOCK + [
            "청소", "부품", "필터", "소모품",
        ],
        "min_price": 250000,
    },
    "공기청정기": {
        "must": ["공기청정기"],
        "block": _COMMON_BLOCK + [
            "필터", "교체필터", "부품", "소모품",
        ],
        "min_price": 150000,   # 15만원 미만은 장난감·소형 USB 타입
    },
    "로봇청소기": {
        "must": ["로봇청소기", "로봇 청소기"],
        "block": _COMMON_BLOCK + [
            "부품", "걸레", "소모품", "필터", "청소포",
        ],
        "min_price": 200000,   # 20만원 미만은 완구 수준
    },
    "식기세척기": {
        "must": ["식기세척기"],
        "block": _COMMON_BLOCK + [
            "세제", "부품", "청소", "소모품",
        ],
        "min_price": 150000,
    },
    "TV": {
        "must": ["TV", "텔레비전"],
        "block": _COMMON_BLOCK + [
            "거치대", "브라켓", "케이블", "리모컨", "청소", "가방",
        ],
        "min_price": 150000,
    },
    "세탁건조기": {
        "must": ["세탁건조기", "건조세탁기"],
        "block": _COMMON_BLOCK + [
            "청소", "세제", "부품", "소모품", "필터",
        ],
        "min_price": 500000,
    },
    "에어프라이어": {
        "must": ["에어프라이어"],
        "block": _COMMON_BLOCK + [
            "부품", "액세서리", "오일종이", "호일", "용지", "세제", "종이", "소모품",
        ],
        "min_price": 20000,
    },
    "전기밥솥": {
        "must": ["전기밥솥", "밥솥"],
        "block": _COMMON_BLOCK + [
            "부품", "패킹", "세제", "소모품",
        ],
        "min_price": 80000,    # 8만원 미만은 캠핑용·미니 제품
    },
    "전자레인지": {
        "must": ["전자레인지"],
        "block": _COMMON_BLOCK + [
            "부품", "청소", "소모품",
        ],
        "min_price": 80000,    # 8만원 미만은 소형 미니 제품
    },
    "가습기": {
        "must": ["가습기"],
        "block": _COMMON_BLOCK + [
            "청소", "세제", "필터", "부품", "소모품",
        ],
        "min_price": 20000,
    },
    "제습기": {
        "must": ["제습기"],
        "block": _COMMON_BLOCK + [
            "부품", "소모품", "필터",
        ],
        "min_price": 50000,
    },
    "선풍기": {
        "must": ["선풍기"],
        "block": _COMMON_BLOCK + [
            "부품", "날개만", "커버", "소모품",
        ],
        "min_price": 15000,
    },
}

_CATEGORY_MAP = {
    '냉장고': '냉장고', '김치냉장고': '냉장고',
    '세탁기': '세탁기', '건조기': '건조기',
    '에어컨': '에어컨', '시스템에어컨': '에어컨',
    '공기청정기': '공기청정기',
    '로봇청소기': '로봇청소기', '청소기': '청소기',
    '식기세척기': '식기세척기',
    'TV': 'TV', '텔레비전': 'TV', '티비': 'TV',
    '에어프라이어': '에어프라이어',
    '밥솥': '전기밥솥', '전기밥솥': '전기밥솥',
    '전자레인지': '전자레인지',
    '커피머신': '커피머신',
    '가습기': '가습기', '제습기': '제습기',
    '선풍기': '선풍기', '히터': '전기히터',
    '헤어드라이어': '헤어드라이어',
    '사운드바': '사운드바', '스피커': '블루투스 스피커',
}

_POS_WORDS = ['좋', '만족', '추천', '훌륭', '최고', '편리', '깔끔', '빠름', '조용', '완벽', '괜찮', '가성비', '예쁘', '튼튼', '탁월', '우수']
_NEG_WORDS = ['아쉽', '실망', '불만', '문제', '고장', '소음', '느림', '비쌈', '불편', '나쁨', '최악', '반품', '환불', '하자', '불량']
_STOP = {'있어', '이렇게', '그리고', '하지만', '있는', '하는', '있고', '않아', '것이', '수도', '이나', '이제', '이것', '에서', '으로', '부터', '같이', '때문', '이라', '하고', '에도', '까지', '이라고', '이런', '정도', '이상', '라서'}
