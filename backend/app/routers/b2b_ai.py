from fastapi import APIRouter, Depends, Query
from app.routers.b2b_utils import *

router = APIRouter()

_TREND_CTX_FALLBACK: dict[str, dict] = {
    "에어컨": {
        "peak_months": "6~8월", "off_months": "11~2월",
        "region":  [{"label":"서울","pct":25},{"label":"경기","pct":21},{"label":"부산","pct":16},{"label":"대구","pct":14},{"label":"인천","pct":10}],
        "install": [{"label":"벽걸이형","pct":48},{"label":"스탠드형","pct":32},{"label":"2in1","pct":12},{"label":"창문형","pct":8}],
        "purpose": [{"label":"냉방 성능","pct":35},{"label":"전기료 절감","pct":28},{"label":"AI 기능","pct":18},{"label":"저소음","pct":12},{"label":"디자인","pct":7}],
        "related": [{"label":"제습기","pct":31},{"label":"선풍기","pct":24},{"label":"공기청정기","pct":18},{"label":"서큘레이터","pct":15},{"label":"창문형에어컨","pct":12}],
    },
    "냉장고": {
        "peak_months": "연중", "off_months": "없음",
        "region":  [{"label":"서울","pct":28},{"label":"경기","pct":24},{"label":"부산","pct":14},{"label":"인천","pct":12},{"label":"대구","pct":10}],
        "install": [{"label":"일반형","pct":45},{"label":"양문형","pct":30},{"label":"4도어","pct":15},{"label":"소형","pct":10}],
        "purpose": [{"label":"용량","pct":35},{"label":"에너지효율","pct":25},{"label":"신선도","pct":20},{"label":"디자인","pct":12},{"label":"소음","pct":8}],
        "related": [{"label":"김치냉장고","pct":28},{"label":"정수기","pct":22},{"label":"전자레인지","pct":18},{"label":"식기세척기","pct":15},{"label":"와인냉장고","pct":17}],
    },
    "세탁기": {
        "peak_months": "3~5월", "off_months": "7~8월",
        "region":  [{"label":"서울","pct":27},{"label":"경기","pct":23},{"label":"부산","pct":15},{"label":"인천","pct":11},{"label":"대구","pct":9}],
        "install": [{"label":"드럼형","pct":55},{"label":"통돌이형","pct":30},{"label":"미니세탁기","pct":10},{"label":"벽걸이형","pct":5}],
        "purpose": [{"label":"세척력","pct":38},{"label":"에너지효율","pct":24},{"label":"소음","pct":18},{"label":"용량","pct":12},{"label":"건조 겸용","pct":8}],
        "related": [{"label":"건조기","pct":42},{"label":"세탁세제","pct":22},{"label":"스팀다리미","pct":16},{"label":"옷걸이","pct":12},{"label":"세탁망","pct":8}],
    },
    "건조기": {
        "peak_months": "10~12월", "off_months": "6~8월",
        "region":  [{"label":"서울","pct":30},{"label":"경기","pct":25},{"label":"부산","pct":13},{"label":"인천","pct":10},{"label":"대구","pct":9}],
        "install": [{"label":"콘덴서형","pct":50},{"label":"히트펌프형","pct":35},{"label":"벽걸이형","pct":15}],
        "purpose": [{"label":"빠른 건조","pct":35},{"label":"에너지효율","pct":28},{"label":"저소음","pct":18},{"label":"살균 기능","pct":12},{"label":"대용량","pct":7}],
        "related": [{"label":"세탁기","pct":45},{"label":"건조대","pct":20},{"label":"스팀다리미","pct":15},{"label":"에어드레서","pct":12},{"label":"세탁세제","pct":8}],
    },
    "공기청정기": {
        "peak_months": "3~5월", "off_months": "7~8월",
        "region":  [{"label":"서울","pct":30},{"label":"경기","pct":26},{"label":"부산","pct":13},{"label":"인천","pct":10},{"label":"대구","pct":8}],
        "install": [{"label":"스탠드형","pct":55},{"label":"소형","pct":28},{"label":"벽걸이형","pct":10},{"label":"차량용","pct":7}],
        "purpose": [{"label":"미세먼지 제거","pct":40},{"label":"바이러스 제거","pct":25},{"label":"냄새 제거","pct":18},{"label":"소음","pct":10},{"label":"디자인","pct":7}],
        "related": [{"label":"가습기","pct":32},{"label":"제습기","pct":25},{"label":"에어컨","pct":20},{"label":"서큘레이터","pct":15},{"label":"환풍기","pct":8}],
    },
    "로봇청소기": {
        "peak_months": "10~12월", "off_months": "4~6월",
        "region":  [{"label":"서울","pct":32},{"label":"경기","pct":27},{"label":"부산","pct":12},{"label":"인천","pct":9},{"label":"대구","pct":8}],
        "install": [{"label":"일반형","pct":60},{"label":"물걸레형","pct":25},{"label":"올인원","pct":15}],
        "purpose": [{"label":"청소 편의","pct":42},{"label":"흡입력","pct":25},{"label":"물걸레 기능","pct":18},{"label":"소음","pct":8},{"label":"배터리","pct":7}],
        "related": [{"label":"진공청소기","pct":35},{"label":"물걸레청소기","pct":28},{"label":"스팀청소기","pct":18},{"label":"청소포","pct":12},{"label":"공기청정기","pct":7}],
    },
    "TV": {
        "peak_months": "11~1월", "off_months": "5~7월",
        "region":  [{"label":"서울","pct":26},{"label":"경기","pct":22},{"label":"부산","pct":15},{"label":"인천","pct":11},{"label":"대구","pct":10}],
        "install": [{"label":"벽걸이형","pct":55},{"label":"스탠드형","pct":35},{"label":"이동형","pct":10}],
        "purpose": [{"label":"화질","pct":38},{"label":"크기","pct":25},{"label":"스마트 기능","pct":18},{"label":"음질","pct":12},{"label":"디자인","pct":7}],
        "related": [{"label":"사운드바","pct":35},{"label":"HDMI케이블","pct":22},{"label":"OTT 구독","pct":18},{"label":"게임콘솔","pct":15},{"label":"TV받침대","pct":10}],
    },
    "식기세척기": {
        "peak_months": "3~5월", "off_months": "7~9월",
        "region":  [{"label":"서울","pct":29},{"label":"경기","pct":25},{"label":"부산","pct":13},{"label":"인천","pct":11},{"label":"대구","pct":9}],
        "install": [{"label":"빌트인형","pct":40},{"label":"일반형","pct":38},{"label":"미니형","pct":22}],
        "purpose": [{"label":"세척력","pct":35},{"label":"용량","pct":25},{"label":"건조 성능","pct":20},{"label":"소음","pct":12},{"label":"에너지효율","pct":8}],
        "related": [{"label":"냉장고","pct":30},{"label":"세제","pct":28},{"label":"가스레인지","pct":18},{"label":"음식물처리기","pct":14},{"label":"전자레인지","pct":10}],
    },
}
_GENERIC_FALLBACK = {
    "peak_months": "연중", "off_months": "없음",
    "region":  [{"label":"서울","pct":26},{"label":"경기","pct":22},{"label":"부산","pct":15},{"label":"인천","pct":11},{"label":"대구","pct":10}],
    "install": [{"label":"일반형","pct":50},{"label":"소형","pct":28},{"label":"대형","pct":22}],
    "purpose": [{"label":"성능","pct":35},{"label":"에너지효율","pct":25},{"label":"가격","pct":20},{"label":"디자인","pct":12},{"label":"소음","pct":8}],
    "related": [{"label":"관련제품1","pct":35},{"label":"관련제품2","pct":28},{"label":"관련제품3","pct":18},{"label":"관련제품4","pct":12},{"label":"관련제품5","pct":7}],
}


@router.get("/ai-report")
async def get_ai_report(category: str = Query(..., min_length=1), period: str = "3m", _: dict = Depends(require_b2b)):
    import json as _json
    from app.dependencies import get_rag_optional

    # ── 캐시 확인 ──
    _ck = f"ai-report:{_CACHE_VER}:{category}:{period}"
    _cached = _GROQ_CACHE.get(_ck)
    if _cached and _time.time() < _cached[0]:
        return _cached[1]

    # Supabase DB 캐시 확인 (인메모리 미스 시)
    from app.services.naver_cache import get_db_cache as _get_ai_db_cache, set_db_cache as _set_ai_db_cache
    _db_ai_key = f"ai_report:{_CACHE_VER}:{category}:{period}"
    _db_ai = await _get_ai_db_cache(_db_ai_key)
    if _db_ai:
        _GROQ_CACHE[_ck] = (_time.time() + _GROQ_TTL, _db_ai)
        return _db_ai

    rag = get_rag_optional()

    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = days_map.get(period, 90)
    time_unit = "week" if days > 30 else "date"
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    dl_headers = {**NAVER_HEADERS, "Content-Type": "application/json"}

    async def _fetch_trend():
        body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate":   end_date.strftime("%Y-%m-%d"),
            "timeUnit":  time_unit,
            "keywordGroups": [{"groupName": category, "keywords": [category]}],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://openapi.naver.com/v1/datalab/search", json=body, headers=dl_headers)
        results = resp.json().get("results", [])
        return results[0]["data"] if results else []

    async def _fetch_brands():
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                headers=NAVER_HEADERS,
                params={"query": category, "display": 100, "sort": "sim"},
            )
        counts: dict[str, int] = {}
        for it in resp.json().get("items", []):
            b = it.get("maker", "").strip() or it.get("brand", "").strip()
            if b:
                counts[b] = counts.get(b, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
        total = sum(v for _, v in top)
        return [{"brand": k, "count": v, "pct": round(v / total * 100) if total else 0} for k, v in top]

    # 대시보드 캐시에 트렌드가 있으면 DataLab 재호출 없이 재사용
    _cached_trend = None
    for _p in (period, "3m", "1m", "6m", "1y"):
        _dc = _GROQ_CACHE.get(f"dashboard:{_CACHE_VER}:{category}:{_p}")
        if _dc and _time.time() < _dc[0] and _dc[1].get("trend"):
            _cached_trend = _dc[1]["trend"]
            break

    # 인메모리 미스 시 Supabase DB 캐시 확인 (Render 해외 차단 대비)
    if _cached_trend is None:
        from app.services.naver_cache import get_db_cache as _get_db_cache
        for _p in (period, "3m", "1m", "6m", "1y"):
            _db_data = await _get_db_cache(f"naver_dashboard:{category}:{_p}")
            if _db_data and _db_data.get("trend"):
                _cached_trend = _db_data["trend"]
                break

    if _cached_trend is not None:
        brand_data = await _fetch_brands()
        brand_data = brand_data if not isinstance(brand_data, Exception) else []
        trend_data = _cached_trend
    else:
        trend_data, brand_data = await asyncio.gather(_fetch_trend(), _fetch_brands(), return_exceptions=True)
        trend_data = trend_data if not isinstance(trend_data, Exception) else []
        brand_data = brand_data if not isinstance(brand_data, Exception) else []

    # DataLab 최신 주 미집계 trailing 저비율 데이터 제거
    while len(trend_data) > 4 and trend_data[-1]["ratio"] < trend_data[-2]["ratio"] * 0.3:
        trend_data = trend_data[:-1]

    ratios  = [d["ratio"] for d in trend_data]
    current = round(ratios[-1], 1) if ratios else 0
    avg_val = round(sum(ratios) / len(ratios), 1) if ratios else 0
    half    = len(ratios) // 2
    old_avg = sum(ratios[:half]) / max(half, 1)
    new_avg = sum(ratios[half:]) / max(len(ratios) - half, 1)
    growth  = round((new_avg - old_avg) / max(old_avg, 1) * 100, 1)
    risk    = _calc_risk(growth)

    top3       = ", ".join(f"{b['brand']} {b['pct']}%" for b in brand_data[:3]) or "데이터 부족"
    top_brand  = brand_data[0]["brand"] if brand_data else "데이터 없음"

    report = {
        "action":               "관망",
        "action_reason":        "데이터를 분석 중입니다",
        "timing":               "-",
        "inventory_advice":     "-",
        "opportunity":          [],
        "risk_summary":         [],
        "brand_focus":          top_brand,
        "summary":              f"{category} 시장 분석 결과입니다.",
        "action_basis":         [],
        "target_segment":       "-",
        "price_range":          "-",
        "key_keywords":         [],
        "recommended_products": "-",
        "risk_factor":          "-",
        "product_strategy":     [],
        "sales_strategy":       [],
        "service_strategy":     [],
        "summary_lines":        [],
        # 소비자 니즈 및 상품 기획
        "product_brief":        "-",
        "consumer_needs":       [],
        "consumer_complaints":  [],
        "recommended_features": [],
        "needs_basis":          "-",
        # 예상 효과
        "expected_sales_growth": "-",
        "expected_effects":      [],
        "projection_summary":    "-",
        # AI 의사결정 & 신뢰도
        "decision_chain":        [],
        "ai_confidence":         0,
        "confidence_breakdown":  [],
        # 이번 주 Action List
        "action_list":           [],
    }

    # 카테고리별 시장 맥락 (설치 형태 / 구매 목적 / 연관 가전)
    ctx = _TREND_CTX_FALLBACK.get(category, _GENERIC_FALLBACK)
    top_install  = ctx["install"][0]["label"] if ctx.get("install") else "-"
    top_related  = ctx["related"][0]["label"] if ctx.get("related") else "-"
    top_purpose  = ctx["purpose"][0]["label"] if ctx.get("purpose") else "-"
    sec_purpose  = ctx["purpose"][1]["label"] if len(ctx.get("purpose", [])) > 1 else top_purpose
    top_related2 = ctx["related"][1]["label"] if len(ctx.get("related", [])) > 1 else top_related
    peak_months  = ctx.get("peak_months", "연중")
    off_months   = ctx.get("off_months", "-")
    install_str  = " / ".join(f"{x['label']} {x['pct']}%" for x in ctx.get("install", [])[:3])
    related_str  = " / ".join(f"{x['label']} {x['pct']}%" for x in ctx.get("related", [])[:3])
    purpose_str  = " / ".join(f"{x['label']} {x['pct']}%" for x in ctx.get("purpose", [])[:3])

    # 트렌드 방향성 — /demand-forecast가 같은 카테고리로 이미 계산해둔 예측 기반 추세가 있으면
    # 그걸 그대로 따라서 '미래예측' 페이지와 '종합 리포트 AI 최종 판단' 문구가 어긋나지 않게 한다.
    # 캐시가 없으면(아직 forecast를 조회한 적 없는 카테고리) 과거 관심도 증감(growth)으로 대체 판단한다.
    _fc_dir = None
    for _p in (period, "3m", "1m", "6m", "1y"):
        _fc = _GROQ_CACHE.get(f"forecast:{_CACHE_VER}:{category}:{_p}")
        if _fc and _time.time() < _fc[0]:
            _fc_dir = _fc[1].get("trend_dir")
            break
    if _fc_dir:
        trend_dir_str = "상승세" if _fc_dir == "상승" else "하락세" if _fc_dir == "하락" else "보합세"
    else:
        trend_dir_str = "상승세" if growth > 5 else "하락세" if growth < -5 else "보합세"

    # ── 키워드/불만 데이터 — 대시보드 캐시 우선, 없으면 경량 fetch ──
    async def _fetch_top_keywords() -> list[dict]:
        raw = await search_products(query=category, page=1, display=30, sort="sim", category=category)
        items = raw.get("items", [])
        KW_STOP = _STOP | {"미포함","포함","수도권","설치비포함","설치비별도","방문설치",
                           "무료설치","무료","별도","이하","이상","할인","택배","직접",
                           "기사","배송","셀프","자가설치","원룸","평","인치"}
        def _is_valid(w: str) -> bool:
            w = w.strip()
            return bool(w) and len(w) >= 2 and w != category and w not in KW_STOP \
                and not re.match(r'^[A-Za-z]{1,4}$', w) and not any(c.isdigit() for c in w)
        counts: Counter = Counter()
        for it in items:
            t = strip_html(it.get("title", ""))
            for src in (it.get("brand") or "", it.get("maker") or "",
                        it.get("category3") or "", it.get("category4") or ""):
                if _is_valid(src): counts[src] += 1
            for tok in re.sub(r'[^가-힣a-zA-Z\s]', ' ', t).split():
                if _is_valid(tok): counts[tok] += 1
        return [{"word": w, "count": c} for w, c in counts.most_common(10)]

    # ── 키워드/불만 데이터 구조화 ──
    _top_keywords: list[dict] = []
    _raw_complaints: list[dict] = []  # [{rank, brand, complaint:[], evidence:{}}]

    for _p in (period, "3m", "1m", "6m", "1y"):
        _dash = _GROQ_CACHE.get(f"dashboard:{_CACHE_VER}:{category}:{_p}")
        if _dash and _time.time() < _dash[0] and _dash[1].get("keywords"):
            _top_keywords = _dash[1]["keywords"][:10]
            break

    _comp_cache = _GROQ_CACHE.get(f"complaints:{category}")
    if _comp_cache and _time.time() < _comp_cache[0]:
        _cv = _comp_cache[1] or []
        _raw_complaints = _cv.get("items", []) if isinstance(_cv, dict) else _cv
    else:
        # complaints 별도 캐시 미스 → dashboard 캐시 또는 DB 캐시에서 fallback
        for _p in (period, "3m", "1m", "6m", "1y"):
            _dash2 = _GROQ_CACHE.get(f"dashboard:{_CACHE_VER}:{category}:{_p}")
            if _dash2 and _time.time() < _dash2[0] and _dash2[1].get("complaints"):
                _raw_complaints = _dash2[1]["complaints"]
                break
        if not _raw_complaints:
            try:
                from app.services.naver_cache import get_db_cache as _get_db_cache2
                _db_comp = await _get_db_cache2(f"naver_dashboard:{category}:{period}")
                if _db_comp and _db_comp.get("complaints"):
                    _raw_complaints = _db_comp["complaints"]
            except Exception:
                pass

    if not _top_keywords:
        try:
            _top_keywords = await _fetch_top_keywords()
        except Exception:
            _top_keywords = []

    # 키워드: 빈도 포함 문자열
    top_kw_str = ", ".join(
        f"{x['word']}({x['count']}건)" for x in _top_keywords[:10]
    ) or "데이터 없음"

    # 불만: 태그별 등장 브랜드 수 + evidence 요약
    _comp_freq: Counter = Counter()
    _comp_evidence: dict[str, str] = {}
    _comp_brands: dict[str, list[str]] = {}
    for item in _raw_complaints:
        brand = item.get("brand") or item.get("product", "")[:6]
        evid  = item.get("evidence", {})
        for tag in item.get("complaint", []):
            if not tag:
                continue
            _comp_freq[tag] += 1
            if tag not in _comp_brands:
                _comp_brands[tag] = []
            if brand and brand not in _comp_brands[tag]:
                _comp_brands[tag].append(brand)
            if tag not in _comp_evidence and evid.get(tag):
                _comp_evidence[tag] = evid[tag][:60]

    # 빈도순 상위 8개, 각각 "태그(N개 브랜드): 근거문장 앞부분"
    _comp_lines = []
    for tag, freq in _comp_freq.most_common(8):
        brands_str = "/".join(_comp_brands.get(tag, [])[:3])
        evid_str   = _comp_evidence.get(tag, "")
        line = f"{tag}({freq}개 제품"
        if brands_str:
            line += f", {brands_str}"
        line += ")"
        if evid_str:
            line += f": {evid_str}"
        _comp_lines.append(line)

    complaint_str = "\n  ".join(_comp_lines) if _comp_lines else "데이터 없음"

    _first_kw   = _top_keywords[0]["word"] if _top_keywords else None
    _first_comp = next(iter(_comp_freq), None) if _comp_freq else None

    try:
        # 공공데이터 환경 신호 로드 (병렬)
        rag_task = rag.query(f"{category} 소비자 반응 구매 결정 트렌드", n_results=8) if rag else asyncio.sleep(0)
        env_task = _load_env_signal(category)
        rag_chunks_raw, _env = await asyncio.gather(rag_task, env_task, return_exceptions=True)

        rag_context = ""
        if isinstance(rag_chunks_raw, list) and rag_chunks_raw:
            rag_context = "\n[소비자 실반응 RAG 데이터]\n" + "\n".join(f"- {c[:_RAG_CHUNK_LEN]}" for c in rag_chunks_raw)

        # 환경 신호 문자열 구성
        _env_str = ""
        if isinstance(_env, dict) and _env.get("vars"):
            _ev = _env["vars"]
            parts = []
            if "kma_temp" in _ev:
                parts.append(f"기온 {_ev['kma_temp']}°C · 습도 {_ev.get('kma_humidity', '-')}%")
            if "air_pm25" in _ev:
                _grade = "매우나쁨" if _ev['air_pm25'] >= 76 else "나쁨" if _ev['air_pm25'] >= 36 else "보통" if _ev['air_pm25'] >= 16 else "좋음"
                parts.append(f"PM2.5 {_ev['air_pm25']}㎍/㎥({_grade})")
            if "kca_count" in _ev:
                parts.append(f"소비자원 피해접수 {_ev['kca_count']}건")
            if "kemco_grade1" in _ev:
                parts.append(f"에너지 1등급 비율 {_ev['kemco_grade1']}% (총 {_ev.get('kemco_total', '?')}개 인증제품 중)")
            if parts:
                _sig_labels = " / ".join(s["label"] for s in _env.get("signals", []))
                _env_str = f"\n■ 외부 환경 신호 (공공데이터 기준)\n  {' · '.join(parts)}\n  → {_sig_labels if _sig_labels else '현재 수요 영향 없음'}\n"

        # KCA 공식 불만 데이터 보강
        if not _raw_complaints and isinstance(_env, dict) and _env.get("vars", {}).get("kca_count"):
            from app.services.naver_cache import get_db_cache as _gc_kca
            _kca = await _gc_kca(f"ext:kca:{category}")
            if _kca and _kca.get("items"):
                for item in _kca["items"][:20]:
                    _raw_complaints.append({
                        "brand": item.get("product", "")[:10],
                        "complaint": [item.get("content", "")[:30]],
                        "evidence": {},
                    })

        _growth_pct = f"{'+' if growth >= 0 else ''}{growth}%"
        _buy_lead_prompt = 14 if time_unit == "date" else (21 if time_unit == "week" else 45)
        prompt = (
            f"[{category} B2B 시장 실측 데이터 — {period}]\n\n"
            f"■ 검색 트렌드\n"
            f"  현재 관심도: {current} / 기간 평균: {avg_val} / 변화율: {_growth_pct} ({trend_dir_str})\n\n"
            f"■ 브랜드 경쟁 구도\n"
            f"  {top3}\n\n"
            f"{_env_str}"
            f"■ 소비자 구매 맥락\n"
            f"  설치 형태: {install_str}\n"
            f"  구매 목적: {purpose_str}\n"
            f"  연관 제품: {related_str}\n"
            f"  성수기: {peak_months} / 비수기: {off_months} / 위험도: {risk}\n\n"
            f"■ 실제 쇼핑 검색 키워드 TOP10 (빈도)\n"
            f"  {top_kw_str}\n"
            f"  → 소비자가 실제로 검색하는 단어들. 제품 기획 시 이 키워드가 반영된 기능을 우선 고려.\n\n"
            f"■ 실측 소비자 불만 (블로그·카페·유튜브 스크래핑, 빈도순)\n"
            f"  {complaint_str}\n"
            f"  → 각 불만은 실제 후기/리뷰에서 수집된 데이터. 이 불만을 해소하는 기능이 시장 공백.\n"
            f"{rag_context}\n\n"
            f"위 실측 데이터를 근거로 아래 JSON을 작성하세요. 일반론 금지 — 반드시 위 데이터의 구체적 수치·키워드·불만을 인용해 작성:\n"
            f'{{\n'
            f'  "action": "매입 확대 또는 매입 유지 또는 재고 축소 또는 관망 중 하나",\n'
            f'  "action_reason": "행동 권고 이유를 구체적 수치와 시장 근거를 포함해 2~3문장으로 작성 (예: 검색 관심도 {current}으로 기간 평균 {avg_val} 대비 {trend_dir_str}이며, 성수기({peak_months}) 진입을 앞두고 수요 확대가 예상됩니다. {top_brand} 중심 시장 집중도가 높아 {top_purpose} 소비층 공략 시 효과적입니다.)",\n'
            f'  "timing": "권장 매입 시기와 이유 (예: 성수기 {peak_months} 2~4주 전 선매입 권장)",\n'
            f'  "inventory_advice": "구체적 재고 조정 방향 (예: 현재 수준 대비 10~15% 확대, {top_brand} 비중 우선)",\n'
            f'  "action_basis": [\n'
            f'    "검색 관심도 근거: 현재 {current}, 기간 평균 {avg_val} 대비 {trend_dir_str} ({_growth_pct}) — 시장 수요 방향 해석",\n'
            f'    "성수기·계절 근거: 성수기 {peak_months} 기준 시장 진입 타이밍 분석",\n'
            f'    "브랜드·경쟁 근거: {top3} 점유 구조에서 매입 전략 근거",\n'
            f'    "소비자 수요 근거: {top_purpose} / {sec_purpose} 구매 목적 기반 수요 판단"\n'
            f'  ],\n'
            f'  "opportunity": [\n'
            f'    {{"title": "성수기 진입", "evidence": "{peak_months} 성수기 전 관심도 {trend_dir_str} 흐름 확인, 수요 집중 예상", "meaning": "성수기 {peak_months} 2~4주 전 선매입으로 기회 선점 가능"}},\n'
            f'    {{"title": "소비자 니즈 명확화", "evidence": "{top_purpose}·{sec_purpose} 키워드 실수요 상위 확인", "meaning": "기능 중심 상품 구성이 판매 전환율 향상에 유리"}},\n'
            f'    {{"title": "연관 구매 가능성", "evidence": "{top_related}·{top_related2} 등 연관 가전 동반 언급 빈도 높음", "meaning": "패키지·번들 판매 기회로 객단가 상승 가능"}}\n'
            f'  ],\n'
            f'  "risk_summary": [\n'
            f'    {{"title": "브랜드 경쟁 심화", "evidence": "{top3} 상위 브랜드 집중 구조", "meaning": "단순 가격 경쟁보다 기능 차별화 및 서비스 강화 필요"}},\n'
            f'    {{"title": "비수기 재고 부담", "evidence": "{off_months} 수요 급감 이력 존재", "meaning": "과잉 매입 시 재고 회전 저하 및 운영비용 상승 위험"}},\n'
            f'    {{"title": "계절성 리스크", "evidence": "성수기({peak_months}) 외 검색 관심도 급격히 하락", "meaning": "{off_months} 비수기 재고 운영 비용 관리 필요"}}\n'
            f'  ],\n'
            f'  "target_segment": "구체적 소비 타깃 (예: 30~50대 {top_purpose} 중심 구매층)",\n'
            f'  "price_range": "데이터 기반 추천 가격대 (예: 50~120만원 프리미엄 라인)",\n'
            f'  "key_keywords": ["{category} 트렌드 키워드1", "키워드2", "키워드3", "키워드4"],\n'
            f'  "recommended_products": "구체적 추천 제품군 (예: {top_purpose}형 {category} 프리미엄 라인)",\n'
            f'  "risk_factor": "핵심 위험 요소 명사형 (20자 이내)",\n'
            f'  "summary": "4문장. 1문장: 검색 관심도 수치({current})와 {trend_dir_str} 흐름 기반 성수기({peak_months}) 수요 확대 가능성 해석. 2문장: {top_brand} 중심 시장에서 프리미엄 제품 전략과 경쟁 구도 분석. 3문장: 연관 가전 패키지 판매를 통한 객단가 상승 기회 서술. 4문장: 브랜드 경쟁 심화와 비수기 재고 부담 리스크 관리 방향 제언. 각 문장은 완결된 분석 문장으로 자연스럽게.",\n'
            f'  "product_strategy": [\n'
            f'    "{top_purpose} 중심 프리미엄 라인 비중 확대로 고마진 구조 구축",\n'
            f'    "{sec_purpose} 특화 기능 강화 모델 선별 매입으로 차별화 포지셔닝",\n'
            f'    "{top_install} 설치 환경 최적화 제품군 우선 선정으로 재구매율 제고"\n'
            f'  ],\n'
            f'  "sales_strategy": [\n'
            f'    "성수기({peak_months}) 2~4주 전 집중 프로모션으로 선점 효과 극대화",\n'
            f'    "{top_related}·{top_related2} 연관 제품 패키지 구성으로 객단가 상승 유도",\n'
            f'    "온라인 채널 리뷰 집중 관리 및 {top_brand} 중심 번들 기획으로 전환율 강화"\n'
            f'  ],\n'
            f'  "service_strategy": [\n'
            f'    "{top_install} 환경 전문 설치·AS 체계 강화로 재구매 고객 만족도 제고",\n'
            f'    "{top_purpose} 사용 품질 관리 및 구매 후 피드백 모니터링 체계 구축",\n'
            f'    "비수기({off_months}) 선제적 점검 서비스 제공으로 고객 이탈 방지"\n'
            f'  ],\n'
            f'  "product_brief": "위 쇼핑 키워드({top_kw_str})와 불만 데이터를 종합해 B2B 유통사가 지금 당장 기획·매입해야 할 구체적 제품 유형 1문장. 형식: [키워드 기반 제품 포지셔닝]을 [구체적 타깃층]에게 [가격대]로 → [불만 해소 포인트] 차별화",\n'
            f'  "consumer_needs": [\n'
            f'    "쇼핑 키워드 {_first_kw if _first_kw else top_kw_str.split(",")[0].split("(")[0].strip() if top_kw_str != "데이터 없음" else category} 등 고빈도 키워드가 시사하는 소비자의 핵심 필요 기능 (20자 이내, 구체적 기능명 포함)",\n'
            f'    "구매 목적 {top_purpose}({sec_purpose}) 데이터에서 도출한 실제 니즈 — 어떤 기능이 이를 충족하는가",\n'
            f'    "{top_install} 설치 환경 소비자가 필요로 하는 설계/편의 기능 — 재구매 결정 요인"\n'
            f'  ],\n'
            f'  "consumer_complaints": [\n'
            + (
            f'    "불만 1위({_first_comp}) → 이를 해소하는 구체적 제품 스펙/기능 포함 (예: 소음 5건 → 진동 저감 압축기 탑재 필요) (20자 이내)",\n'
            f'    "설치·AS 관련 불만 → 어떤 제품 설계·서비스 패키지로 해소 가능한지 (20자 이내)",\n'
            f'    "가격·성능 갭 관련 불만 → 어떤 스펙 조합이 해결책인지 (20자 이내)"\n'
            if _comp_freq else
            f'    "{category} {top_purpose} 소비자가 자주 겪는 불만1 — 어떤 기능으로 해소 가능한지 포함 (20자 이내)",\n'
            f'    "{category} 설치·AS 관련 예상 불만 → 해소 방안 포함",\n'
            f'    "{category} 가격·성능 관련 예상 불만 → 해소 방안 포함"\n'
            )
            + f'  ],\n'
            f'  "recommended_features": [\n'
            f'    "[기능명]: 쇼핑 키워드 {_first_kw or category} 수요 충족 + 불만({_first_comp or "주요 소비자 불만"}) 해소 — 시장 공백 직접 공략 (20자 이내)",\n'
            f'    "[기능명]: {top_purpose} 구매 목적 직접 충족 — 재구매율·객단가 상승 근거",\n'
            f'    "[기능명]: 불만 데이터 2·3위 키워드 해소 — {top_install} 환경 최적화",\n'
            f'    "[기능명]: {top_brand} 대비 차별화 포인트 — 경쟁 포지셔닝 근거"\n'
            f'  ],\n'
            f'  "needs_basis": "2문장. 1문장: 쇼핑 키워드 상위({_first_kw or category} 등)와 불만({_first_comp or "소비자 주요 불만"} 등) 데이터를 교차하면 현재 시장에 [이런 제품 유형]이 부재하며 이것이 기획 기회다 — 구체적 키워드·수치 인용 필수. 2문장: 위 기능 4가지를 탑재한 제품이 {top_brand} 중심 경쟁에서 차별화되는 이유와 예상 시장 효과.",\n'
            f'  "expected_sales_growth": "{category} 수요 방향성 서술 (구체적 % 수치 없이, 방향+근거만. 예: 성수기({peak_months}) 진입 및 {trend_dir_str} 흐름으로 관심도 상승 기대, {top_brand} 중심 프리미엄 수요 확대 가능성 높음)",\n'
            f'  "expected_effects": [\n'
            f'    "성수기 집중 매출 확대 (20자 이내, 예: {peak_months} 집중 매출 확대)",\n'
            f'    "프리미엄 제품 중심 객단가 상승 (20자 이내, 예: {top_purpose} 프리미엄 객단가 상승)",\n'
            f'    "연관 가전 패키지 판매 확대 (20자 이내, 예: 연관 가전 패키지 판매 확대)",\n'
            f'    "비수기 재고 손실 최소화 (20자 이내, 예: {off_months} 재고 손실 최소화)"\n'
            f'  ],\n'
            f'  "projection_summary": "예상 결과 종합 판단 2~3문장. 시장 방향({trend_dir_str}·위험도 {risk})·성수기({peak_months})·추천 전략 효과를 종합해 B2B 유통 관점 기대 결과 서술. 마지막 문장은 핵심 위험 요소 언급.",\n'
            f'  "decision_chain": [\n'
            f'    "검색 트렌드: 관심도 {current} ({trend_dir_str}, 기간 평균 대비 {_growth_pct})",\n'
            f'    "브랜드 집중도: {top3} — 경쟁 구도 분석",\n'
            f'    "성수기 신호: {peak_months} 진입 {_buy_lead_prompt}일 전 타이밍",\n'
            f'    "소비자 니즈: {top_purpose}·{_first_kw or category} 키워드 수요 집중"\n'
            f'  ],\n'
            f'  "ai_confidence": 75,\n'
            f'  "confidence_breakdown": [\n'
            f'    {{"factor": "검색 데이터 최신성", "pct": 95}},\n'
            f'    {{"factor": "가격 데이터 품질", "pct": 91}},\n'
            f'    {{"factor": "리뷰 데이터", "pct": 36}},\n'
            f'    {{"factor": "예측 신뢰도", "pct": 75}}\n'
            f'  ],\n'
            f'  "action_list": [\n'
            f'    {{"stars":5,"action":"실제 행동 중심 제목 (예: 성수기 전 재고 20% 확대)","dept":"구매","timing":"이번 주","budget":"500만원"}},\n'
            f'    {{"stars":5,"action":"실제 행동 중심 제목 (예: {top_brand} 경쟁 모델 가격 비교 점검)","dept":"마케팅","timing":"7일 이내","budget":"300만원"}},\n'
            f'    {{"stars":4,"action":"실제 행동 중심 제목 (예: {top_purpose} 타겟 프로모션 기획)","dept":"상품기획","timing":"2주 이내","budget":"별도 없음"}},\n'
            f'    {{"stars":3,"action":"실제 행동 중심 제목","dept":"영업","timing":"이번 달","budget":"별도 없음"}},\n'
            f'    {{"stars":2,"action":"실제 행동 중심 제목","dept":"기획","timing":"다음 달","budget":"별도 없음"}}\n'
            f'  ]\n'
            f'}}\n\n'
            f'[규칙] 1.consumer_needs·complaints·features는 위 실제 키워드 직접 인용. 2.features는 "[기능명]:근거" 형식. '
            f'3.action_basis 수치({current},{_growth_pct}) 인용. 4.% 수치는 근거 있을 때만. '
            f'5.일반론("보통","대체로") 금지. 6.ai_confidence 0~100 정수. confidence_breakdown의 pct는 "참고 비중"이 아니라 '
            f'각 데이터 항목 자체의 품질·신뢰도(%)이므로 항목별로 독립적으로 평가하고 합이 100일 필요 없음 '
            f'(예: 리뷰 데이터처럼 수집량이 적은 항목은 낮게, 검색·가격처럼 실시간 수집되는 항목은 높게). '
            f'7.action_list 5개: {category}에 실제로 맞는 구체적 행동 제목(예: "성수기 전 재고 OO% 확대", "{top_brand} 대비 가격 재점검"), '
            f'"{category} 시급 실행항목"처럼 카테고리명만 붙인 추상적 제목 금지. action 20자이내, dept=상품기획/마케팅/구매/영업 중 택1, budget 현실적 금액.'
        )

        res = await _groq_create(
            messages=[
                {"role": "system", "content": "당신은 B2B 가전 유통 전략 어드바이저입니다. 기업 보고서 수준의 구체적 수치·근거·카테고리 특성을 반영한 분석을 작성하세요. 일반론 없이 데이터 기반으로 작성하며, 순수 JSON만 출력하세요."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.3,
        )
        raw = res.choices[0].message.content.strip()
        # JSON 범위 추출 ({...}) — 마크다운 코드블록·앞뒤 텍스트 모두 처리
        _start, _end = raw.find('{'), raw.rfind('}')
        if _start != -1 and _end > _start:
            parsed = _json.loads(raw[_start:_end + 1])
        else:
            parsed = _json.loads(raw)
        report.update({k: v for k, v in parsed.items() if k in report})

        # summary → summary_lines: 숫자.숫자는 분리하지 않는 문장 분리
        import re as _re
        _summary = report.get("summary", "")
        # '. ' 앞이 숫자가 아닌 경우만 split (예: 3.5% 는 유지, '합니다. 50대+' 는 분리)
        _lines = _re.split(r'(?<!\d)\. ', _summary)
        report["summary_lines"] = [s.strip().rstrip('.') + '.' if s.strip() else ''
                                   for s in _lines if s.strip()]
    except Exception as e:
        report["_groq_error"] = repr(e)[:300]
        report["action_reason"] = "AI 분석을 일시적으로 사용할 수 없습니다. 잠시 후 새로고침 해주세요."
        report["summary"] = f"{category} 시장 데이터 수집은 완료됐으나 AI 분석 서버가 일시적으로 한도에 도달했습니다."

    result = {
        "category": category,
        "period":   period,
        "metrics": {
            "trend_score": current,
            "avg_score":   avg_val,
            "growth_rate": growth,
            "risk":        risk,
        },
        "brands":  brand_data,
        "report":  report,
        "context": {
            "peak_months": ctx.get("peak_months", "-"),
            "off_months":  ctx.get("off_months",  "-"),
            "install":     ctx.get("install", []),
            "purpose":     ctx.get("purpose", []),
            "related":     ctx.get("related", []),
            "region":      ctx.get("region",  []),
        },
    }
    if "_groq_error" not in report:
        _GROQ_CACHE[_ck] = (_time.time() + _GROQ_TTL, result)
        try:
            await _set_ai_db_cache(_db_ai_key, result, ttl_hours=8)
        except Exception:
            pass
    else:
        # AI 실패 시 만료된 DB 캐시라도 반환 (에러 화면 대신)
        try:
            from app.services.naver_cache import get_db_cache_stale as _get_stale
            _stale = await _get_stale(_db_ai_key)
            if _stale:
                return _stale
        except Exception:
            pass
    return result


@router.get("/demand-forecast")
async def get_demand_forecast(category: str = Query(..., min_length=1), period: str = "3m", _: dict = Depends(require_b2b)):
    import logging
    import numpy as np
    try:
        import pandas as pd
        from prophet import Prophet
        _PROPHET_AVAIL = True
    except ImportError:
        _PROPHET_AVAIL = False
    from app.dependencies import get_rag_optional
    rag = get_rag_optional()

    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = days_map.get(period, 90)
    if days <= 30:
        time_unit = "date"
    elif days < 365:
        time_unit = "week"
    else:
        time_unit = "month"

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    dl_headers = {**NAVER_HEADERS, "Content-Type": "application/json"}

    # ── 표시용 데이터: 선택한 period ──────────────────────────────────────────
    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate":   end_date.strftime("%Y-%m-%d"),
        "timeUnit":  time_unit,
        "keywordGroups": [{"groupName": category, "keywords": [category]}],
    }
    # ── 학습용 데이터: 항상 2년치 주별 (Prophet 연간 패턴 학습 위해) ──────────
    train_start = end_date - timedelta(days=730)
    train_body = {
        "startDate": train_start.strftime("%Y-%m-%d"),
        "endDate":   end_date.strftime("%Y-%m-%d"),
        "timeUnit":  "week",
        "keywordGroups": [{"groupName": category, "keywords": [category]}],
    }
    # 대시보드 캐시에 트렌드 데이터가 있으면 DataLab 재호출 없이 재사용
    trend_data = []
    for _p in (period, "3m", "1m", "6m", "1y"):
        _dc = _GROQ_CACHE.get(f"dashboard:{_CACHE_VER}:{category}:{_p}")
        if _dc and _time.time() < _dc[0] and _dc[1].get("trend"):
            trend_data = _dc[1]["trend"]
            break

    train_data = []
    if not trend_data:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp, train_resp = await asyncio.gather(
                    client.post("https://openapi.naver.com/v1/datalab/search", json=body, headers=dl_headers),
                    client.post("https://openapi.naver.com/v1/datalab/search", json=train_body, headers=dl_headers),
                )
            results = resp.json().get("results", [])
            trend_data = results[0]["data"] if results else []
            train_results = train_resp.json().get("results", [])
            train_data = train_results[0]["data"] if train_results else trend_data
        except Exception:
            return {"error": "네이버 DataLab 응답 지연 — 잠시 후 다시 시도해주세요"}
    else:
        # 캐시 트렌드는 표시용. 학습용(2년치)은 별도 fetch
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                train_resp = await client.post(
                    "https://openapi.naver.com/v1/datalab/search", json=train_body, headers=dl_headers
                )
            train_results = train_resp.json().get("results", [])
            train_data = train_results[0]["data"] if train_results else trend_data
        except Exception:
            train_data = trend_data

    if not trend_data:
        return {"error": "트렌드 데이터를 불러올 수 없습니다"}

    # DataLab 최신 집계 지연으로 인한 trailing 저비율 데이터 제거
    def _trim_trailing(data, unit="week"):
        # 주별/월별은 마지막 1포인트 제거 (현재 주/월은 집계 미완료)
        if unit != "date" and len(data) > 6:
            data = data[:-1]
        # 추가로 직전 대비 70% 미만 포인트도 제거
        while len(data) > 4 and data[-1]["ratio"] < data[-2]["ratio"] * 0.7:
            data = data[:-1]
        return data

    trend_data = _trim_trailing(trend_data, time_unit)
    train_data = _trim_trailing(train_data, "week")

    # 1m(date)는 일별 데이터로 단기 정확도 유지, 그 외는 2년 주별 학습 데이터 사용
    if time_unit == "date":
        df = pd.DataFrame({
            "ds": pd.to_datetime([d["period"] for d in trend_data]),
            "y":  [float(d["ratio"]) for d in trend_data],
        })
    else:
        df = pd.DataFrame({
            "ds": pd.to_datetime([d["period"] for d in train_data]),
            "y":  [float(d["ratio"]) for d in train_data],
        })

    freq_map     = {"date": "D", "week": "W", "month": "MS"}
    forecast_map = {"date": 14,  "week": 22,  "month": 6}
    freq         = freq_map[time_unit]
    forecast_n   = forecast_map[time_unit]

    hist_max  = float(df["y"].max())  if not df.empty else 100.0
    hist_mean = float(df["y"].mean()) if not df.empty else 50.0
    forecast_cap = max(hist_max * 1.5, hist_mean * 3.0)

    # ── 공공데이터 외부 변수 로드 (Prophet/XGBoost 공용) ──────────────────────
    from app.services.public_data import get_ext_dataframe
    _ext_df = None
    _ext_cols_used: list[str] = []  # 실제 모델에 반영된 외부 변수 목록
    try:
        _ext_df = await get_ext_dataframe(category, df["ds"])
    except Exception as _e:
        logger.warning("[ExtData] 외부 변수 로드 실패 (%s): %s", category, _e)

    # 외부 변수 → 출처 메타 매핑
    _EXT_SOURCE_META = {
        "kma_temp":     {"name": "기상청 ASOS", "var": "기온(℃)", "provider": "data.go.kr"},
        "kma_humidity": {"name": "기상청 ASOS", "var": "습도(%)", "provider": "data.go.kr"},
        "air_pm25":     {"name": "에어코리아",   "var": "PM2.5(㎍/㎥)", "provider": "data.go.kr"},
        "air_pm10":     {"name": "에어코리아",   "var": "PM10(㎍/㎥)",  "provider": "data.go.kr"},
        "kepco_rate":   {"name": "한국전력공사", "var": "전기요금(원/kWh)", "provider": "bigdata.kepco.co.kr"},
        "customs_tv":   {"name": "관세청 수출입통계", "var": "TV 수입 물량(kg)", "provider": "unipass.customs.go.kr"},
        "cpi":          {"name": "통계청 KOSIS",  "var": "소비자물가지수", "provider": "kosis.kr"},
    }

    def _run_prophet() -> pd.DataFrame:
        logging.getLogger("prophet").setLevel(logging.ERROR)
        logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
        n_pts = len(df)
        _df = df.copy()
        m = Prophet(
            yearly_seasonality=(n_pts >= 52),   # 1년치 이상 있을 때만
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.80,
            seasonality_mode="additive",
            changepoint_prior_scale=0.1,
            seasonality_prior_scale=12.0,
        )
        if n_pts >= 26:
            m.add_seasonality(name="monthly", period=4.33, fourier_order=5)

        # 외부 변수 주입 (데이터 충분할 때만)
        ext_cols = []
        if _ext_df is not None and n_pts >= 26:
            _df = _df.merge(_ext_df, on="ds", how="left")
            for col in [c for c in _ext_df.columns if c != "ds"]:
                if _df[col].notna().sum() >= n_pts * 0.5:  # 50% 이상 유효값
                    _df[col].fillna(_df[col].mean(), inplace=True)
                    m.add_regressor(col, standardize=True)
                    ext_cols.append(col)
            logger.info("[Prophet] 외부 변수 추가: %s", ext_cols)
            _ext_cols_used.extend(c for c in ext_cols if c not in _ext_cols_used)

        m.fit(_df)
        future = m.make_future_dataframe(periods=forecast_n, freq=freq)

        # 미래 기간 외부 변수: 월별 역사 평균으로 채움
        if ext_cols:
            for col in ext_cols:
                month_avg = _df.groupby(_df["ds"].dt.month)[col].mean().to_dict()
                future[col] = future["ds"].dt.month.map(month_avg)
                future[col].fillna(_df[col].mean(), inplace=True)

        return m.predict(future)

    # ── 선형회귀: 폴백 + 계절 영향도 분석 ────────────────────────────────────
    def _run_linear_fallback():
        """Prophet 실패 시 선형회귀 폴백."""
        import math as _math
        ratios = df["y"].tolist()
        n = len(ratios)
        xs = list(range(n))
        sx = sum(xs); sy = sum(ratios)
        sxy = sum(x * y for x, y in zip(xs, ratios))
        sxx = sum(x * x for x in xs)
        denom = n * sxx - sx * sx
        slope_lr = (n * sxy - sx * sy) / denom if denom else 0.0
        intercept = (sy - slope_lr * sx) / n
        residuals_lr = [ratios[i] - (intercept + slope_lr * i) for i in range(n)]
        std_lr = _math.sqrt(sum(r ** 2 for r in residuals_lr) / max(n - 2, 1))
        last_dt = df["ds"].iloc[-1]
        delta_map = {"date": timedelta(days=1), "week": timedelta(weeks=1), "month": timedelta(days=30)}
        delta = delta_map[time_unit]
        rows = []
        for i in range(forecast_n):
            xi = n + i
            pred = max(0.0, round(intercept + slope_lr * xi, 1))
            lbl = (last_dt + delta * (i + 1)).strftime("%Y-%m-%d")
            rows.append({"ds": lbl, "yhat": pred,
                         "yhat_lower": max(0.0, pred - _CI_MULTIPLIER * std_lr),
                         "yhat_upper": pred + _CI_MULTIPLIER * std_lr,
                         "trend": intercept + slope_lr * xi})
        return rows, slope_lr, std_lr

    def _run_lr_influence():
        """선형회귀: 계절 영향도 분석 (월별 효과 + 추세 기울기)"""
        y_arr = df["y"].values
        n     = len(y_arr)
        months = [d.month for d in df["ds"]]
        # X: intercept + trend + 12 month dummies
        X = np.zeros((n, 14))
        X[:, 0] = 1.0                          # intercept
        X[:, 1] = np.arange(n, dtype=float)    # trend
        for i, m in enumerate(months):
            X[i, m + 1] = 1.0                  # month dummy (cols 2-13)
        try:
            coefs, _, _, _ = np.linalg.lstsq(X, y_arr, rcond=None)
        except Exception:
            return None
        trend_slope  = float(coefs[1])
        month_coefs  = {m: float(coefs[m + 1]) for m in range(1, 13)}
        mn = {1:'1월',2:'2월',3:'3월',4:'4월',5:'5월',6:'6월',
              7:'7월',8:'8월',9:'9월',10:'10월',11:'11월',12:'12월'}
        peak_m = max(month_coefs, key=month_coefs.get)
        low_m  = min(month_coefs, key=month_coefs.get)
        direction = '증가' if trend_slope > 0 else '감소'
        return {
            "trend_slope":     round(trend_slope, 3),
            "peak_month":      mn[peak_m],
            "low_month":       mn[low_m],
            "monthly_effects": [
                {"month": mn[m], "effect": round(month_coefs[m], 1)}
                for m in range(1, 13)
            ],
            "interpretation": (
                f"매 기간 관심도가 {abs(round(trend_slope, 2))} 포인트씩 {direction}하는 추세이며, "
                f"{mn[peak_m]}에 계절 관심도가 가장 높고 {mn[low_m]}에 가장 낮습니다."
            ),
        }

    # ── XGBoost: 계절 features + 공공데이터 외부 변수 ────────────────────────
    def _run_xgb():
        try:
            import xgboost as xgb
            logger.info("[XGB] xgboost import OK, version=%s", xgb.__version__)
        except ImportError as e:
            logger.warning("[XGB] import 실패: %s", e)
            return None, None
        try:
            y_arr = df["y"].values
            n     = len(y_arr)
            LAG   = min(8, max(2, n // 10))
            logger.info("[XGB] n=%d, LAG=%d", n, LAG)
            if n < LAG + 4:
                return None, None

            from collections import defaultdict as _dd
            month_vals: dict = _dd(list)
            for i, dt in enumerate(df["ds"]):
                month_vals[dt.month].append(float(y_arr[i]))
            month_avg    = {m: float(np.mean(vs)) for m, vs in month_vals.items()}
            global_mean  = float(np.mean(y_arr))
            hist_std     = float(np.std(y_arr))

            # 외부 변수: 날짜 → {col: val} 맵
            _ext_cols: list[str] = []
            _ext_by_ds: dict     = {}
            _ext_month_avg: dict = {}
            if _ext_df is not None:
                _ext_cols = [c for c in _ext_df.columns if c != "ds"]
                for _, row in _ext_df.iterrows():
                    _ext_by_ds[row["ds"]] = [float(row.get(c, 0) or 0) for c in _ext_cols]
                # 미래 예측용 월별 평균
                for col in _ext_cols:
                    _ext_month_avg[col] = _ext_df.groupby(_ext_df["ds"].dt.month)[col].mean().to_dict()
                logger.info("[XGB] 외부 변수: %s", _ext_cols)
                for c in _ext_cols:
                    if c not in _ext_cols_used:
                        _ext_cols_used.append(c)

            def _get_ext(ds) -> list:
                # 훈련: 실제값, 예측: 월별 평균
                if ds in _ext_by_ds:
                    return _ext_by_ds[ds]
                m = ds.month if hasattr(ds, "month") else 1
                return [float(_ext_month_avg.get(c, {}).get(m, 0) or 0) for c in _ext_cols]

            def _feats(seasonal_pos: int, month: int, lags: list, ds=None) -> list:
                lag_arr = lags[-LAG:]
                m_avg   = month_avg.get(month, global_mean)
                base = [
                    seasonal_pos % 52,
                    month,
                    float(np.sin(2 * np.pi * month / 12)),
                    float(np.cos(2 * np.pi * month / 12)),
                    float(np.sin(2 * np.pi * (seasonal_pos % 52) / 52)),
                    m_avg,
                    *lag_arr,
                    float(np.mean(lag_arr)),
                    float(np.std(lag_arr)) if len(lag_arr) > 1 else 0.0,
                ]
                if _ext_cols and ds is not None:
                    base += _get_ext(ds)
                return base

            X_tr, Y_tr = [], []
            for i in range(LAG, n):
                m  = df["ds"].iloc[i].month
                ds = df["ds"].iloc[i]
                X_tr.append(_feats(i, m, list(y_arr[i - LAG:i]), ds=ds))
                Y_tr.append(float(y_arr[i]))
            X_tr = np.array(X_tr); Y_tr = np.array(Y_tr)

            val_size  = max(4, int(len(X_tr) * 0.2))
            X_fit, Y_fit = X_tr[:-val_size], Y_tr[:-val_size]
            X_val, Y_val = X_tr[-val_size:],  Y_tr[-val_size:]

            model = xgb.XGBRegressor(
                n_estimators=150,       # 300→150 과적합 억제
                max_depth=3,            # 4→3
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.7,
                min_child_weight=3,     # 2→3
                gamma=0.2,              # 0.1→0.2
                reg_lambda=2.0,         # L2 정규화 추가
                reg_alpha=0.1,          # L1 정규화 추가
                random_state=42, verbosity=0, n_jobs=1,
            )
            model.fit(X_fit, Y_fit)
            val_pred = model.predict(X_val)
            rmse_xgb = float(np.sqrt(np.mean((Y_val - val_pred) ** 2)))
            model.fit(X_tr, Y_tr)

            delta_map2 = {"D": timedelta(days=1), "W": timedelta(weeks=1), "MS": timedelta(days=30)}
            delta2  = delta_map2[freq]
            last_dt = df["ds"].iloc[-1]
            rolling = list(y_arr[-LAG:])
            preds   = []
            for i in range(forecast_n):
                future_ds = last_dt + delta2 * (i + 1)
                m   = future_ds.month
                m_avg = month_avg.get(m, global_mean)
                xf  = np.array([_feats(n + i, m, rolling, ds=future_ds)])
                p   = float(model.predict(xf)[0])
                # 월별 역사 평균 ±1.5 std 범위로 클리핑 (극단 예측 방지)
                lo  = max(0.0, m_avg - 1.5 * hist_std)
                hi  = m_avg + 1.5 * hist_std
                p   = max(lo, min(hi, p))
                p   = max(0.0, min(forecast_cap, p))
                preds.append({"period": future_ds.strftime("%Y-%m-%d"), "predicted": round(p, 1)})
                # 롤링 라그에는 스무딩값 사용 (캐스케이드 방지)
                rolling.append(0.6 * p + 0.4 * m_avg)
            return preds, rmse_xgb
        except Exception as e:
            logger.warning("XGBoost 학습 실패: %s", e)
            return None, None

    # ── 모델 실행 ─────────────────────────────────────────────────────────────
    use_prophet = False
    if _PROPHET_AVAIL:
        try:
            fc = await asyncio.to_thread(_run_prophet)
            use_prophet = True
        except Exception as e:
            logger.warning("Prophet 실패, 선형회귀 폴백 사용: %s", e)

    try:
        xgb_preds, xgb_rmse = await asyncio.to_thread(_run_xgb)
    except Exception as e:
        logger.warning("XGBoost 실행 실패: %s", e)
        xgb_preds, xgb_rmse = None, None
    influence = _run_lr_influence()

    if use_prophet:
        # R² 기반 신뢰도
        hist_yhat = fc.iloc[:len(df)]["yhat"].values
        ss_res    = float(np.sum((df["y"].values - hist_yhat) ** 2))
        ss_tot    = float(np.sum((df["y"].values - df["y"].mean()) ** 2))
        r_squared = max(0.0, 1.0 - ss_res / max(ss_tot, 1e-9))
        confidence = int(r_squared * 100)
        prophet_rmse = float(np.sqrt(ss_res / len(df)))
        future_fc = fc.iloc[len(df):]
        prophet_forecast = [
            {
                "period":    row["ds"].strftime("%Y-%m-%d"),
                "predicted": round(min(forecast_cap, max(0.0, row["yhat"])), 1),
                "ci_low":    round(min(forecast_cap, max(0.0, row["yhat_lower"])), 1),
                "ci_high":   round(min(forecast_cap * 1.2, max(0.0, row["yhat_upper"])), 1),
            }
            for _, row in future_fc.iterrows()
        ]
        trend_vals    = future_fc["trend"].values
        slope         = float((trend_vals[-1] - trend_vals[0]) / max(forecast_n - 1, 1))
        hist_yhat_arr = hist_yhat
    else:
        fb_rows, slope, res_std_fb = _run_linear_fallback()
        prophet_forecast = [
            {
                "period":    r["ds"],
                "predicted": round(r["yhat"], 1),
                "ci_low":    round(max(0.0, r["yhat_lower"]), 1),
                "ci_high":   round(r["yhat_upper"], 1),
            }
            for r in fb_rows
        ]
        prophet_rmse  = float(res_std_fb)
        confidence    = 50
        hist_yhat_arr = np.array([df["y"].mean()] * len(df))

    # ── 앙상블: Prophet + XGBoost (홀드아웃 RMSE 기반 가중치, Prophet 최소 40%) ──────
    if xgb_preds and use_prophet and xgb_rmse is not None and prophet_rmse > 0:
        total_rmse = prophet_rmse + xgb_rmse
        w_p = min(0.65, max(0.40, xgb_rmse  / total_rmse))   # Prophet 최소 40%, 최대 65%
        w_x = 1.0 - w_p
        forecast = [
            {
                "period":    prophet_forecast[i]["period"],
                "predicted": round(w_p * prophet_forecast[i]["predicted"] + w_x * xgb_preds[i]["predicted"], 1),
                "ci_low":    prophet_forecast[i]["ci_low"],
                "ci_high":   prophet_forecast[i]["ci_high"],
            }
            for i in range(forecast_n)
        ]
        model_used  = "ensemble"
        model_weights = {"prophet": round(w_p, 2), "xgb": round(w_x, 2)}
    else:
        forecast      = prophet_forecast
        model_used    = "prophet" if use_prophet else "linear"
        model_weights = None

    # ── 학습 스케일 기준 현재값 + 월별 기준선 추출 ────────────────────────────
    # train_data(2년, 7월=100 정규화)로 모델을 학습했으므로 예측값은 train 스케일.
    # 두 쿼리의 weekly 경계일이 달라 exact match 불가 → 날짜 차이 최소 포인트 선택.
    train_last_ratio = None
    monthly_baseline: dict[int, float] = {}
    if time_unit != "date" and trend_data and train_data:
        from datetime import datetime as _dt
        from collections import defaultdict as _dd
        last_dt = _dt.strptime(trend_data[-1]["period"][:10], "%Y-%m-%d")
        closest = min(
            train_data,
            key=lambda d: abs((_dt.strptime(d["period"][:10], "%Y-%m-%d") - last_dt).days)
        )
        if closest and float(closest["ratio"]) > 0:
            train_last_ratio = round(float(closest["ratio"]), 2)
            logger.info("[Scale] display_last=%.1f  train_last=%.1f  (period: %s vs %s)",
                        float(trend_data[-1]["ratio"]), train_last_ratio,
                        trend_data[-1]["period"], closest["period"])

        # 2년치 train_data에서 월별 평균값 (예측 % 비교 기준)
        _m_vals: dict[int, list] = _dd(list)
        for d in train_data:
            _m_vals[int(d["period"][5:7])].append(float(d["ratio"]))
        monthly_baseline = {m: round(sum(v) / len(v), 2) for m, v in _m_vals.items()}

    if use_prophet:
        residuals  = df["y"].values - hist_yhat_arr
        res_std    = float(np.sqrt((residuals ** 2).mean()))
    else:
        res_std = res_std_fb
    slope_threshold = max(0.15, res_std * 0.3)

    # 프론트엔드 KPI("예상 변화율")와 동일한 기준(직전 실측값 대비 향후 3개월 평균)으로
    # 추세를 판정해 AI 전망 문구가 화면에 표시되는 % 수치와 어긋나지 않도록 한다.
    _ref_ratio = train_last_ratio if train_last_ratio else (
        float(trend_data[-1]["ratio"]) if trend_data else None
    )
    _next3 = forecast[:3]
    _next3_avg = (
        sum(f["predicted"] for f in _next3) / len(_next3) if _next3 else None
    )
    near_term_pct = (
        round((_next3_avg - _ref_ratio) / _ref_ratio * 100, 1)
        if _ref_ratio and _next3_avg is not None and _ref_ratio > 0
        else None
    )

    if near_term_pct is not None:
        if near_term_pct > 5:
            trend_dir = "상승"
        elif near_term_pct < -5:
            trend_dir = "하락"
        else:
            trend_dir = "안정"
    elif slope > slope_threshold:
        trend_dir = "상승"
    elif slope < -slope_threshold:
        trend_dir = "하락"
    else:
        trend_dir = "안정"

    peak_idx    = max(range(forecast_n), key=lambda i: forecast[i]["predicted"])
    peak_period = forecast[peak_idx]["period"]

    recommendation = (
        f"수요 상승세가 예측됩니다. {peak_period[:7]} 이전에 재고를 선제적으로 확보하시길 추천합니다."
        if trend_dir == "상승"
        else f"수요 하락세가 예측됩니다. 재고를 보수적으로 운영하시고 프로모션 전략 검토를 권장합니다."
        if trend_dir == "하락"
        else "수요가 안정적인 흐름을 보이고 있습니다. 현재 재고 수준을 유지하며 시장 변화를 모니터링하세요."
    )

    # ── 시장 키워드 추출 (쇼핑 상품 타이틀 기반) ─────────────────────────────
    async def _fetch_market_keywords() -> list[str]:
        """쇼핑 API 상품명에서 핵심 수식어 키워드 추출 (상위 8개)"""
        try:
            raw = await search_products(query=category, page=1, display=30, sort="sim", category=category)
            titles = [strip_html(it.get("title", "")) for it in raw.get("items", []) if it.get("title")]
            from collections import Counter as _Counter
            words: list[str] = []
            _model_num = re.compile(r'^[A-Za-z0-9]{5,}$')  # 모델번호 패턴 (영숫자만, 5자 이상)
            _brand_set = {"삼성전자", "LG전자", "캐리어", "위니아", "파세코", "귀뚜라미", "롯데", "코웨이"}
            for t in titles:
                for tok in re.split(r"[\s/·,()·\[\]<>]+", t):
                    tok = tok.strip()
                    if (len(tok) >= 2 and len(tok) <= 10
                            and tok not in _STOP
                            and category not in tok
                            and tok not in _brand_set
                            and not _model_num.match(tok)   # 모델번호 제외
                            and not tok.isdigit()):
                        words.append(tok)
            top = [w for w, _ in _Counter(words).most_common(20)][:8]
            return top
        except Exception:
            return []

    rag_insight: dict = {}
    _ri_ck = f"forecast-rag:{_CACHE_VER}:{category}:{trend_dir}:{peak_period[:7]}"
    _ri_cached = _GROQ_CACHE.get(_ri_ck)
    if _ri_cached and _ri_cached[0] > _time.time():
        rag_insight = _ri_cached[1]
    else:
      try:
        import json as _json_fc

        # 병렬: RAG + 키워드 추출
        rag_chunks_raw, market_kws = await asyncio.gather(
            rag.query(f"{category} 계절 수요 시즌 구매 패턴", n_results=5) if rag else asyncio.sleep(0),
            _fetch_market_keywords(),
        )
        rag_chunks = rag_chunks_raw if isinstance(rag_chunks_raw, list) else []

        ctx = ""
        if rag_chunks:
            ctx += "\n[소비자 구매 패턴 데이터]\n" + "\n".join(f"- {c[:_RAG_CHUNK_LEN]}" for c in rag_chunks)
        if market_kws:
            ctx += f"\n[현재 시장 주목 키워드] {', '.join(market_kws)}"

        res = await _groq_create(
            messages=[
                {"role": "system", "content": "가전 시장 수요 예측 어드바이저입니다. 순수 JSON만 출력하세요."},
                {"role": "user", "content": (
                    f"[{category} 예측 요약]\n"
                    f"- 트렌드: {trend_dir}\n"
                    f"- 예측 피크: {peak_period[:7]}\n"
                    f"{ctx}\n\n"
                    f"다음 JSON 형식으로 응답하세요:\n"
                    f'{{\n'
                    f'  "opportunity": ["기회요인1 (키워드 기반, 15자 이내)", "기회요인2", "기회요인3"],\n'
                    f'  "risk": ["위험요인1 (15자 이내)", "위험요인2", "위험요인3"],\n'
                    f'  "strategy": ["전략1 (20자 이내 행동지침)", "전략2", "전략3"]\n'
                    f'}}\n'
                    f'opportunity: 위 키워드 중 상승 요인을 활용해 "{category} X 수요 증가" 또는 "X 관심 확대" 형태로 작성\n'
                    f'risk: 주요 위험 요인 2~3가지 (명사형)\n'
                    f'strategy: 구매·판매 전략 2~3가지 (구체적 행동 지침). 특정 월을 직접 언급하지 말고 '
                    f'"성수기 전", "피크 시즌 전", "비수기" 등 상대적 시점 표현을 사용할 것\n'
                    f'순수 JSON만 출력하세요.'
                )},
            ],
            max_tokens=400,
            temperature=0.3,
        )
        raw_fc = res.choices[0].message.content.strip()
        s_fc = raw_fc.find("{"); e_fc = raw_fc.rfind("}")
        if s_fc != -1 and e_fc != -1:
            rag_insight = _json_fc.loads(raw_fc[s_fc:e_fc + 1])
            _GROQ_CACHE[_ri_ck] = (_time.time() + _GROQ_TTL, rag_insight)
      except Exception as e:
        logger.warning("RAG insight 생성 실패: %s", e)
        rag_insight = {}

    # ── 매입 타이밍 신호 계산 ──────────────────────────────────────────────────
    today_dt = date.today()
    try:
        peak_dt = datetime.strptime(peak_period[:10], "%Y-%m-%d").date()
        days_to_peak = (peak_dt - today_dt).days
    except Exception:
        days_to_peak = 0

    # 선매입 권장 기간: 피크 2~3주 전 (weekly 기준 2포인트 = ~14일)
    _buy_lead = 14 if time_unit == "date" else (21 if time_unit == "week" else 45)
    days_to_buy = max(0, days_to_peak - _buy_lead)

    # 변곡점 탐지: 예측 구간에서 방향이 바뀌는 첫 지점
    inflection_period = None
    if len(forecast) >= 3:
        _preds = [f["predicted"] for f in forecast]
        for _i in range(1, len(_preds) - 1):
            _prev = _preds[_i - 1]; _cur = _preds[_i]; _nxt = _preds[_i + 1]
            # 로컬 최고점 (상승→하락 전환) 또는 로컬 최저점 (하락→상승 전환)
            if (_cur >= _prev and _cur >= _nxt and _cur > _preds[0] * 1.05):
                inflection_period = forecast[_i]["period"]
                break
            if (_cur <= _prev and _cur <= _nxt and _cur < _preds[0] * 0.95):
                inflection_period = forecast[_i]["period"]
                break

    if trend_dir == "상승":
        if days_to_peak > 0:
            _buy_label = f"D-{days_to_buy}일 매입 권장" if days_to_buy > 0 else "즉시 매입 권장"
            timing_signal = {
                "type":         "buy",
                "label":        _buy_label,
                "days_to_peak": days_to_peak,
                "days_to_buy":  days_to_buy,
                "peak_period":  peak_period[:10],
                "message":      f"수요 피크({peak_period[:7]}) {_buy_lead}일 전인 지금이 선매입 적기입니다. 재고를 선제 확보해 피크 시즌 기회를 포착하세요.",
            }
        else:
            timing_signal = {
                "type":         "hold",
                "label":        "피크 통과 중",
                "days_to_peak": days_to_peak,
                "days_to_buy":  0,
                "peak_period":  peak_period[:10],
                "message":      f"수요 피크({peak_period[:7]})를 지나는 시점입니다. 현재 재고 수준을 유지하며 프로모션을 집중하세요.",
            }
    elif trend_dir == "하락":
        timing_signal = {
            "type":         "wait",
            "label":        "매입 보류 권장",
            "days_to_peak": days_to_peak,
            "days_to_buy":  0,
            "peak_period":  peak_period[:10],
            "message":      f"수요 하락 추세가 예측됩니다. 신규 매입을 보류하고 기존 재고 소진에 집중하세요. 변곡점({inflection_period[:7] if inflection_period else '미정'}) 이후 재진입을 검토하세요.",
        }
    else:
        timing_signal = {
            "type":         "hold",
            "label":        "AI 전망",
            "days_to_peak": days_to_peak,
            "days_to_buy":  0,
            "peak_period":  peak_period[:10],
            "message":      f"수요가 안정적인 흐름을 보이고 있습니다.\n현재 매입 수준을 유지하되, 예상 성수기({peak_period[:7]}) 진입 전 수요 변화에 대비해 재고 계획을 점검하는 것이 유리합니다.",
        }

    # /ai-report 등 다른 엔드포인트가 같은 추세 판단을 재사용할 수 있도록 캐시
    _GROQ_CACHE[f"forecast:{_CACHE_VER}:{category}:{period}"] = (
        _time.time() + _GROQ_TTL, {"trend_dir": trend_dir, "near_term_pct": near_term_pct}
    )

    return {
        "category":        category,
        "period":          period,
        "time_unit":       time_unit,
        "history":         [{"period": d["period"], "ratio": d["ratio"]} for d in trend_data],
        "forecast":        forecast,
        "trend_direction": trend_dir,
        "slope":           round(slope, 3),
        "peak_period":     peak_period,
        "confidence":      confidence,
        "recommendation":  recommendation,
        "timing_signal":   timing_signal,
        "inflection_period": inflection_period,
        "rag_insight":     rag_insight,
        "model_info": {
            "used":    model_used,
            "weights": model_weights,
            "rmse": {
                "prophet": round(prophet_rmse, 2) if use_prophet else None,
                "xgb":     round(xgb_rmse, 2)    if xgb_rmse is not None else None,
            },
        },
        "influence":         influence,
        "train_last_ratio":  train_last_ratio,
        "monthly_baseline":  monthly_baseline,
        "ext_vars_used":     _ext_cols_used,
        "data_sources": [
            {**_EXT_SOURCE_META[col], "col": col}
            for col in _ext_cols_used
            if col in _EXT_SOURCE_META
        ],
    }


# ── 공공데이터 환경 신호 헬퍼 ────────────────────────────────────────────────
_ENV_VARS_FOR = {
    "에어컨":     ["kma_temp", "kma_humidity"],
    "냉장고":     ["kma_temp"],
    "세탁기":     [],
    "건조기":     [],
    "공기청정기": ["air_pm25", "air_pm10"],
    "로봇청소기": [],
    "식기세척기": [],
    "TV":         [],
    "제습기":     ["kma_temp", "kma_humidity"],
    "가습기":     ["kma_humidity"],
    "선풍기":     ["kma_temp"],
}

async def _load_env_signal(category: str) -> dict:
    """카테고리별 최신 환경 신호를 공공데이터 캐시에서 로드."""
    from app.services.naver_cache import get_db_cache as _gc
    from datetime import datetime as _dt

    vars_needed = _ENV_VARS_FOR.get(category, [])
    result: dict = {"category": category, "vars": {}, "signals": [], "sources": []}

    # KMA 최근 1주 평균
    if any(v.startswith("kma_") for v in vars_needed):
        kma = await _gc("ext:kma:history")
        if kma and kma.get("items"):
            recent = sorted(kma["items"], key=lambda x: x["date"], reverse=True)[:7]
            avg_temp = round(sum(i["temp"] for i in recent) / len(recent), 1)
            avg_hum  = round(sum(i["humidity"] for i in recent) / len(recent), 1)
            result["vars"]["kma_temp"]     = avg_temp
            result["vars"]["kma_humidity"] = avg_hum
            result["vars"]["kma_date"]     = recent[0]["date"]
            result["sources"].append("기상청 ASOS")
            # 카테고리별 신호 해석
            if category in ("에어컨", "선풍기"):
                if avg_temp >= 27:
                    result["signals"].append({"icon": "🔥", "label": f"기온 {avg_temp}℃ · 습도 {avg_hum}% → 냉방 수요 상승 구간", "level": "high"})
                elif avg_temp >= 20:
                    result["signals"].append({"icon": "🌤", "label": f"기온 {avg_temp}℃ · 습도 {avg_hum}% → 냉방 수요 준비 구간", "level": "mid"})
                else:
                    result["signals"].append({"icon": "❄️", "label": f"기온 {avg_temp}℃ → 비수기", "level": "low"})
            elif category == "냉장고":
                if avg_temp >= 25:
                    result["signals"].append({"icon": "🌡", "label": f"기온 {avg_temp}℃ → 식품 보관 수요 증가", "level": "mid"})
            elif category in ("제습기",):
                if avg_temp >= 23 and avg_hum >= 65:
                    result["signals"].append({"icon": "💧", "label": f"기온 {avg_temp}℃ · 습도 {avg_hum}% → 제습기 수요 상승", "level": "high"})
            elif category == "가습기":
                if avg_hum <= 40:
                    result["signals"].append({"icon": "🌵", "label": f"습도 {avg_hum}% → 건조함, 가습기 수요 상승", "level": "high"})

    # 에어코리아 최근 PM2.5/PM10
    if any(v.startswith("air_") for v in vars_needed):
        air = await _gc("ext:airkorea:history")
        if air and air.get("items"):
            recent_air = sorted(air["items"], key=lambda x: x["date"], reverse=True)[:7]
            avg_pm25 = round(sum(i.get("pm25", 0) for i in recent_air) / len(recent_air), 1)
            avg_pm10 = round(sum(i.get("pm10", 0) for i in recent_air) / len(recent_air), 1)
            result["vars"]["air_pm25"] = avg_pm25
            result["vars"]["air_pm10"] = avg_pm10
            result["sources"].append("에어코리아")
            grade = "매우나쁨" if avg_pm25 >= 76 else "나쁨" if avg_pm25 >= 36 else "보통" if avg_pm25 >= 16 else "좋음"
            level = "high" if avg_pm25 >= 36 else "mid" if avg_pm25 >= 16 else "low"
            result["signals"].append({"icon": "🌫", "label": f"PM2.5 {avg_pm25}㎍/㎥ ({grade}) → 공기청정기 수요 {'상승' if avg_pm25 >= 36 else '보통'}", "level": level})

    # KCA 불만 건수
    kca = await _gc(f"ext:kca:{category}")
    if kca and kca.get("items"):
        result["vars"]["kca_count"] = len(kca["items"])
        result["sources"].append("한국소비자원")

    # 에너지공단 KEMCO 효율등급 1등급 비율
    kemco = await _gc(f"ext:kemco:{category}")
    if kemco and kemco.get("grade1_ratio") is not None:
        ratio = kemco["grade1_ratio"]
        total = kemco.get("total_products", 0)
        result["vars"]["kemco_grade1"]  = ratio
        result["vars"]["kemco_total"]   = total
        result["sources"].append("에너지공단")
        if ratio >= 50:
            result["signals"].append({"icon": "", "label": f"에너지 1등급 비율 {ratio}% → 고효율 프리미엄 제품 선호 뚜렷", "level": "high"})
        elif ratio >= 25:
            result["signals"].append({"icon": "", "label": f"에너지 1등급 비율 {ratio}% → 효율등급 경쟁 확대 중", "level": "mid"})
        else:
            result["signals"].append({"icon": "", "label": f"에너지 1등급 비율 {ratio}% → 보급형 중심 시장", "level": "low"})

    return result


@router.get("/env-signal")
async def get_env_signal(category: str = Query(..., min_length=1), _: dict = Depends(require_b2b)):
    """카테고리별 공공데이터 기반 외부 환경 신호."""
    _ck = f"env_signal:{category}"
    _cached = _GROQ_CACHE.get(_ck)
    if _cached and _time.time() < _cached[0]:
        return _cached[1]
    result = await _load_env_signal(category)
    _GROQ_CACHE[_ck] = (_time.time() + 1800, result)  # 30분 캐시
    return result
