import json
import math

from bs4 import BeautifulSoup

from app.routers.b2b_utils import *
from app.services.price_service import get_danawa_price_history
from app.routers.naver import require_naver_available, search_products

try:
    import pandas as _pd
    from prophet import Prophet as _Prophet
    _PROPHET_AVAILABLE = True
except ImportError:
    _PROPHET_AVAILABLE = False

router = APIRouter()

# 네이버 쇼핑인사이트(실제 쇼핑 클릭 동향) 카테고리 코드 — b2b_product.py와 동일한 매핑을 공유
_SHOPPING_CAT_MAP = {
    "에어컨":    "50000134",
    "냉장고":    "50000136",
    "세탁기":    "50000138",
    "건조기":    "50000139",
    "공기청정기": "50000140",
    "로봇청소기": "50000141",
    "식기세척기": "50000142",
    "TV":        "50000008",
    "전기밥솥":  "50000143",
    "전자레인지": "50000144",
}

_CAPACITY_RE = re.compile(r'(\d{2,4})\s*[Ll리]')


def _extract_capacity(title: str):
    """제품명에서 용량(L) 추출 — 경쟁 제품을 '비슷한 스펙'으로 매칭할 때 사용."""
    m = _CAPACITY_RE.search(title)
    return int(m.group(1)) if m else None


# 국내 가전 모델명(예: LG "S656P003")은 앞 글자가 1개뿐인 경우가 많아 공용 유틸의
# extract_model_number(최소 2글자 접두 요구)로는 못 잡는다 — 공용 유틸은 다른 곳에서도
# 쓰이므로 건드리지 않고, 경쟁 제품 모델명 추출에만 쓸 더 넓은 정규식을 따로 둔다.
_MODEL_CANDIDATE_RE = re.compile(r'[A-Z]{1,5}\d{1,4}[A-Z0-9]{2,12}')


def _extract_model_broad(title: str):
    candidates = [c for c in _MODEL_CANDIDATE_RE.findall(title.upper()) if len(c) >= 6]
    return candidates[0] if candidates else None

_RENTAL_KW = [
    "렌탈", "리스", "렌트", "대여", "월정액", "구독",
    "업소용", "영업용", "주방용", "매장용",
]

# "사용후기" 검색에 실제 리뷰가 아니라 판매자/블로거의 홍보·특가 안내 글이 섞여 들어오면
# 진짜 사용 경험이 아닌 이벤트/할인 문구가 감성 분류를 오염시킨다 (예: 정보성 안내 문구가
# 부정으로 오분류되는 문제) — 리뷰 풀에 들어가기 전에 걸러낸다.
_PROMO_KW = ["핫딜", "특가", "이벤트", "페스티벌", "상품권", "무료설치", "쿠폰", "사은품", "증정", "혜택가", "혜택을"]


_FOREIGN_SCRIPT_RE = re.compile(
    r'[Ѐ-ӿͰ-Ͽ֐-׿؀-ۿ฀-๿]'
)


_HANGUL_RE = re.compile(r'[가-힣]')


def _clean_ai_text(text):
    """LLM이 간혹 섞어 내보내는 키릴·그리스·한자/가나 등 이질적 문자가 포함된 경우, 또는 폴백
    모델이 지시를 안 지키고 통째로 영어로 답한 경우 신뢰하지 않고 버린다 (한글이 거의 없는
    긴 문장은 번역 누락으로 간주 — 모델명 등 알파벳 단어 몇 개는 정상 한국어 문장에도
    섞이므로, 문장이 어느 정도 길면서 한글 비중이 매우 낮을 때만 걸러낸다)."""
    if not isinstance(text, str) or not text.strip():
        return None
    if _FOREIGN_SCRIPT_RE.search(text) or _has_non_korean_cjk(text):
        return None
    if len(text) >= 25 and len(_HANGUL_RE.findall(text)) < len(text) * 0.15:
        return None
    return text


def _linear_trend_fit(history: list[dict]):
    """실제 데이터 구간에 대한 선형회귀 적합선 — 미래 예측이 아니라 추세 방향을 보여주는 오버레이용."""
    ys = [h["ratio"] for h in history]
    n = len(ys)
    if n < 2:
        return [], 0.0
    xs = list(range(n))
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    denom = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / denom if denom else 0.0
    intercept = (sy - slope * sx) / n
    fitted = [
        {"period": history[i]["period"], "ratio": round(intercept + slope * i, 1)}
        for i in range(n)
    ]
    return fitted, slope


def _run_prophet_sync(train_data: list[dict], periods: int = 22, freq: str = "W"):
    """Prophet 기반 예측 — CPU 바운드라 asyncio.to_thread로 호출해야 한다.
    freq="W"(주간, 검색량) 또는 "MS"(월간, 쇼핑인사이트 판매량)."""
    import logging as _logging
    _logging.getLogger("prophet").setLevel(_logging.ERROR)
    _logging.getLogger("cmdstanpy").setLevel(_logging.ERROR)

    df = _pd.DataFrame({
        "ds": _pd.to_datetime([d["period"] for d in train_data]),
        "y":  [float(d["ratio"]) for d in train_data],
    })
    n_pts = len(df)
    # 월 단위(MS, 쇼핑인사이트 판매량)는 실무상 최대 24개월 남짓만 쌓여 연간 주기를
    # 1~2번밖에 못 본다 — 이 상태에서 yearly_seasonality를 켜면 과적합으로 특정 월에
    # 예측치가 0 근처로 급락했다가 급등하는 등 비현실적인 예측이 나온다. 그래서 월
    # 단위는 계절성 없이 추세(trend)만으로 예측하고, 데이터가 훨씬 많은 주 단위(검색
    # 관심도)만 연간 계절성을 사용한다.
    m = _Prophet(
        yearly_seasonality=(n_pts >= 52 if freq == "W" else False),
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,
        seasonality_mode="additive",
        changepoint_prior_scale=0.1,
    )
    m.fit(df)
    future = m.make_future_dataframe(periods=periods, freq=freq)
    fc = m.predict(future)
    last_ds = df["ds"].max()
    future_rows = fc[fc["ds"] > last_ds]
    rows = []
    for row in future_rows.itertuples():
        ratio = max(0.0, round(float(row.yhat), 1))
        rows.append({
            "period": row.ds.strftime("%Y-%m-%d"),
            "ratio":  ratio,
            "lower":  max(0.0, round(float(row.yhat_lower), 1)),
            "upper":  max(ratio, round(float(row.yhat_upper), 1)),
        })
    return rows


def _linear_forecast(history: list[dict], n_forecast: int = 8, step_days: int = 7):
    """단순 선형회귀 예측 (Prophet 사용 불가/실패 시 대체용). step_days=7(주간) 또는 30(월간)."""
    ys = [h["ratio"] for h in history]
    n = len(ys)
    if n < 4:
        return [], 0.0

    xs = list(range(n))
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    denom = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / denom if denom else 0.0
    intercept = (sy - slope * sx) / n
    residuals = [ys[i] - (intercept + slope * i) for i in range(n)]
    std = math.sqrt(sum(r * r for r in residuals) / max(n - 2, 1))

    last_date = date.fromisoformat(history[-1]["period"][:10])
    forecast = []
    for i in range(1, n_forecast + 1):
        xi = n - 1 + i
        pred = max(0.0, round(intercept + slope * xi, 1))
        label = (last_date + timedelta(days=step_days * i)).isoformat()
        forecast.append({
            "period": label,
            "ratio":  pred,
            "lower":  max(0.0, round(pred - _CI_MULTIPLIER * std, 1)),
            "upper":  round(pred + _CI_MULTIPLIER * std, 1),
        })
    return forecast, slope


@router.get("/product-search")
async def get_product_search(q: str = Query(..., min_length=1), _: dict = Depends(require_b2b)):
    """검색어에 매칭되는 실제 상품 목록(사진·모델명·가격)을 반환 — 사용자가 그 중 하나를 골라야
    /search-analysis가 해당 '단일 상품' 기준으로 정밀 분석을 수행한다."""
    from app.services.public_data import get_kemco_model_grades_cached

    detected_category = None
    for kw, cat in _CATEGORY_MAP.items():
        if kw in q:
            detected_category = cat
            break

    try:
        result = await search_products(query=q, page=1, display=40, sort="sim")
        raw = result.get("items", [])
    except Exception as e:
        logger.warning("[product-search] 조회 실패: %s", e)
        raw = []

    # 정부 API 전체 조회는 수십~수백 초 걸려 실시간 요청을 막을 수 없다 —
    # 캐시가 있으면 즉시 실데이터를 쓰고, 없으면 백그라운드로 채우는 동안은 폴백(정규식)만 쓴다.
    grade_map = await get_kemco_model_grades_cached(detected_category) if detected_category else {}

    # 국내 가전 모델명(예: RM70F90R2ZD, RS84DB5002CW)은 3자리 연속 숫자가 없는 경우가 많아
    # 기존 extract_model_number보다 넓게 잡아야 KEMCO 등급표와 매칭된다.
    _model_candidate_re = re.compile(r'[A-Z]{1,5}\d{1,4}[A-Z0-9]{2,12}')
    _energy_re = re.compile(r'(\d)\s*등급')
    seen_titles: set[str] = set()
    items = []
    for it in raw:
        if not it.get("price") or it["price"] <= 0:
            continue
        title = it.get("title", "")
        if title in seen_titles or any(k in title for k in _RENTAL_KW):
            continue
        seen_titles.add(title)

        energy_grade = None
        if grade_map:
            candidates = [c for c in _model_candidate_re.findall(title.upper()) if len(c) >= 6]
            for cand in candidates:
                if cand in grade_map:
                    energy_grade = grade_map[cand]
                    break
        if energy_grade is None:
            m = _energy_re.search(title)
            energy_grade = int(m.group(1)) if m else None

        items.append({
            "title": title,
            "brand": it.get("brand", "").strip(),
            "price": it["price"],
            "image": it.get("image", ""),
            "link":  it.get("link", ""),
            "energy_grade": energy_grade,
        })

    return {"query": q, "items": items[:30]}


async def _fetch_review_snippets(query: str, display_blog: int = 10, display_cafe: int = 6, sort: str = "date"):
    """블로그+카페 리뷰 텍스트 스니펫 실검색 (공용 헬퍼)."""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            blog_r, cafe_r = await asyncio.gather(
                client.get("https://openapi.naver.com/v1/search/blog.json", headers=NAVER_HEADERS,
                    params={"query": query, "display": display_blog, "sort": sort}),
                client.get("https://openapi.naver.com/v1/search/cafearticle.json", headers=NAVER_HEADERS,
                    params={"query": query, "display": display_cafe, "sort": sort}),
            )
        out = []
        for it in blog_r.json().get("items", []):
            txt = strip_html(it.get("description", "")).strip()
            if len(txt) < 20:
                continue
            out.append({"source": "블로그", "title": strip_html(it["title"]), "text": txt[:200], "link": it.get("link", "")})
        for it in cafe_r.json().get("items", []):
            txt = strip_html(it.get("description", "")).strip()
            if len(txt) < 20:
                continue
            out.append({"source": "카페", "title": strip_html(it["title"]), "text": txt[:200], "link": it.get("link", "")})
        return out
    except Exception as e:
        logger.warning("[search-analysis] 리뷰 조회 실패 (%s): %s", query, e)
        return []


_NAVER_BLOG_RE = re.compile(r'https?://blog\.naver\.com/([\w-]+)/(\d+)')


async def _fetch_full_review_text(url: str) -> str | None:
    """리뷰 링크의 실제 본문 전체를 가져온다 — 네이버 검색 API가 주는 스니펫은 100~150자로
    짧아서 실제 단점/장점 내용이 나오기 직전에 잘리는 경우가 많다 (예: '단점까지 다 까발리는
    후기 시작해 볼게요!'처럼 본론 직전에 끊김). 네이버 블로그 PC 페이지는 본문이 iframe 안에
    있어 직접 못 읽으므로 모바일 페이지로 바꿔서 가져온다. 로그인 필요한 카페 글 등 실패하면
    None을 반환해 호출부가 기존 짧은 스니펫을 그대로 쓰게 한다."""
    m = _NAVER_BLOG_RE.match(url)
    fetch_url = f"https://m.blog.naver.com/{m.group(1)}/{m.group(2)}" if m else url
    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(fetch_url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        body = soup.select_one("div.se-main-container") or soup.select_one("#postViewArea") or soup
        text = re.sub(r'\s+', ' ', body.get_text(" ")).strip()
        return text[:1500] if len(text) > 100 else None
    except Exception:
        return None


async def _enrich_with_full_text(reviews: list[dict]) -> list[dict]:
    """AI 요약에 쓸 상위 리뷰들만 원문 페이지에서 본문 전체를 받아와 스니펫을 교체한다 —
    전체 리뷰 풀(최대 40개)을 다 긁으면 너무 느리니, 실제로 요약 프롬프트에 들어갈 소수
    (부정 8개 + 긍정 6개)만 동시 5개로 제한해서 가져온다."""
    sem = asyncio.Semaphore(5)

    async def _one(r: dict) -> dict:
        if not r.get("link"):
            return r
        async with sem:
            full_text = await _fetch_full_review_text(r["link"])
        return {**r, "text": full_text} if full_text else r

    return list(await asyncio.gather(*[_one(r) for r in reviews]))


_SENTIMENT_LINE_RE = re.compile(r'(\d+)\s*[:.\)]\s*(positive|negative|pos|neg|긍정|부정)', re.IGNORECASE)


async def _classify_reviews_sentiment(items: list[dict]) -> list[str] | None:
    """리뷰 전체를 긍/부정으로 분류 — 단순 키워드 카운트는 '소음이 거의 없다', '고장 없이
    잘 쓴다'처럼 부정 단어(소음/고장)가 들어가도 실제로는 긍정인 문장을 오분류하는 문제가
    있어, 문맥을 읽을 수 있는 AI로 분류한다.
    일일 토큰 한도 소진 시 폴백되는 보조 모델은 JSON 형식 지시를 잘 안 지키고 배치가 크면
    응답이 잘리기도 해서, 토큰 효율이 좋고 부분 복구가 쉬운 "번호:라벨" 줄글 형식을 쓴다.
    응답이 중간에 잘려도 파싱된 앞부분은 그대로 쓰고, 못 받은 나머지만 None으로 남겨
    호출부가 그 항목만 키워드 카운트로 폴백하게 한다."""
    if not items:
        return []
    numbered = "\n".join(f"{i + 1}. {it['text'][:150]}" for i, it in enumerate(items))
    try:
        resp = await _groq_create(
            messages=[
                {"role": "system", "content": "당신은 가전제품 리뷰 감성 분류기입니다. 단어만 보지 말고 문맥을 정확히 읽고 분류하세요."},
                {"role": "user", "content": (
                    f"아래 리뷰 {len(items)}개 각각이 전반적으로 긍정적인지(pos) 부정적인지(neg) 분류하세요. "
                    "'소음이 거의 없다', '고장 없이 잘 쓴다', '불편함 없이 편하게 사용 중'처럼 부정적인 단어가 "
                    "들어가도 그것이 없다/안 그렇다는 의미면 긍정(pos)입니다. 실제로 사용자가 불만·문제·아쉬운 "
                    "점을 직접 이야기하는 리뷰만 부정(neg)이고, 사용법·보관법·이벤트/할인 안내처럼 단순 정보성·"
                    "홍보성 내용이거나 불만인지 애매한 경우는 전부 긍정(pos)으로 분류하세요 — 확실한 근거가 "
                    "없으면 기본값은 pos입니다.\n\n"
                    f"{numbered}\n\n"
                    f"각 줄에 번호와 라벨만 콜론으로 구분해 출력하세요 (설명·다른 텍스트 없이), "
                    f"정확히 {len(items)}줄:\n1:pos\n2:neg\n..."
                )},
            ],
            max_tokens=min(4000, 100 + len(items) * 20), temperature=0.0,
        )
        raw = resp.choices[0].message.content.strip()
        matches = _SENTIMENT_LINE_RE.findall(raw)
        if not matches:
            return None
        by_index: dict[int, str] = {}
        for idx_s, lb in matches:
            idx = int(idx_s) - 1
            if 0 <= idx < len(items):
                by_index[idx] = "neg" if lb.lower() in ("neg", "negative", "부정") else "pos"
        # 절반 미만만 받으면 이 배치 자체를 신뢰하기 어려우니 통째로 폴백
        if len(by_index) < len(items) * 0.5:
            return None
        return [by_index.get(i) for i in range(len(items))]
    except Exception as e:
        logger.warning("[search-analysis] 리뷰 감성 분류 실패: %s", e)
        return None


@router.get("/search-analysis")
async def get_search_analysis(
    q: str = Query(..., min_length=1),
    hint: str = Query("", description="상품 목록 선택 전, 사용자가 원래 입력한 검색어 — 정확한 상품명에는 카테고리 단어가 없는 경우가 많아 보조 힌트로 사용"),
    force: bool = Query(False, description="true면 캐시를 무시하고 가격·리뷰·AI 리포트를 전부 새로 가져온다 ('업데이트' 버튼용)"),
    _: dict = Depends(require_b2b),
):
    require_naver_available()
    from app.database import fetchall, execute as db_exec

    today = date.today()
    # 공용 extract_model_number는 앞 글자가 1개뿐인 국내 모델명(예: "RS84DB5002CW",
    # "S656P003")을 못 잡는다 — 경쟁 제품 쪽엔 이미 _extract_model_broad로 고쳐놨는데,
    # 정작 선택한 제품 자신의 모델명(화면 표시 + 가격 이력 추적 키로 사용)은 안 고쳐져 있었다.
    # 이러면 모델명이 화면에 안 뜨고, 같은 제품을 다른 검색어로 다시 조회할 때마다 가격
    # 이력이 서로 다른 키로 쪼개져 안 쌓이는 문제가 있었다.
    model = extract_model_number(q) or _extract_model_broad(q)
    product_key = model if model else re.sub(r'\s+', ' ', q.strip())[:100]

    detected_category = None
    for text in (q, hint):
        if not text:
            continue
        for kw, cat in _CATEGORY_MAP.items():
            if kw in text:
                detected_category = cat
                break
        if detected_category:
            break

    # 이 도구는 가전제품(냉장고·세탁기·에어컨 등) 전용으로 설계돼 있다 — 스마트폰처럼
    # _CATEGORY_MAP에 없는 카테고리는 가격 이상치 필터(통신사 약정가 vs 무약정가 구분 불가),
    # DataLab 카테고리 코드, 리뷰 관련성 필터(용량/모델 기반)가 전부 안 맞아서 억지로 분석을
    # 진행하면 말도 안 되는 가격이나 텅 빈 추이·경쟁 제품 카드처럼 오히려 잘못된 결과를
    # 보여주게 된다. 지원 안 되는 카테고리는 정직하게 안내하고 끝낸다.
    if not detected_category:
        return {
            "query": q,
            "category": None,
            "unsupported": True,
            "message": "이 상품의 카테고리는 아직 지원하지 않습니다. 이 도구는 냉장고·세탁기·에어컨·건조기 등 가전제품 분석에 특화되어 있어, 스마트폰 등 다른 상품군은 정확한 분석을 제공할 수 없습니다.",
        }

    _ck = f"search-analysis:{_CACHE_VER}:v2:{q}"
    _cached = _GROQ_CACHE.get(_ck)
    if not force and _cached and _time.time() < _cached[0]:
        return _cached[1]

    search_q_product  = model if model else q
    search_q_category = detected_category or q

    async def _fetch_product_items():
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(NAVER_SHOP_URL, headers=NAVER_HEADERS,
                    params={"query": search_q_product, "display": 40, "sort": "sim"})
            raw = resp.json().get("items", []) if resp.status_code == 200 else []
        except Exception as e:
            logger.warning("[search-analysis] 제품 가격 조회 실패: %s", e)
            raw = []
        return [
            {
                "mall":  strip_html(it.get("mallName", "")),
                "brand": (it.get("maker") or it.get("brand") or "").strip(),
                "title": strip_html(it.get("title", "")),
                "price": int(it["lprice"]),
                "link":  it.get("link", ""),
                "image": it.get("image", ""),
            }
            for it in raw
            if it.get("lprice") and int(it["lprice"]) > 0
            and not any(k in strip_html(it.get("mallName", "")) for k in _RENTAL_KW)
            and not any(k in strip_html(it.get("title", "")) for k in _RENTAL_KW)
        ]

    async def _fetch_category_items():
        if not detected_category:
            return []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(NAVER_SHOP_URL, headers=NAVER_HEADERS,
                    params={"query": detected_category, "display": 60, "sort": "sim"})
            raw = resp.json().get("items", []) if resp.status_code == 200 else []
        except Exception as e:
            logger.warning("[search-analysis] 카테고리 조회 실패: %s", e)
            raw = []
        return [
            {
                "brand": (it.get("maker") or it.get("brand") or "").strip(),
                "title": strip_html(it.get("title", "")),
                "price": int(it["lprice"]),
                "link":  it.get("link", ""),
                "image": it.get("image", ""),
            }
            for it in raw
            if it.get("lprice") and int(it["lprice"]) > 0
            and not any(k in strip_html(it.get("title", "")) for k in _RENTAL_KW)
        ]

    async def _fetch_search_trend(keyword: str, days: int):
        """네이버 데이터랩 검색 관심도 — keyword를 파라미터로 받아 카테고리든 브랜드+제품명이든
        재사용 가능하게 만든 공용 버전 (예전엔 카테고리명 하나만 하드코딩돼 있어서 같은
        카테고리의 모든 제품이 완전히 똑같은 검색량·수요예측 수치를 보였다)."""
        if not keyword:
            return []
        try:
            end_d   = today
            start_d = today - timedelta(days=days)
            body = {
                "startDate": start_d.strftime("%Y-%m-%d"),
                "endDate":   end_d.strftime("%Y-%m-%d"),
                "timeUnit":  "week",
                "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}],
            }
            headers = {**NAVER_HEADERS, "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=(15.0 if days > 90 else 10.0)) as client:
                resp = await client.post("https://openapi.naver.com/v1/datalab/search", json=body, headers=headers)
            results = resp.json().get("results", [])
            data = results[0]["data"] if results else []
        except Exception as e:
            logger.warning("[search-analysis] 검색 트렌드 조회 실패(%s): %s", keyword, e)
            data = []
        if len(data) > 6:
            data = data[:-1]
        return data

    def _trend_keyword_candidates(query: str, category: str) -> list[str]:
        """검색량 추이를 카테고리 전체가 아니라 이 제품(브랜드+제품라인)에 최대한 가깝게
        잡기 위한 후보들 — 완전한 모델명까지 쓰면 데이터랩에 검색량 자체가 없어서(0건
        확인됨), 브랜드+제품명 앞 2~3단어 정도로만 좁히고 그마저 데이터가 부족하면
        카테고리로 폴백한다. "LG전자"처럼 제품명에 붙는 정식 법인명은 실제 검색어("LG")와
        달라 데이터랩에 검색량이 거의 안 잡히므로(확인: "LG전자 디오스 냉장고" 2건 vs
        "LG 디오스 냉장고" 14건), 첫 단어의 "전자" 접미사를 뗀 버전도 후보에 같이 넣는다."""
        words = query.split()
        if words and words[0].endswith("전자") and len(words[0]) > 2:
            words = [words[0][:-2]] + words[1:]
        seen: set[str] = set()
        candidates = []
        for n in (3, 2):
            if len(words) >= n:
                kw = " ".join(words[:n])
                if kw not in seen and kw != category:
                    seen.add(kw)
                    candidates.append(kw)
        if category and category not in seen:
            candidates.append(category)
        return candidates or ([category] if category else [])

    async def _fetch_shopping_trend(days: int):
        """네이버 쇼핑인사이트(실제 쇼핑 클릭 동향, 월 단위) — 검색 관심도와 별개로 '판매량' 근사치로 사용."""
        cat_code = _SHOPPING_CAT_MAP.get(detected_category)
        if not cat_code:
            return []
        try:
            end_d   = today
            start_d = today - timedelta(days=days)
            body = {
                "startDate": start_d.strftime("%Y-%m-%d"),
                "endDate":   end_d.strftime("%Y-%m-%d"),
                "timeUnit":  "month",
                "category":  [{"name": detected_category, "param": [cat_code]}],
            }
            headers = {**NAVER_HEADERS, "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post("https://openapi.naver.com/v1/datalab/shopping/categories", json=body, headers=headers)
            results = resp.json().get("results", [])
            data = results[0]["data"] if results else []
        except Exception as e:
            logger.warning("[search-analysis] 쇼핑인사이트 조회 실패: %s", e)
            data = []
        # 이번 달은 집계가 끝나지 않아 값이 비정상적으로 낮게 나오므로 마지막(이번 달) 포인트는 제거
        if data and data[-1]["period"][:7] == today.strftime("%Y-%m"):
            data = data[:-1]
        return [{"period": d["period"], "ratio": d["ratio"]} for d in data]

    async def _fetch_danawa():
        try:
            return await get_danawa_price_history(search_q_product, q)
        except Exception as e:
            logger.warning("[search-analysis] 다나와 조회 실패: %s", e)
            return {"history": [], "launch_price": None}

    async def _fetch_release_info():
        """실제 출시 관련 뉴스/블로그 검색 결과 — AI가 이 텍스트에서만 출시일·출시가를 추출하도록 근거로 사용."""
        try:
            rq = f"{q} 출시가 출시일"
            async with httpx.AsyncClient(timeout=8.0) as client:
                news_r, blog_r = await asyncio.gather(
                    client.get("https://openapi.naver.com/v1/search/news.json", headers=NAVER_HEADERS,
                        params={"query": rq, "display": 5, "sort": "sim"}),
                    client.get("https://openapi.naver.com/v1/search/blog.json", headers=NAVER_HEADERS,
                        params={"query": rq, "display": 5, "sort": "sim"}),
                )
            snippets = []
            for it in news_r.json().get("items", []):
                txt = strip_html(it.get("description", "")).strip()
                if txt:
                    snippets.append(f"[뉴스] {strip_html(it.get('title',''))}: {txt[:200]}")
            for it in blog_r.json().get("items", []):
                txt = strip_html(it.get("description", "")).strip()
                if txt:
                    snippets.append(f"[블로그] {strip_html(it.get('title',''))}: {txt[:200]}")
            return snippets[:8]
        except Exception as e:
            logger.warning("[search-analysis] 출시 정보 조회 실패: %s", e)
            return []

    # 검색량 추이를 카테고리 전체("냉장고")가 아니라 이 제품(브랜드+제품라인, 예: "삼성
    # 비스포크")에 최대한 가깝게 잡는다 — 후보들을 병렬로 90일치만 먼저 떠보고, 가장
    # 구체적이면서 데이터가 충분한(6건 이상) 키워드를 채택한다. 다 부족하면 카테고리로
    # 자연스럽게 폴백된다(후보 목록 맨 끝에 카테고리 자체가 항상 들어있음).
    trend_keyword = detected_category
    trend_data = []
    if detected_category:
        _trend_candidates = _trend_keyword_candidates(q, detected_category)
        _trend_probes = await asyncio.gather(*[_fetch_search_trend(c, 90) for c in _trend_candidates])
        for _cand, _probe_data in zip(_trend_candidates, _trend_probes):
            if len(_probe_data) >= 6:
                trend_keyword, trend_data = _cand, _probe_data
                break

    (product_items, category_items, train_data,
     sales_trend_data, sales_train_data,
     product_reviews, category_reviews, release_snippets, danawa_result) = await asyncio.gather(
        _fetch_product_items(),
        _fetch_category_items(),
        _fetch_search_trend(trend_keyword, 730) if _PROPHET_AVAILABLE else asyncio.sleep(0, result=[]),
        _fetch_shopping_trend(365),
        _fetch_shopping_trend(730),
        # sort="sim"(정확도순)으로 바꿔야 "단점" 키워드와 실제로 관련된 글이 우선 잡힌다 —
        # date순은 최신 글만 잡혀 리뷰 내용과 무관한 글이 섞이고, 표본이 작으면 부정 후기가
        # 거의 안 잡히는 문제가 있어 수집량도 늘렸다.
        _fetch_review_snippets(f"{search_q_product} 사용후기 단점", 20, 15, sort="sim"),
        _fetch_review_snippets(f"{search_q_category} 사용후기 단점", 20, 15, sort="sim") if detected_category else asyncio.sleep(0, result=[]),
        _fetch_release_info(),
        _fetch_danawa(),
    )

    # 제품 자체 리뷰가 있으면 우선 사용하고, 부족하면 카테고리 리뷰로 보강 (실제 데이터 풀 확보).
    # category_reviews는 "냉장고 사용후기 단점"처럼 카테고리명으로만 검색해서 전혀 다른
    # 브랜드/모델(LG, 스타리온 미니냉장고, 캠핑 쿨러 등)의 리뷰가 섞여 들어온다 — 이 남의
    # 제품 얘기가 선택한 제품의 감성 점수/배지에 그대로 반영되면 안 되니, 모델명(또는 용량)이
    # 실제로 일치하는 것만 보강 풀에 남긴다.
    _sel_model_broad = _extract_model_broad(q)
    _sel_capacity_for_filter = _extract_capacity(q)

    def _is_relevant_category_review(r: dict) -> bool:
        combined = (r["title"] + " " + r["text"]).upper()
        if _sel_model_broad:
            return _sel_model_broad in combined
        if _sel_capacity_for_filter:
            return f"{_sel_capacity_for_filter}L" in combined or f"{_sel_capacity_for_filter}리터" in combined
        return True

    reviews = product_reviews + [
        r for r in category_reviews if r not in product_reviews and _is_relevant_category_review(r)
    ]
    reviews = [r for r in reviews if not any(k in r["text"] or k in r["title"] for k in _PROMO_KW)]

    # ── 관심도(검색량) 추세 — 가격 신호와 결합해 종합 결론에 사용 — + Prophet 미래 예측 ──
    linear_trend_pts, slope = _linear_trend_fit(trend_data) if trend_data else ([], 0.0)

    prophet_forecast = []
    if _PROPHET_AVAILABLE and len(train_data) >= 8:
        try:
            prophet_forecast = await asyncio.to_thread(_run_prophet_sync, train_data, 22)
        except Exception as e:
            logger.warning("[search-analysis] Prophet 예측 실패: %s", e)
    if not prophet_forecast and trend_data:
        prophet_forecast, _ = _linear_forecast(trend_data)

    # 검색량 추이 한줄 평가 — 등락 원인을 추측(=지어내기)하지 않고, 실제 최근 변동폭과
    # 예측 방향/크기만 사실 그대로 서술한다.
    interest_reason = None
    if trend_data:
        recent_vals = [d["ratio"] for d in trend_data[-8:]] if len(trend_data) >= 8 else [d["ratio"] for d in trend_data]
        lo_v, hi_v = round(min(recent_vals), 1), round(max(recent_vals), 1)
        swing_pct = round((hi_v - lo_v) / max(lo_v, 1) * 100, 1)
        if prophet_forecast:
            base = trend_data[-1]["ratio"]
            fc_end = prophet_forecast[-1]["ratio"]
            fc_pct = round((fc_end - base) / max(base, 1) * 100, 1)
            direction = "상승" if fc_pct > 0 else ("하락" if fc_pct < 0 else "보합")
            interest_reason = (
                f"최근 관심도는 최저 {lo_v}~최고 {hi_v} 사이에서 등락(변동폭 {swing_pct}%)했고, "
                f"향후 {len(prophet_forecast)}주간 {direction}세로 {'+' if fc_pct >= 0 else ''}{fc_pct}% 변화할 것으로 예측됩니다."
            )
        else:
            interest_reason = f"최근 관심도는 최저 {lo_v}~최고 {hi_v} 사이에서 등락(변동폭 {swing_pct}%)했습니다."

    # ── 판매량(쇼핑인사이트 클릭 동향) 추세 — 검색 관심도와는 별개 지표 — + Prophet 예측 ──
    sales_linear_trend_pts, sales_slope = _linear_trend_fit(sales_trend_data) if sales_trend_data else ([], 0.0)

    sales_prophet_forecast = []
    if _PROPHET_AVAILABLE and len(sales_train_data) >= 8:
        try:
            sales_prophet_forecast = await asyncio.to_thread(_run_prophet_sync, sales_train_data, 8, "MS")
        except Exception as e:
            logger.warning("[search-analysis] 판매량 Prophet 예측 실패: %s", e)
    if not sales_prophet_forecast and sales_trend_data:
        sales_prophet_forecast, _ = _linear_forecast(sales_trend_data, 8, step_days=30)

    # 판매량 추이 한줄 평가 — AI 없이 실제 추세/예측 수치만으로 규칙 기반 생성.
    # 방향(상승/하락)은 반드시 '예측 변화율'과 같은 기준으로 계산해야 한다 — 서로 다른
    # 지표(전체 이력 회귀 기울기 vs 예측 구간 변화율)를 섞으면 "상승세인데 -90% 감소"
    # 처럼 문장 안에서 모순되는 경우가 생긴다.
    sales_reason = None
    if sales_trend_data and sales_prophet_forecast:
        base = sales_trend_data[-1]["ratio"]
        fc_end = sales_prophet_forecast[-1]["ratio"]
        fc_pct = round((fc_end - base) / max(base, 1) * 100, 1)
        direction = "상승" if fc_pct > 0 else ("하락" if fc_pct < 0 else "보합")
        sales_reason = (
            f"최근 판매(쇼핑 클릭) 지수는 {round(base, 1)}이며, 향후 {len(sales_prophet_forecast)}개월간 "
            f"{direction}세로 {'+' if fc_pct >= 0 else ''}{fc_pct}% 변화할 것으로 예측됩니다."
        )
    elif sales_trend_data:
        direction = "상승" if sales_slope > 0 else ("하락" if sales_slope < 0 else "보합")
        sales_reason = f"최근 판매(쇼핑 클릭) 추세는 {direction}세입니다."

    # ── 제품 단위 가격 인텔리전스 (#1 기본정보, #4 가격변동, #5 가격적정성의 토대) ──
    price_block = None
    product_image = None
    product_brand = None
    if product_items:
        prices = sorted(it["price"] for it in product_items)
        med = prices[len(prices) // 2]
        filt = [it for it in product_items if med * 0.2 <= it["price"] <= med * 5]
        if filt:
            fp = [it["price"] for it in filt]
            min_p, max_p, avg_p = min(fp), max(fp), int(sum(fp) / len(fp))
            mall_map: dict[str, int] = {}
            for it in filt:
                m = it["mall"]
                if m and (m not in mall_map or it["price"] < mall_map[m]):
                    mall_map[m] = it["price"]
            malls = sorted([{"mall": m, "price": p} for m, p in mall_map.items()], key=lambda x: x["price"])[:8]
            cheapest = min(filt, key=lambda x: x["price"])
            with_image = next((it for it in filt if it.get("image")), None)
            product_image = with_image["image"] if with_image else None
            product_brand = next((it["brand"] for it in filt if it.get("brand")), None)

            mall_json = json.dumps(malls, ensure_ascii=False)
            try:
                await db_exec(
                    """
                    INSERT INTO product_price_history
                        (product_key, product_name, model_number, min_price, max_price, avg_price, snapshot_date, mall_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_key, snapshot_date) DO UPDATE SET
                        min_price = EXCLUDED.min_price,
                        max_price = EXCLUDED.max_price,
                        avg_price = EXCLUDED.avg_price,
                        mall_data = EXCLUDED.mall_data
                    """,
                    (product_key, q[:500], model, min_p, max_p, avg_p, today, mall_json),
                )
            except Exception as e:
                logger.warning("[search-analysis] 가격 DB 저장 실패 [%s]: %s", q[:50], e)

            history_rows = await fetchall(
                "SELECT snapshot_date, min_price, avg_price FROM product_price_history "
                "WHERE product_key = %s ORDER BY snapshot_date ASC LIMIT 60",
                (product_key,),
            )
            # 다나와 실제 과거 가격 이력(최대 24개월) + 우리 DB에 쌓인 최근 스냅샷을 합쳐 진짜 이력 그래프를 만든다
            merged_history: dict[str, dict] = {}
            for h in (danawa_result or {}).get("history", []):
                merged_history[h["period"]] = {"date": h["period"], "min_price": h["price"], "avg_price": h["price"]}
            for r in history_rows:
                d = str(r["snapshot_date"])
                merged_history[d] = {"date": d, "min_price": r["min_price"], "avg_price": r["avg_price"]}
            price_history = [merged_history[k] for k in sorted(merged_history.keys())]

            # "역대 평균가"는 오늘 이전의 진짜 과거 이력만으로 계산해야 한다 — 위에서 오늘
            # 스냅샷을 이미 DB에 저장한 뒤 이 history_rows를 다시 읽어오기 때문에, 필터링
            # 안 하면 오늘 가격 자신이 "역대 평균"에 섞여 들어가 "현재가 vs 역대 평균" 비교가
            # 자기 자신과 비교하는 꼴이 되어 신호가 무뎌진다. (차트에 쓰는 price_history 자체는
            # 오늘 포인트를 포함해야 하므로 그대로 두고, 기준선 계산에서만 오늘을 뺀다.)
            prior_history = [r for r in price_history if r["date"] != str(today)]
            if prior_history:
                hist_avg = int(sum(r["avg_price"] for r in prior_history) / len(prior_history))
                hist_min = min(r["min_price"] for r in prior_history)
            else:
                hist_avg, hist_min = avg_p, min_p
            vs_pct = round((min_p - hist_avg) / max(hist_avg, 1) * 100, 1)

            # 가격 신호 + 관심도(수요) 추세를 함께 봐서 최종 결론을 낸다
            if vs_pct <= -5:
                signal_type = "buy"
            elif vs_pct >= 5 and slope <= 0:
                signal_type = "avoid"
            elif vs_pct >= 5:
                signal_type = "wait"
            elif slope > 1:
                signal_type = "buy"
            else:
                signal_type = "wait"
            signal = {"buy": "매입 추천", "wait": "관망 권장", "avoid": "매입 추천하지 않음"}[signal_type]

            # 가격 적정성(#5)은 가격만으로 판단 — 수요 추세는 섞지 않는다
            if vs_pct <= -5:
                fairness_type = "cheap"
            elif vs_pct >= 5:
                fairness_type = "expensive"
            else:
                fairness_type = "fair"
            fairness_label = {"cheap": "저렴한 편", "fair": "적정 가격", "expensive": "비싼 편"}[fairness_type]

            # 가격 변동(#4) — 실제 이력(다나와 + 우리 DB)이 2개 이상 쌓였을 때만 변동률 계산.
            # 처음~마지막 시점만 비교하면 중간에 오르내림이 있어도 우연히 같은 값이면 0%로
            # 보여 "그래프는 변동이 있는데 왜 0%야"라는 오해가 생긴다 — 순변동(net)과 별개로
            # 이력 중 최저~최고 변동폭(range)도 같이 계산해 실제 변동을 정확히 반영한다.
            price_change_pct = None
            price_range_pct = None
            hist_max_price = None
            if len(price_history) >= 2:
                first_avg = price_history[0]["avg_price"]
                last_avg  = price_history[-1]["avg_price"]
                price_change_pct = round((last_avg - first_avg) / max(first_avg, 1) * 100, 1)
                avgs = [r["avg_price"] for r in price_history]
                lo_avg, hi_avg = min(avgs), max(avgs)
                hist_max_price = hi_avg
                price_range_pct = round((hi_avg - lo_avg) / max(lo_avg, 1) * 100, 1)

            danawa_launch_price = (danawa_result or {}).get("launch_price")

            price_block = {
                "min_price": min_p, "max_price": max_p, "avg_price": avg_p,
                "hist_avg_price": hist_avg, "hist_min_price": hist_min,
                "cheapest_mall": cheapest["mall"], "cheapest_link": cheapest["link"],
                "malls": malls, "price_history": price_history,
                "signal": signal, "signal_type": signal_type, "vs_hist_pct": vs_pct,
                "fairness_type": fairness_type, "fairness_label": fairness_label,
                "price_change_pct": price_change_pct, "price_range_pct": price_range_pct,
                "hist_max_price": hist_max_price, "history_points": len(price_history),
                "launch_price": danawa_launch_price,
            }

    # ── 카테고리 단위 시장 가격 분포 (제품 가격을 못 구했을 때 폴백) ──────────
    cat_price = None
    if category_items:
        cp = sorted(it["price"] for it in category_items)
        cat_price = {"min": cp[0], "max": cp[-1], "avg": int(sum(cp) / len(cp)), "count": len(cp)}

    market_price = (
        {"min": price_block["min_price"], "max": price_block["max_price"],
         "avg": price_block["avg_price"], "count": len(product_items)}
        if price_block else cat_price
    )

    # ── #7 경쟁 제품 1v1 비교 대상 선정 — 브랜드/가격이 아니라 '비슷한 스펙(용량)'의 단일 제품 ──
    competitor = None
    if category_items:
        query_brand = product_brand
        if not query_brand:
            for b in sorted({it["brand"] for it in category_items if it["brand"]}, key=len, reverse=True):
                if b and b in q:
                    query_brand = b
                    break
        ref_price = price_block["min_price"] if price_block else (cat_price["avg"] if cat_price else None)
        selected_capacity = _extract_capacity(q)
        candidates = [it for it in category_items if it["brand"] and it["brand"] != query_brand]

        if selected_capacity:
            # 용량이 추출되는(=비교 가능한 스펙이 있는) 제품만 후보로 삼고, 용량 차이가 가장 적은 순으로 정렬
            spec_candidates = []
            for it in candidates:
                cap = _extract_capacity(it["title"])
                if cap is not None:
                    spec_candidates.append((abs(cap - selected_capacity), it, cap))
            spec_candidates.sort(key=lambda x: x[0])
            if spec_candidates:
                # 용량이 너무 동떨어진(50% 이상 차이) 제품은 '비슷한 스펙'이라 보기 어려우므로 제외
                diff, best, cap = spec_candidates[0]
                if diff <= selected_capacity * 0.5:
                    competitor = {**best, "matched_capacity": cap}

        if not competitor and ref_price:
            candidates.sort(key=lambda it: abs(it["price"] - ref_price))
            if candidates:
                competitor = candidates[0]

        if competitor:
            competitor = {**competitor, "model_number": _extract_model_broad(competitor["title"])}

    competitor_reviews = []
    if competitor:
        competitor_reviews = await _fetch_review_snippets(f"{competitor['title'][:40]} 후기", 6, 4)
        competitor_reviews = await _enrich_with_full_text(competitor_reviews[:6])

    # ── RAG(pgvector) 컨텍스트 ────────────────────────────────────────────────
    rag_enhanced = False
    rag_context = ""
    try:
        from app.dependencies import get_rag_optional
        rag = get_rag_optional()
        if rag and detected_category:
            rag_chunks = await rag.query(f"{detected_category} 시장 동향 수요 전망", n_results=3)
            if rag_chunks:
                rag_context = " / ".join(c[:300] for c in rag_chunks)[:900]
                rag_enhanced = True
    except Exception as e:
        logger.warning("[search-analysis] RAG 조회 실패: %s", e)

    # ── #8 소비자 리뷰 감성 분석 (AI 프롬프트보다 먼저 계산) — 리뷰 단위로 긍/부정을
    # 태깅한 뒤, 점수·배지·목록·AI 요약을 전부 '같은 분류 기준'으로 통일한다.
    # (예전엔 부정 요약은 "부정 단어가 하나라도 있으면" 기준, 배지는 "부정>긍정 단어"
    # 기준으로 서로 달라서 "부정 0인데 왜 부정 요약이 있어?" 같은 불일치가 났었다.)
    # 단순 단어 카운트는 "소음이 거의 없다"처럼 부정 단어(소음)가 들어가도 실제로는
    # 긍정인 문장을 오분류한다 — 문맥을 읽을 수 있는 AI로 분류하고, 실패 시에만
    # 예전 키워드 카운트로 폴백한다.
    review_pool = reviews[:40]
    ai_sentiments = await _classify_reviews_sentiment(review_pool)
    tagged_reviews = []
    for i, r in enumerate(review_pool):
        sentiment = ai_sentiments[i] if ai_sentiments is not None else None
        if sentiment is None:
            p = sum(1 for w in _POS_WORDS if w in r["text"])
            n = sum(1 for w in _NEG_WORDS if w in r["text"])
            sentiment = "neg" if n > p else "pos"
        tagged_reviews.append({**r, "sentiment": sentiment})
    pos_review_count = sum(1 for r in tagged_reviews if r["sentiment"] == "pos")
    neg_review_count = sum(1 for r in tagged_reviews if r["sentiment"] == "neg")
    total_tagged = pos_review_count + neg_review_count
    sentiment_score = round(pos_review_count / total_tagged * 100) if total_tagged > 0 else None

    # ── AI 종합 분석 (단일 Groq 호출 — 실제 수집 데이터에 근거해서만 작성) ────
    neg_reviews = [r for r in tagged_reviews if r["sentiment"] == "neg"][:8]
    pos_reviews = [r for r in tagged_reviews if r["sentiment"] == "pos"][:6]
    # 검색 API 스니펫(100~150자)만으로는 실제 단점/장점 내용이 잘려서 AI가 요약할 실체가
    # 없는 경우가 잦다 — 요약 프롬프트에 실제로 쓰일 이 소수 리뷰만 원문 페이지에서 본문
    # 전체를 가져와 교체한다 (실패하면 기존 스니펫 그대로 유지, 프론트 리뷰 목록에는 영향 없음).
    neg_reviews, pos_reviews = await asyncio.gather(
        _enrich_with_full_text(neg_reviews), _enrich_with_full_text(pos_reviews)
    )

    recent = trend_data[-1]["ratio"] if trend_data else None
    prev   = trend_data[-5]["ratio"] if len(trend_data) >= 5 else (trend_data[0]["ratio"] if trend_data else None)
    change_pct = round((recent - prev) / prev * 100, 1) if recent is not None and prev else None
    forecast_change_pct = None
    if prophet_forecast and trend_data:
        base = trend_data[-1]["ratio"]
        forecast_change_pct = round((prophet_forecast[-1]["ratio"] - base) / max(base, 1) * 100, 1)

    ai_result: dict = {}
    try:
        price_summary = (
            f"현재 최저가 {price_block['min_price']:,}원, 역대 평균가 {price_block['hist_avg_price']:,}원 "
            f"({price_block['vs_hist_pct']}% 대비), 가격 적정성 판단: {price_block['fairness_label']}"
            + (
                f", 이력 기간 순변동 {price_block['price_change_pct']}%, "
                f"최저 {price_block['hist_min_price']:,}원~최고 {price_block['hist_max_price']:,}원 사이 "
                f"최대 {price_block['price_range_pct']}% 변동"
                if price_block['price_change_pct'] is not None else ", 가격 변동 이력 아직 부족"
            )
            if price_block else "가격 데이터 부족"
        )
        neg_text = " / ".join(r["text"][:400] for r in neg_reviews)[:3200]
        pos_text = " / ".join(r["text"][:400] for r in pos_reviews)[:2400]
        release_text = "\n".join(release_snippets)[:1500]
        verdict_label = price_block["signal"] if price_block else None

        competitor_block = ""
        if competitor:
            comp_review_text = " / ".join(r["text"][:400] for r in competitor_reviews)[:2000]
            spec_note = (
                f"(용량 {competitor['matched_capacity']}L로 검색하신 제품과 스펙이 유사)"
                if competitor.get("matched_capacity") else "(비슷한 가격대)"
            )
            competitor_block = (
                f"\n비교 대상 경쟁 제품: {competitor['brand']} - {competitor['title'][:60]} "
                f"{spec_note} (가격 {competitor['price']:,}원)\n경쟁 제품 리뷰 스니펫: {comp_review_text or '없음'}\n"
            )

        prompt = (
            f"제품/카테고리: {q} ({detected_category or '카테고리 미상'})\n"
            f"최근 관심도 변화(최근값 대비 4주 전): {change_pct if change_pct is not None else '데이터 부족'}%\n"
            f"향후 예측 관심도 변화(현재 대비 예측 끝 시점): {forecast_change_pct if forecast_change_pct is not None else '데이터 부족'}%\n"
            f"가격 정보: {price_summary}\n"
            f"출시 관련 검색 결과:\n{release_text or '검색 결과 없음'}\n"
            f"부정 리뷰 내용: {neg_text or '없음'}\n"
            f"긍정 리뷰 내용: {pos_text or '없음'}\n"
            + competitor_block
            + (f"참고 자료(내부 리서치 문서): {rag_context}\n" if rag_context else "")
            + (f"시스템이 가격·수요 추세를 종합해 이미 내린 결론: '{verdict_label}'\n" if verdict_label else "")
            + "\n위 실제 데이터만 근거로 삼아 아래 JSON만 출력하세요 (다른 텍스트 없이 순수 JSON만). "
              "제공된 데이터에 없는 내용은 절대 지어내지 말고, 근거가 없으면 해당 필드에 null을 넣으세요:\n"
            '{"release_date":"YYYY-MM 형식 또는 출시 검색 결과에서 확인 안되면 null",'
            '"launch_price":"검색 결과에 명시된 출시 당시 가격(정수, 원 단위) 또는 확인 안되면 null",'
            '"report_summary":"제품의 시장 상황을 종합한 3~4문장 리포트",'
            f'"conclusion_reason":"왜 \'{verdict_label or "관망 권장"}\' 결론인지 가격·수요 근거로 든 1~2문장",'
            '"price_change_reason":"가격 변동 이력이 있다면 그 증감 이유 추정 1문장, 없으면 null",'
            '"price_fairness_reason":"가격 적정성 판단 이유 1~2문장",'
            '"selected_pros":["선택한 제품의 장점 2~3개. 가격/가격 적정성은 시스템이 별도로 채우니 "'
            '"절대 언급하지 말고 리뷰·기능·디자인 등 가격 이외의 내용만 쓰세요. 리뷰 스니펫 문장을 그대로 "'
            '"베끼지 말고 핵심만 짧게 새로 쓰세요 — 스니펫이 문장 중간에 잘려 있으면 그 리뷰는 무시하세요. "'
            '"리뷰에 없는 수치·통계(예: \'92%의 고객이\')는 절대 지어내지 마세요"],'
            '"selected_cons":["선택한 제품의 단점 2~3개. 위와 동일하게 가격/가격 적정성 언급 금지, 원문 "'
            '"그대로 베끼기 금지, 잘린 스니펫 무시, 없는 수치 지어내기 금지 규칙 모두 적용"],'
            '"competitor_pros":["위에 지정된 단 하나의 경쟁 제품에 대한 장점만 2~3개. 가격은 언급하지 "'
            '"말고, 경쟁 제품 리뷰 스니펫에 다른 모델명이 섞여 있어도 그 모델은 언급하지 말고 지정된 "'
            '"경쟁 제품 얘기만 하세요. 리뷰 문장을 그대로 베끼지 말고 핵심만 새로 쓰고, 없는 수치·통계는 "'
            '"지어내지 마세요. 비교 대상 없으면 빈 배열"],'
            '"competitor_cons":["같은 단 하나의 경쟁 제품에 대한 단점만 2~3개, 가격/다른 모델 언급 금지, "'
            '"원문 그대로 베끼기 금지, 없는 수치 지어내기 금지. 비교 대상 없으면 빈 배열"],'
            '"recommended":"selected 또는 competitor, 비교 대상 없으면 null",'
            '"recommendation_reason":"두 제품 중 하나를 추천하는 이유 1~2문장, 비교 대상 없으면 null",'
            '"positive_summary":"긍정 리뷰에 적힌 구체적인 장점(예: 대용량, 조용함, 디자인 등)만 골라 "'
            '종합한 2~3문장 요약. 리뷰가 \'장점을 알려주겠다/정리해보겠다\'는 말만 있고 실제 구체적인 내용이 '
            '스니펫에 안 담겨 있으면 그런 리뷰는 무시하고, 구체적인 내용이 하나도 없으면 null",'
            '"negative_summary":"부정 리뷰에 적힌 구체적인 단점/불만(예: 소음, 고장, 좁은 공간 등)만 골라 '
            '종합한 2~3문장 요약. 리뷰가 \'단점을 알려주겠다/까발리겠다\'는 말만 있고 실제 구체적인 내용이 '
            '스니펫에 안 담겨 있으면 그런 리뷰는 무시하고, 구체적인 내용이 하나도 없으면 null"}\n'
            "conclusion_reason과 price_fairness_reason은 반드시 시스템이 낸 결론/적정성 판단과 같은 방향으로 쓰세요. "
            "positive_summary/negative_summary는 위에 제공된 리뷰 내용에 없는 내용은 절대 지어내지 마세요. "
            + (
                "selected_pros/selected_cons/competitor_pros/competitor_cons에는 가격이나 '가격 적정성' "
                "얘기를 절대 넣지 마세요 — 두 제품의 실제 가격 비교는 시스템이 정확한 숫자로 별도로 붙입니다."
                if competitor else ""
            )
        )
        resp = await _groq_create(
            messages=[
                {"role": "system", "content": (
                    "당신은 B2B 가전 유통 바이어를 위한 시장 분석 어드바이저입니다. 제공된 실제 데이터에만 근거해 "
                    "순수 JSON으로 답하세요. JSON의 모든 문자열 값(요약, 이유, 장단점 등)은 예외 없이 반드시 "
                    "한국어로만 작성하세요 — 영어나 다른 언어로 쓰면 안 됩니다."
                )},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1300, temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        if "```" in raw:
            raw = re.sub(r'```(?:json)?\s*', '', raw).replace('```', '').strip()
        start_i, end_i = raw.find('{'), raw.rfind('}')
        if start_i != -1 and end_i > start_i:
            ai_result = json.loads(raw[start_i:end_i + 1])
    except Exception as e:
        logger.warning("[search-analysis] AI 분석 실패: %s", e)

    def _clean_list(val):
        if not isinstance(val, list):
            return []
        return [x for x in val if _clean_ai_text(x)]

    _PRICE_MENTION_RE = re.compile(r'[\d,]{4,}\s*원|가격')

    def _drop_fairness_leak(items: list[str]) -> list[str]:
        """가격/가격 적정성 언급은 AI가 틀리기 쉬워(폴라리티 반전, 다른 제품 가격과 혼동)
        시스템이 정확한 숫자로 별도 처리한다 — 프롬프트 지시를 안 지키는 경우를 대비한 최후 방어선."""
        return [x for x in items if not _PRICE_MENTION_RE.search(x)]

    def _drop_other_model_mentions(items: list[str], comp: dict) -> list[str]:
        """경쟁 제품 리뷰 스니펫에 다른 모델명이 섞여 들어와, AI가 지정된 단 하나의 경쟁
        제품이 아니라 다른 용량의 제품을 언급하는 걸 걸러내는 최후 방어선."""
        cap = (comp or {}).get("matched_capacity") or _extract_capacity((comp or {}).get("title", ""))
        if not cap:
            return items
        out = []
        for x in items:
            other_caps = [int(c) for c in re.findall(r'(\d{2,4})\s*[Ll리]', x)]
            if other_caps and cap not in other_caps:
                continue
            out.append(x)
        return out

    def _drop_raw_echo_items(items: list[str], source_reviews: list[dict]) -> list[str]:
        """리뷰 스니펫이 문장 중간에 잘려 있으면, AI가 장단점을 뽑아내는 대신 잘린 원문
        문장을 그대로 항목으로 넣는 경우가 있다 (예: '...단점까지 싹 다 까발리는 투명한 한'
        처럼 문장이 안 끝난 채로 단점 항목에 들어감) — 원문과 35자 이상 겹치면 버린다."""
        out = []
        for x in items:
            if any(
                text[i:i + 35] and text[i:i + 35] in x
                for r in source_reviews
                for text in [r["text"]]
                for i in range(0, max(len(text) - 35, 0) + 1, 10)
            ):
                continue
            out.append(x)
        return out

    # 출시일도 다나와 등록월(실제 스크래핑 값)을 최우선으로 신뢰 — 뉴스/블로그 검색은 대부분
    # "출시일"을 명시하지 않아 신뢰도가 낮으므로 다나와에 없을 때만 보조로 사용
    release_date = (danawa_result or {}).get("release_date")
    if not release_date:
        release_date = ai_result.get("release_date") if isinstance(ai_result.get("release_date"), str) else None

    # 출시가는 다나와 실스크래핑 값을 최우선으로 신뢰 — AI 추출은 실제 검색 결과가 있을 때만 보조로 사용
    launch_price = price_block.get("launch_price") if price_block else None
    if launch_price is None:
        ai_launch_price = ai_result.get("launch_price")
        if isinstance(ai_launch_price, str):
            digits = re.sub(r'[^\d]', '', ai_launch_price)
            launch_price = int(digits) if digits else None
        elif isinstance(ai_launch_price, (int, float)):
            launch_price = int(ai_launch_price)

    report_summary = _clean_ai_text(ai_result.get("report_summary"))
    conclusion_reason = _clean_ai_text(ai_result.get("conclusion_reason")) or (
        {
            "buy":   f"현재 최저가가 역대 평균가 대비 {abs(price_block['vs_hist_pct'])}% 저렴해 매입 적기입니다.",
            "wait":  f"현재 최저가가 역대 평균가 대비 {price_block['vs_hist_pct']}% 비싸 가격 하락을 기다리는 편이 좋습니다.",
            "avoid": f"가격이 역대 평균가 대비 {price_block['vs_hist_pct']}% 비싼데 관심도까지 하락 추세라 매입을 권하지 않습니다.",
        }[price_block["signal_type"]] if price_block else "가격 데이터가 부족해 판단하기 어렵습니다."
    )
    price_change_reason = _clean_ai_text(ai_result.get("price_change_reason")) or (
        (
            f"최근 이력 동안 최저 {price_block['hist_min_price']:,}원~최고 {price_block['hist_max_price']:,}원 "
            f"사이를 오가며 최대 {price_block['price_range_pct']}% 변동했고, 이력 기간 순변동은 {price_block['price_change_pct']}%입니다."
        )
        if price_block and price_block.get("price_change_pct") is not None and price_block.get("price_range_pct") is not None
        else None
    )
    price_fairness_reason = _clean_ai_text(ai_result.get("price_fairness_reason")) or (
        f"현재가가 이력 평균 대비 {price_block['vs_hist_pct']}%로 {price_block['fairness_label']}입니다." if price_block else None
    )
    # "AI 수요 예측"은 검색 관심도(브랜드/제품라인 단위까지만 실재하는 데이터 — 완전한
    # 모델명으로는 데이터랩 검색량이 0건인 걸 직접 확인함) 대신, 이 정확한 단일 제품(SKU)
    # 자체의 실제 가격 이력(다나와+DB로 이 제품만 추적)을 기준으로 삼는다. 검색량 기반으로는
    # 같은 브랜드/라인의 다른 제품이 전부 같은 수치를 보일 수밖에 없었지만, 가격 이력은
    # 제품마다 실제로 다른 진짜 시계열이라 SKU별로 다른 값이 나온다.
    price_trend_pct = None
    demand_headline = None
    demand_reason = None
    if price_block and len(price_block["price_history"]) >= 2:
        _price_pts = [{"period": r["date"], "ratio": r["avg_price"]} for r in price_block["price_history"]]
        _, _price_slope = _linear_trend_fit(_price_pts)
        _p_dir = "하락" if _price_slope < 0 else ("상승" if _price_slope > 0 else "보합")
        price_trend_pct = price_block["price_change_pct"]
        demand_headline = (
            f"이 제품의 실제 가격은 최근 {_p_dir}세이며, 이력 기간 순변동은 "
            f"{'+' if price_trend_pct >= 0 else ''}{price_trend_pct}%입니다."
        )
        # demand_reason은 AI에 맡기지 않고 항상 규칙 기반으로 만든다 — AI가 여기서도
        # (프롬프트 지시에도 불구하고) 낡은 "관심도" 언어를 섞어 headline의 실제 가격
        # 수치와 모순되는 문장을 만드는 경우가 있어(예: "가격은 안정적" vs 실제 +16.9%),
        # 이 필드는 실제 숫자로만 채운다.
        demand_reason = (
            f"최저 {price_block['hist_min_price']:,}원~최고 {price_block['hist_max_price']:,}원 사이에서 "
            f"등락(변동폭 {price_block['price_range_pct']}%)했고, "
            + (
                "가격이 계속 낮아지는 추세라 매수 심리에 유리한 국면입니다." if _p_dir == "하락"
                else "가격이 오르는 추세라 매입을 서두르는 편이 유리할 수 있습니다." if _p_dir == "상승"
                else "가격이 안정적인 편입니다."
            )
        )

    selected_pros = _drop_raw_echo_items(_drop_fairness_leak(_clean_list(ai_result.get("selected_pros"))), pos_reviews + neg_reviews)
    selected_cons = _drop_raw_echo_items(_drop_fairness_leak(_clean_list(ai_result.get("selected_cons"))), pos_reviews + neg_reviews)
    competitor_pros = _drop_raw_echo_items(
        _drop_fairness_leak(_drop_other_model_mentions(_clean_list(ai_result.get("competitor_pros")), competitor)), competitor_reviews
    ) if competitor else []
    competitor_cons = _drop_raw_echo_items(
        _drop_fairness_leak(_drop_other_model_mentions(_clean_list(ai_result.get("competitor_cons")), competitor)), competitor_reviews
    ) if competitor else []

    # 가격 비교는 AI에 맡기면 극성(장점/단점)을 반대로 쓰거나 엉뚱한 제품 가격과 헷갈리는 경우가
    # 있어, 실제 숫자로 시스템이 직접 비교해 정확한 방향으로만 장단점에 덧붙인다.
    if competitor and price_block:
        sel_price, comp_price = price_block["min_price"], competitor["price"]
        if sel_price < comp_price:
            diff = comp_price - sel_price
            selected_pros.append(f"경쟁 제품보다 {diff:,}원 저렴합니다.")
            competitor_cons.append(f"검색하신 제품보다 {diff:,}원 비쌉니다.")
        elif sel_price > comp_price:
            diff = sel_price - comp_price
            selected_cons.append(f"경쟁 제품보다 {diff:,}원 비쌉니다.")
            competitor_pros.append(f"검색하신 제품보다 {diff:,}원 저렴합니다.")

    def _is_raw_echo(summary: str | None, source_reviews: list[dict]) -> bool:
        """리뷰 스니펫이 잘려서 실제 불만/장점 내용이 없으면, AI가 요약 대신 원문 티저
        문장을 그대로 베껴 쓰는 경우가 있다 — 원문 리뷰 문장 하나를 통째로(35자 이상)
        베낀 경우만 원문 재탕으로 보고 버린다. 짧은 문구 재사용은 정상적인 요약에서도
        흔하므로(예: '소모품 교체 비용') 임계값을 낮게 잡으면 정상 요약까지 오탐한다."""
        if not summary:
            return False
        for r in source_reviews:
            text = r["text"]
            for i in range(0, max(len(text) - 35, 0) + 1, 10):
                if text[i:i + 35] and text[i:i + 35] in summary:
                    return True
        return False

    recommended = ai_result.get("recommended") if ai_result.get("recommended") in ("selected", "competitor") else None
    recommendation_reason = _clean_ai_text(ai_result.get("recommendation_reason"))
    positive_summary = _clean_ai_text(ai_result.get("positive_summary")) if pos_reviews else None
    negative_summary = _clean_ai_text(ai_result.get("negative_summary")) if neg_reviews else None
    if _is_raw_echo(positive_summary, pos_reviews):
        positive_summary = None
    if _is_raw_echo(negative_summary, neg_reviews):
        negative_summary = None

    result = {
        "query": q,
        "category": detected_category,
        "trend_keyword": trend_keyword,
        "model_number": model,

        # 1. 제품 기본 정보
        "product_info": {
            "name": q,
            "brand": product_brand,
            "image": product_image,
            "release_date": release_date,
            "launch_price": launch_price,
            "current_price": price_block["min_price"] if price_block else None,
        },

        # 2. AI 종합 리포트
        "ai_report": {
            "summary": report_summary,
            "conclusion": price_block["signal_type"] if price_block else None,
            "conclusion_label": price_block["signal"] if price_block else "데이터 부족",
            "conclusion_reason": conclusion_reason,
        },

        # 3. 판매량/검색량 추이 (기존 Prophet 차트 재사용)
        "interest_forecast": {
            "history":          trend_data,
            "linear_trend":     linear_trend_pts,
            "prophet_forecast": prophet_forecast,
            "rag_enhanced":     rag_enhanced,
            "reason":           interest_reason,
        },
        "sales_forecast": {
            "history":          sales_trend_data,
            "linear_trend":     sales_linear_trend_pts,
            "prophet_forecast": sales_prophet_forecast,
            "reason":           sales_reason,
        },

        # 4. 가격 변동 분석
        "price_change": {
            "history": price_block["price_history"] if price_block else [],
            "change_pct": price_block["price_change_pct"] if price_block else None,
            "range_pct": price_block["price_range_pct"] if price_block else None,
            "reason": price_change_reason,
        },

        # 5. 가격 적정성 분석
        "price_fairness": {
            "type":  price_block["fairness_type"] if price_block else None,
            "label": price_block["fairness_label"] if price_block else "데이터 부족",
            "vs_hist_pct": price_block["vs_hist_pct"] if price_block else None,
            "current_price": price_block["min_price"] if price_block else None,
            "hist_avg_price": price_block["hist_avg_price"] if price_block else None,
            "malls": price_block["malls"] if price_block else [],
            "reason": price_fairness_reason,
        },

        # 6. AI 수요 예측 (이 제품 고유의 실제 가격 이력 기준)
        "demand_forecast": {
            "headline": demand_headline,
            "reason": demand_reason,
            "price_trend_pct": price_trend_pct,
        },

        # 7. 경쟁 제품 비교
        "competitor_comparison": {
            "competitor": competitor,
            "selected_pros": selected_pros,
            "selected_cons": selected_cons,
            "competitor_pros": competitor_pros,
            "competitor_cons": competitor_cons,
            "recommended": recommended,
            "recommendation_reason": recommendation_reason,
        },

        # 8. 소비자 리뷰 감성 분석
        "review_sentiment": {
            "score": sentiment_score,
            "pos": pos_review_count,
            "neg": neg_review_count,
            "reviews": tagged_reviews,
            "positive_summary": positive_summary,
            "negative_summary": negative_summary,
        },
    }

    # AI 호출이 실패해서 ai_result가 비어있으면(리포트/장단점/요약이 텅 빈 결과) 정상 TTL로
    # 캐싱하면 다음 요청들이 전부 이 실패 결과를 그대로 재사용하게 된다 — 일시적 장애(레이트
    # 리밋 등)일 수 있으니 짧은 TTL만 주고 곧 재시도되게 한다.
    _ttl = _GROQ_TTL if ai_result else 60
    _GROQ_CACHE[_ck] = (_time.time() + _ttl, result)
    return result
