from fastapi import APIRouter, Depends, Query
from app.routers.b2b_utils import *

router = APIRouter()


@router.post("/cache/clear")
async def clear_b2b_cache(_: dict = Depends(require_b2b)):
    _GROQ_CACHE.clear()
    _GROQ_MODEL_EXHAUSTED.clear()
    return {"ok": True, "message": "캐시 초기화 완료"}

@router.get("/dashboard")
async def get_b2b_dashboard(category: str = Query(..., min_length=1), period: str = "3m", _: dict = Depends(require_b2b)):
    from app.dependencies import get_rag_optional
    from app.services.naver_cache import get_db_cache as _get_db_cache, set_db_cache as _set_db_cache

    _ck     = f"dashboard:{_CACHE_VER}:{category}:{period}"
    _db_key = f"naver_dashboard:{category}:{period}"

    # 1. 인메모리 캐시
    _cached = _GROQ_CACHE.get(_ck)
    if _cached and _time.time() < _cached[0]:
        cached_result = _cached[1]
        # complaints + complaint_summary를 별도 캐시에서 최신값 주입
        _cc = _GROQ_CACHE.get(f"complaints:{category}")
        if _cc and _time.time() < _cc[0] and _cc[1]:
            _cc_data = _cc[1]
            _items   = _cc_data.get("items", [])   if isinstance(_cc_data, dict) else (_cc_data or [])
            _summary = _cc_data.get("summary", []) if isinstance(_cc_data, dict) else []
            cached_result = {**cached_result, "complaints": _items, "complaint_summary": _summary}
        return cached_result

    # 2. Supabase DB 캐시 (Render에서 Naver API 해외 차단 대비)
    _db_data = await _get_db_cache(_db_key)
    if _db_data:
        _GROQ_CACHE[_ck] = (_time.time() + min(_GROQ_TTL, 3600), _db_data)
        return _db_data

    rag = get_rag_optional()

    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = days_map.get(period, 90)
    time_unit = "week" if days > 30 else "date"
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    dl_headers = {**NAVER_HEADERS, "Content-Type": "application/json"}

    async def fetch_trend():
        body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate":   end_date.strftime("%Y-%m-%d"),
            "timeUnit":  time_unit,
            "keywordGroups": [{"groupName": category, "keywords": [category]}],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://openapi.naver.com/v1/datalab/search", json=body, headers=dl_headers)
        payload = resp.json()
        if "errorCode" in payload:
            logger.warning("DataLab trend 오류 [%s]: %s — %s", category, payload.get("errorCode"), payload.get("errorMessage"))
            return []
        results = payload.get("results", [])
        return results[0]["data"] if results else []

    async def fetch_brand_share():
        # search_products는 brand/maker를 합쳐버리므로 직접 호출
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                headers=NAVER_HEADERS,
                params={"query": category, "display": 100, "sort": "sim"},
            )
        items = resp.json().get("items", [])
        counts: dict[str, int] = {}
        for it in items:
            # maker(제조사) 우선, 없으면 brand
            key = it.get("maker", "").strip() or it.get("brand", "").strip()
            if key:
                counts[key] = counts.get(key, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
        total = sum(v for _, v in top)
        return [{"brand": k, "count": v, "pct": round(v / total * 100) if total else 0} for k, v in top]

    async def fetch_age(age_codes_list: list[str]) -> float:
        body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate":   end_date.strftime("%Y-%m-%d"),
            "timeUnit":  "month",
            "keywordGroups": [{"groupName": category, "keywords": [category]}],
            "ages": age_codes_list,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://openapi.naver.com/v1/datalab/search", json=body, headers=dl_headers)
        payload = resp.json()
        if "errorCode" in payload:
            logger.warning("DataLab age 오류 [%s/%s]: %s — %s", category, age_codes_list, payload.get("errorCode"), payload.get("errorMessage"))
            return 0.0
        results = payload.get("results", [])
        data = results[0]["data"] if results else []
        return sum(d["ratio"] for d in data) / len(data) if data else 0.0

    async def fetch_keywords():
        raw = await search_products(query=category, page=1, display=30, sort="sim", category=category)
        items = raw.get("items", [])

        KW_STOP = _STOP | {
            "미포함", "포함", "수도권", "설치비포함", "설치비별도", "방문설치",
            "무료설치", "무료", "별도", "이하", "이상", "할인", "택배", "직접",
            "기사", "배송", "셀프", "자가설치", "원룸", "평", "인치",
        }
        # 순수 영문 2~4자 토큰(모델코드)은 제외
        def is_valid(w: str) -> bool:
            w = w.strip()
            if not w or len(w) < 2 or w == category or w in KW_STOP:
                return False
            if re.match(r'^[A-Za-z]{1,4}$', w):   # 짧은 영문 코드 제외
                return False
            if any(c.isdigit() for c in w):         # 숫자 포함 제외
                return False
            return True

        # 단어별 등장 제품 예시 수집
        word_counts: Counter = Counter()
        word_examples: dict[str, list[str]] = {}

        def record(w: str, title: str):
            if not is_valid(w):
                return
            word_counts[w] += 1
            if w not in word_examples:
                word_examples[w] = []
            if len(word_examples[w]) < 3:
                short = strip_html(title)[:30]
                if short not in word_examples[w]:
                    word_examples[w].append(short)

        for it in items:
            t = strip_html(it.get("title", ""))
            record(it.get("brand") or "", t)
            record(it.get("maker") or "", t)
            record(it.get("category3") or "", t)
            record(it.get("category4") or "", t)
            for tok in re.sub(r'[^가-힣a-zA-Z\s]', ' ', t).split():
                record(tok, t)

        top = word_counts.most_common(20)
        return [
            {"word": w, "count": c, "examples": word_examples.get(w, [])}
            for w, c in top
        ]

    async def fetch_review_mention_count() -> int:
        """블로그 + 카페 리뷰 언급 총량 — 시장 리뷰 활동 지표"""
        async with httpx.AsyncClient(timeout=6.0) as client:
            blog_r, cafe_r = await asyncio.gather(
                client.get("https://openapi.naver.com/v1/search/blog.json",
                           headers=NAVER_HEADERS,
                           params={"query": f"{category} 리뷰", "display": 1}),
                client.get("https://openapi.naver.com/v1/search/cafearticle.json",
                           headers=NAVER_HEADERS,
                           params={"query": f"{category} 리뷰", "display": 1}),
            )
        blog_total = blog_r.json().get("total", 0) if blog_r.status_code == 200 else 0
        cafe_total = cafe_r.json().get("total", 0) if cafe_r.status_code == 200 else 0
        return blog_total + cafe_total

    age_groups = [["2"], ["3", "4"], ["5", "6"], ["7", "8"], ["9", "10", "11"]]
    age_labels = ["10대", "20대", "30대", "40대", "50대+"]

    async def fetch_complaints():
        _KW_STOP = {
            category, "제품", "구매", "사용", "배송", "설치", "가격", "서비스",
            "이번", "이후", "경우", "정도", "때문", "생각", "느낌", "부분",
            "것이", "수있", "있는", "없는", "같은", "하는", "되는", "이런",
            "저희", "우리", "모두", "정말", "너무", "매우", "조금", "약간",
            "그냥", "아직", "계속", "바로", "항상", "다시", "처음", "이미",
        }
        _POS_SENTENCE = ["없", "작아", "적어", "좋아", "좋은", "만족", "괜찮", "추천", "최고", "훌륭", "완벽", "조용"]

        # Step1: 쇼핑 API 직접 호출 (maker 필드 포함)
        async with httpx.AsyncClient(timeout=8.0) as client:
            shop_resp = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                headers=NAVER_HEADERS,
                params={"query": category, "display": 10, "sort": "sim"},
            )
        raw_items = shop_resp.json().get("items", [])[:10]
        if not raw_items:
            logger.warning("[complaints] 쇼핑 결과 없음")
            return []

        products = [
            {
                "title": strip_html(it.get("title", "")),
                "brand": it.get("brand", "").strip(),
                "maker": it.get("maker", "").strip(),
                "price": int(it.get("lprice") or 0),
            }
            for it in raw_items
        ]

        # Step2: maker 기준 중복 제거
        seen_makers: dict[str, bool] = {}
        for p in products:
            key = p["maker"] or p["brand"] or category
            seen_makers[key] = True

        async def search_maker_complaint(maker: str) -> dict:
            articles: list[dict] = []
            all_text = ""
            naver_queries = [
                ("https://openapi.naver.com/v1/search/blog.json",        f"{maker} {category} 단점 아쉬운점"),
                ("https://openapi.naver.com/v1/search/cafearticle.json",  f"{maker} {category} 후기 불편"),
                ("https://openapi.naver.com/v1/search/news.json",         f"{maker} {category} 결함 불만"),
            ]
            async with httpx.AsyncClient(timeout=8.0) as client:
                for url, q in naver_queries:
                    try:
                        resp = await client.get(
                            url, headers=NAVER_HEADERS,
                            params={"query": q, "display": 6, "sort": "date"},
                        )
                        if "blog" in url:       src = "블로그"
                        elif "cafe" in url:     src = "카페"
                        else:                   src = "뉴스"
                        for item in resp.json().get("items", []):
                            title = strip_html(item.get("title", ""))
                            desc  = strip_html(item.get("description", ""))
                            all_text += " " + title + " " + desc
                            articles.append({
                                "title":       title,
                                "description": desc,
                                "link":        item.get("originallink") or item.get("link", ""),
                                "pubDate":     item.get("pubDate", "")[:10],
                                "source":      src,
                            })
                    except Exception as e:
                        logger.warning(f"[complaints] Naver 검색 실패 q={q}: {e}")

                # YouTube 리뷰 영상
                if YOUTUBE_API_KEY:
                    try:
                        yt_resp = await client.get(
                            YOUTUBE_SEARCH_URL,
                            params={
                                "part": "snippet", "type": "video",
                                "q": f"{maker} {category} 리뷰 단점",
                                "maxResults": 4,
                                "relevanceLanguage": "ko",
                                "key": YOUTUBE_API_KEY,
                            },
                            timeout=6.0,
                        )
                        for item in yt_resp.json().get("items", []):
                            vid   = item["id"].get("videoId", "")
                            snip  = item.get("snippet", {})
                            title = snip.get("title", "")
                            desc  = snip.get("description", "")[:120]
                            all_text += " " + title + " " + desc
                            articles.append({
                                "title":       title,
                                "description": desc or "YouTube 리뷰 영상",
                                "link":        f"https://www.youtube.com/watch?v={vid}",
                                "pubDate":     snip.get("publishedAt", "")[:10],
                                "source":      "YouTube",
                                "thumbnail":   snip.get("thumbnails", {}).get("default", {}).get("url", ""),
                                "channel":     snip.get("channelTitle", ""),
                            })
                    except Exception as e:
                        logger.warning(f"[complaints] YouTube 검색 실패: {e}")

            import json as _json

            # ── 1. 부정 문장만 필터 ──────────────────────────────────────────────
            _NEG_MARKERS = [
                '단점', '불만', '아쉬', '불편', '문제', '고장', '결함', '냄새',
                '소음', '발열', '느린', '비싸', '무거', '오작동', '기스', '파손',
                '오래', '안됨', '안돼', '이상', '실망', '후회', '별로', '최악',
                '시끄럽', '덥다', '뜨겁', '느리다', '무겁다', '비싸다',
            ]
            _POS_SENTENCES = ['장점', '좋은점', '강추합니다', '추천합니다', '만족합니다', '최고입니다']
            sentences = re.split(r'[.!?\n。]', all_text)
            neg_sentences = [
                s.strip() for s in sentences
                if any(m in s for m in _NEG_MARKERS)
                and not any(p in s for p in _POS_SENTENCES)
                and 5 < len(s.strip()) < 200
            ]
            neg_text = '. '.join(neg_sentences[:50]) if len(neg_sentences) >= 3 else all_text
            sample = neg_text[:2500]

            # ── 2. Groq: 구조화된 키워드+근거 추출 ─────────────────────────────
            _POS_FILTER = {
                '좋음', '좋은', '최고', '추천', '만족', '훌륭', '완벽', '탁월', '빠름',
                '조용', '조용함', '강추', '성능', '편리', '편리함', '깔끔', '쾌적',
                '우수', '뛰어남', '탁월함', '우수함',
            }
            _POS_CONTAINS = ['좋', '추천', '만족', '최고', '훌륭', '완벽', '우수', '뛰어']

            tags: list[str] = []
            tag_evidence: dict[str, str] = {}   # 키워드 → 근거 문장

            if all_text.strip():
                try:
                    resp = await _groq_create(
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "당신은 한국 소비자 불만 분석 전문가입니다. "
                                    "반드시 부정적 키워드(결함·불편·단점)만 추출하고 "
                                    "긍정적·중립적 단어는 절대 포함하지 마세요."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"아래는 '{maker} {category}' 소비자 불만 텍스트입니다.\n\n"
                                    f"[추출 규칙]\n"
                                    f"1. 실제 불만/결함/단점 키워드만 (예: 소음, 발열, 누수, 냄새, 고장)\n"
                                    f"2. 브랜드명·모델명·일반 명사 제외\n"
                                    f"3. 좋음·추천·만족·성능 같은 긍정 단어 절대 금지\n"
                                    f"4. 최대 7개, 자주 등장한 순서대로\n\n"
                                    f"[출력 형식] JSON만 (설명 없이):\n"
                                    f"{{\"keywords\": [\"소음\", \"발열\"], "
                                    f"\"evidence\": {{\"소음\": \"실외기 진동과 작동 소음이 크다는 의견이 여러 후기에서 반복적으로 나타났습니다.\", "
                                    f"\"발열\": \"장시간 사용 시 본체 상단부에 과열 현상이 발생한다는 보고가 다수 확인되었습니다.\"}}}}\n\n"
                                    f"[근거 문장 작성 규칙]\n"
                                    f"- 최소 20자 이상의 완전한 문장으로 작성\n"
                                    f"- '~한다는 의견이 반복적으로 나타났습니다', '~는 보고가 다수 확인되었습니다' 형식 사용\n"
                                    f"- 단순 형용사(불편합니다, 아쉽습니다)만 쓰지 말고 구체적 현상을 포함\n\n"
                                    f"[텍스트]\n{sample}"
                                ),
                            },
                        ],
                        max_tokens=200,
                        temperature=0.0,
                    )
                    raw = resp.choices[0].message.content.strip()
                    # JSON 파싱
                    start, end = raw.find('{'), raw.rfind('}')
                    if start != -1 and end > start:
                        parsed = _json.loads(raw[start:end+1])
                        kws = parsed.get("keywords", [])
                        evid = parsed.get("evidence", {})
                        tags = [
                            t for t in kws
                            if isinstance(t, str) and 2 <= len(t) <= 10
                            and t not in _POS_FILTER
                            and not any(p in t for p in _POS_CONTAINS)
                        ][:7]
                        tag_evidence = {t: evid.get(t, "") for t in tags}
                except Exception as e:
                    logger.warning(f"[complaints] Groq 추출 실패: {e}")
                    # JSON 실패 시 단순 정규식 fallback
                    raw_fb = ""
                    try:
                        raw_fb = resp.choices[0].message.content.strip()
                    except Exception:
                        pass
                    parsed_fb = re.findall(r'"([가-힣]{2,6})"', raw_fb)
                    tags = [t for t in parsed_fb if t not in _POS_FILTER][:7]

            # ── 3. 교차 검증: 여러 기사에 등장한 키워드 우선 ──────────────────
            if tags:
                def article_count(t):
                    return sum(1 for a in articles if t in a["title"] + " " + a["description"])
                counts = {t: article_count(t) for t in tags}
                # 1개 기사에만 등장한 키워드는 신뢰도 낮음 → 뒤로 밀기
                tags = sorted(tags, key=lambda t: counts.get(t, 0), reverse=True)

            logger.info(f"[complaints] maker={maker} tags={tags} articles={len(articles)}")

            # ── 4. 소스: 각 태그 언급 기사 우선 정렬 ──────────────────────────
            def source_score(a):
                text = a["title"] + " " + a["description"]
                return sum(1 for t in tags if t in text)

            scored = sorted(articles, key=source_score, reverse=True)
            sources = [a for a in scored if source_score(a) > 0] or articles
            return {
                "tags": tags,
                "evidence": tag_evidence,   # 키워드 → 근거 문장
                "sources": sources[:8],
            }

        maker_list = list(seen_makers.keys())
        maker_results = await asyncio.gather(
            *[search_maker_complaint(m) for m in maker_list],
            return_exceptions=True,
        )
        maker_complaints: dict[str, dict] = {
            m: (r if not isinstance(r, Exception) else {"tags": [], "sources": []})
            for m, r in zip(maker_list, maker_results)
        }

        # Step3: 제품별 결과 조립
        result = []
        for i, p in enumerate(products):
            key  = p["maker"] or p["brand"] or category
            data = maker_complaints.get(key, {"tags": [], "sources": [], "evidence": {}})
            result.append({
                "rank":      i + 1,
                "product":   p["title"][:24],
                "brand":     p["brand"] or p["maker"],
                "price":     p["price"],
                "complaint": data["tags"],
                "evidence":  data.get("evidence", {}),
                "sources":   data["sources"],
            })

        # Step4: 전체 불만 집계 — 빈도% + 브랜드별 분포
        total_products = len(result)
        tag_freq: Counter = Counter()
        tag_brands: dict[str, list[str]] = {}
        tag_evidence_all: dict[str, str] = {}
        for item in result:
            brand = item.get("brand") or ""
            evid  = item.get("evidence", {})
            for tag in item["complaint"]:
                tag_freq[tag] += 1
                tag_brands.setdefault(tag, [])
                if brand and brand not in tag_brands[tag]:
                    tag_brands[tag].append(brand)
                if tag not in tag_evidence_all and evid.get(tag):
                    tag_evidence_all[tag] = evid[tag]

        top_items = tag_freq.most_common(10)
        max_cnt = top_items[0][1] if top_items else 1
        complaint_summary = [
            {
                "tag":      tag,
                "count":    cnt,
                "pct":      round(cnt / max_cnt * 100),  # 최빈 태그 대비 상대값 (항상 1위=100%)
                "brands":   tag_brands.get(tag, [])[:4],
                "evidence": tag_evidence_all.get(tag, ""),
            }
            for tag, cnt in top_items
        ]

        # result에 summary 주입
        return {"items": result, "summary": complaint_summary}


    # DataLab 동시 호출 과다 → rate limit 방지: trend/brand/keywords/complaints 병렬, age는 순차
    base_results = await asyncio.gather(
        fetch_trend(),
        fetch_brand_share(),
        fetch_keywords(),
        fetch_complaints(),
        fetch_review_mention_count(),
        return_exceptions=True,
    )

    trend_data           = base_results[0] if not isinstance(base_results[0], Exception) else []
    brand_data           = base_results[1] if not isinstance(base_results[1], Exception) else []
    keywords             = base_results[2] if not isinstance(base_results[2], Exception) else []
    _complaints_raw      = base_results[3] if not isinstance(base_results[3], Exception) else {}
    complaints           = _complaints_raw.get("items", []) if isinstance(_complaints_raw, dict) else (_complaints_raw or [])
    complaint_summary    = _complaints_raw.get("summary", []) if isinstance(_complaints_raw, dict) else []
    review_mention_count = base_results[4] if not isinstance(base_results[4], Exception) else 0

    # DataLab age 호출 순차 실행 (rate limit 방지, 총 ~1.5s)
    age_raw = []
    for g in age_groups:
        try:
            await asyncio.sleep(0.3)
            age_raw.append(await fetch_age(g))
        except Exception:
            age_raw.append(0.0)

    # DataLab 최신 주 미집계 trailing 저비율 데이터 제거
    while len(trend_data) > 4 and trend_data[-1]["ratio"] < trend_data[-2]["ratio"] * 0.3:
        trend_data = trend_data[:-1]

    age_total = sum(age_raw)
    age_dist = [
        {"label": lbl, "value": round(v, 1), "pct": round(v / age_total * 100) if age_total else 0}
        for lbl, v in zip(age_labels, age_raw)
    ]

    ratios   = [d["ratio"] for d in trend_data]
    current  = round(ratios[-1], 1) if ratios else 0
    avg_val  = round(sum(ratios) / len(ratios), 1) if ratios else 0
    half     = len(ratios) // 2
    old_avg  = sum(ratios[:half]) / max(half, 1)
    new_avg  = sum(ratios[half:]) / max(len(ratios) - half, 1)
    growth   = round((new_avg - old_avg) / max(old_avg, 1) * 100, 1)
    risk     = _calc_risk(growth)

    summary   = f"{category} 시장의 최근 {period} 트렌드 데이터를 분석한 결과입니다."
    groq_err  = None
    try:
        top3 = ", ".join(f"{b['brand']} {b['pct']}%" for b in brand_data[:3]) or "데이터 부족"
        top_age = max(age_dist, key=lambda x: x["value"])["label"] if age_dist else "30대"

        rag_context = ""
        if rag:
            chunks = await rag.query(f"{category} 소비자 반응 트렌드 구매 후기", n_results=6)
            if chunks:
                rag_context = "\n[소비자 실반응 데이터]\n" + "\n".join(f"- {c[:_RAG_CHUNK_LEN]}" for c in chunks)

        prompt = (
            f"[{category} 시장 B2B 분석 데이터]\n"
            f"- 검색 관심도: 현재 {current} / 기간 평균 {avg_val}\n"
            f"- {period} 성장률: {'+' if growth >= 0 else ''}{growth}%\n"
            f"- 주요 브랜드: {top3}\n"
            f"- 주 관심층: {top_age}\n"
            f"{rag_context}\n\n"
            f"위 데이터를 바탕으로 아래 JSON 구조로만 출력하세요 (설명·마크다운 없이):\n"
            f'{{\n'
            f'  "growth_potential": "높음 | 보통 | 낮음 중 하나",\n'
            f'  "competition_factors": ["경쟁 요인 1", "경쟁 요인 2", "경쟁 요인 3"],\n'
            f'  "risk_factors": ["주의 요소 1", "주의 요소 2"],\n'
            f'  "conclusion_lines": [\n'
            f'    "단락1: 현재 시장 상황과 성장세 판단 1~2문장. ~것으로 판단됩니다 어조.",\n'
            f'    "단락2: 소비자 관심 키워드·브랜드 경쟁 기반 전략 시사점 1~2문장. 특히 로 시작, ~전략이 효과적일 것으로 예상됩니다 어조.",\n'
            f'    "단락3: 리스크와 모니터링 포인트 1문장. 다만 으로 시작. ~필요합니다 어조."\n'
            f'  ]\n'
            f'}}'
        )
        res = await _groq_create(
            messages=[
                {"role": "system", "content": "당신은 B2B 가전 시장 분석 전문가입니다. 기업 보고서 형식의 객관적 어조로 분석하세요. 순수 JSON만 출력하세요."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.3,
        )
        import json as _json_mr
        raw_mr = res.choices[0].message.content.strip()
        start_mr, end_mr = raw_mr.find('{'), raw_mr.rfind('}')
        if start_mr != -1 and end_mr > start_mr:
            parsed_summary = _json_mr.loads(raw_mr[start_mr:end_mr+1])
            if isinstance(parsed_summary, dict) and parsed_summary:
                summary = parsed_summary
        else:
            summary = raw_mr
    except Exception as e:
        groq_err = repr(e)[:200]

    market_report = {
        "trend_score":         current,
        "avg_score":           avg_val,
        "growth_rate":         growth,
        "risk":                risk,
        "summary":             summary,
        "review_mention_count": review_mention_count,
    }
    if groq_err:
        market_report["_groq_error"] = groq_err

    # complaints 별도 캐시 (items + summary 함께 저장)
    _COMPLAINT_CACHE_KEY = f"complaints:{category}"
    if complaints:
        _GROQ_CACHE[_COMPLAINT_CACHE_KEY] = (_time.time() + 1800, {"items": complaints, "summary": complaint_summary})
    else:
        _cc = _GROQ_CACHE.get(_COMPLAINT_CACHE_KEY)
        if _cc and _time.time() < _cc[0] and _cc[1]:
            _cc_data = _cc[1]
            complaints        = _cc_data.get("items", []) if isinstance(_cc_data, dict) else (_cc_data or [])
            complaint_summary = _cc_data.get("summary", []) if isinstance(_cc_data, dict) else []

    # complaints sources → YouTube 영상 / 뉴스·블로그 기사 분리
    yt_videos: list[dict] = []
    news_sources: list[dict] = []
    seen_links: set = set()
    for item in complaints:
        for src in item.get("sources", []):
            lnk = src.get("link", "")
            if not lnk or lnk in seen_links:
                continue
            seen_links.add(lnk)
            if src.get("source") == "YouTube":
                yt_videos.append(src)
            elif src.get("source") in ("뉴스", "블로그", "카페"):
                news_sources.append(src)
    yt_videos   = yt_videos[:8]
    news_sources = sorted(news_sources, key=lambda x: x.get("pubDate", ""), reverse=True)[:8]

    result = {
        "category": category,
        "period":   period,
        "trend":    trend_data,
        "brands":   brand_data,
        "age_distribution": age_dist,
        "keywords":   keywords,
        "complaints": complaints,
        "complaint_summary": complaint_summary,
        "youtube_videos": yt_videos,
        "news_sources":   news_sources,
        "market_report": market_report,
        "_fetched_at": _time.time(),
    }
    # complaints가 여전히 비어 있으면 메인 캐시 저장 생략 → 다음 요청에서 재시도
    complaint_ok = bool(complaints) or bool(_GROQ_CACHE.get(_COMPLAINT_CACHE_KEY))
    if not groq_err and trend_data and complaint_ok:
        result_no_complaints = {**result, "complaints": [], "complaint_summary": []}
        _GROQ_CACHE[_ck] = (_time.time() + _GROQ_TTL, result_no_complaints)

    # Supabase DB에 전체 결과 저장 (로컬 실행 시 Render용 캐시 자동 생성)
    if trend_data:
        try:
            await _set_db_cache(_db_key, result)
        except Exception as _dce:
            logger.warning("[dashboard] DB 캐시 저장 실패: %s", _dce)

    return result
