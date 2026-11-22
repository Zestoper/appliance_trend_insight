"""B2B 분석 화면 일괄 점검: 여러 품목에서 상품 50개 정도를 골라 실제 분석을 돌리고
비어 있는 값 · 서로 안 맞는 값 · 이상한 값을 자동으로 찾아 보고서로 남긴다.

실행 (맥 터미널 · 중간에 끊겨도 다시 실행하면 이어서 함):
  cd backend && NAVER_MAINTENANCE_MODE=true python scripts/audit_b2b_analysis.py          # 빠른 모드 (5분 안팎)
  cd backend && NAVER_MAINTENANCE_MODE=true python scripts/audit_b2b_analysis.py --full   # AI 리포트까지 (30~50분)
빠른 모드는 AI 리포트 · 리뷰 감성 AI · 블로그 원문 읽기를 건너뛰고 데이터 값만 점검한다.
결과: 저장소 맨 위 b2b_audit/ 폴더 (report.md · results.jsonl) — 커밋하지 말 것
주의: 화면에서 분석을 연 것과 같아서 상품마다 오늘 가격 한 줄이 가격 이력에 저장된다.
"""
import asyncio
import json
import os
import re
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("JWT_SECRET", "audit")

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "b2b_audit")
RESULTS = os.path.join(OUT_DIR, "results.jsonl")
REPORT = os.path.join(OUT_DIR, "report.md")

QUERIES = [
    "삼성 냉장고", "LG 냉장고", "김치냉장고", "드럼세탁기", "통돌이 세탁기", "건조기",
    "스탠드 에어컨", "벽걸이 에어컨", "공기청정기", "로봇청소기", "무선청소기", "식기세척기",
    "TV 65인치", "에어프라이어", "전기밥솥", "전자레인지", "제습기",
]
PICKS = (0, 4, 9)   # 목록에서 1 · 5 · 10번째 (사용자가 위쪽만 고르지는 않으니)
FULL = "--full" in sys.argv
CONCURRENCY = int(os.getenv("AUDIT_CONCURRENCY", "1" if FULL else "4"))
ONLY = {int(x) for x in os.getenv("AUDIT_ONLY", "").split(",") if x.strip()}   # 예: AUDIT_ONLY=46,47,48


def issues_of(r: dict, picked: dict) -> list[tuple[str, str]]:
    """(심각도, 설명) 목록. 심각도: 오류 > 이상 > 빈값"""
    out = []

    def add(level, msg):
        out.append((level, msg))

    if r.get("_error"):
        add("오류", f"분석 실패: {r['_error']}")
        return out
    if r.get("unsupported"):
        add("오류", "지원하지 않는 카테고리로 나옴")
        return out

    info = r.get("product_info") or {}
    pf = r.get("price_fairness") or {}
    pc = r.get("price_change") or {}
    ai = r.get("ai_report") or {}
    itf = r.get("interest_forecast") or {}
    sf = r.get("sales_forecast") or {}
    comp = (r.get("competitor_comparison") or {})
    rs = r.get("review_sentiment") or {}
    dm = r.get("demand_forecast") or {}

    # ── 기본 정보 ──
    # 모델명이 없는 브랜드(모바 · 로보락 · 다이슨 등)는 화면에서 줄을 숨긴다 → 문제 아님
    for k, label in [("brand", "제조사"), ("release_date", "출시일"), ("image", "이미지"), ("current_price", "현재가")]:
        if not info.get(k):
            add("빈값", f"{label} 없음")
    if not info.get("launch_price") and not info.get("max_price_24m"):
        add("빈값", "출시가 · 24개월 최고가 둘 다 없음")
    cur = info.get("current_price")
    if cur and picked.get("price") and not (0.5 <= cur / picked["price"] <= 2.0):
        add("이상", f"현재가 {cur:,}원이 목록 가격 {picked['price']:,}원과 2배 넘게 다름")
    lp = info.get("launch_price") or info.get("max_price_24m")
    if cur and lp and cur > lp * 1.3:
        add("이상", f"현재가 {cur:,}원이 출시가/최고가 {lp:,}원보다 30% 넘게 비쌈")
    rd = info.get("release_date")
    if rd and re.match(r"\d{4}-\d{2}", rd) and rd > date.today().strftime("%Y-%m"):
        add("이상", f"출시일 {rd}이 미래")
    if rd and re.match(r"\d{4}-\d{2}", rd):
        months = (date.today().year - int(rd[:4])) * 12 + date.today().month - int(rd[5:7])
        if FULL and months > 12 and "신제품" in (ai.get("summary") or ""):
            add("이상", f"출시 {months}개월 된 제품을 AI가 '신제품'이라고 씀")

    # ── 가격 적정성 · 결론 ──
    if pf.get("type") is None:
        add("빈값", "가격 적정성 판단 없음 (가격 데이터 부족)")
    vs = pf.get("vs_hist_pct")
    if vs is not None and abs(vs) >= 40:
        add("이상", f"역대 평균 대비 {vs}% (40% 넘게 차이 · 기준이 다른 가격이 섞였을 수 있음)")
    concl = ai.get("conclusion")
    if concl == "buy" and pf.get("type") == "expensive":
        add("이상", "결론 매입 추천인데 적정성은 비싼 편")
    if concl == "avoid" and pf.get("type") == "cheap":
        add("이상", "결론 매입 비추천인데 적정성은 저렴한 편")
    summ = (ai.get("summary") or "") if FULL else ""
    if FULL and not summ:
        add("빈값", "AI 종합 리포트 요약 없음 (AI 호출 실패일 수 있음)")
    if FULL and not ai.get("conclusion_reason"):
        add("빈값", "결론 이유 없음")
    if vs is not None and summ:
        if vs <= -5 and re.search(r"(높은 편|비싼 편|비싸)", summ):
            add("이상", f"평균보다 {vs}% 싼데 AI 요약에 '비싸다' 표현")
        if vs >= 5 and re.search(r"(낮아 |저렴한 편|저렴해)", summ):
            add("이상", f"평균보다 +{vs}% 비싼데 AI 요약에 '저렴하다' 표현")

    # ── 가격 변동 ──
    ph = pc.get("history") or []
    if len(ph) < 2:
        add("빈값", f"가격 변동 이력 {len(ph)}개 (그래프 비어 보임)")
    else:
        avgs = [h["min_price"] for h in ph]   # 서버와 같이 최저가 기준
        chg = round((ph[-1]["min_price"] - ph[0]["min_price"]) / max(ph[0]["min_price"], 1) * 100, 1)
        if pc.get("change_pct") is not None and chg != pc["change_pct"]:
            add("오류", f"순변동 화면 {pc['change_pct']}% · 재계산 {chg}%")
        rng = round((max(avgs) - min(avgs)) / max(min(avgs), 1) * 100, 1)
        if pc.get("range_pct") is not None and rng != pc["range_pct"]:
            add("오류", f"변동폭 화면 {pc['range_pct']}% · 재계산 {rng}%")
        if rng >= 80:
            add("이상", f"가격 변동폭 {rng}% (조건부 특가 · 다른 상품이 섞였을 수 있음)")
        if cur and not (min(avgs) * 0.5 <= cur <= max(avgs) * 1.5):
            add("이상", f"현재가 {cur:,}원이 가격 이력 범위({min(avgs):,}~{max(avgs):,})와 동떨어짐")
    if dm.get("price_trend_pct") != pc.get("change_pct"):
        add("오류", f"수요 예측 가격 추세 {dm.get('price_trend_pct')} ≠ 가격 변동 {pc.get('change_pct')}")

    # ── 검색량 ──
    ih = itf.get("history") or []
    fc = itf.get("prophet_forecast") or []
    if not ih:
        add("빈값", "검색량 데이터 없음")
    else:
        mx = max(h["ratio"] for h in ih)
        # 최댓값이 100보다 작으면 이번 주(덜 끝난 주)가 최고였던 것 → 정상 (이번 주는 빼고 보여줌)
        if len(ih) < 8:
            add("이상", f"검색량 {len(ih)}주뿐 (검색이 적어 빠진 주가 많음 · 그래프 신뢰 낮음)")
        if fc:
            up = max(x.get("upper", x["ratio"]) for x in fc)
            if up > mx * 1.31:
                add("이상", f"예측 범위 상단 {up}이 실제 최댓값 {mx}의 1.3배 초과")
    reason = itf.get("reason") or ""
    m = re.search(r"([+-]?\d+(?:\.\d+)?)% 변화", reason)
    if m and abs(float(m.group(1))) < 1 and "보합" not in reason:
        add("이상", f"검색량 예측 문장이 1% 미만 변화를 상승/하락으로 씀: {reason[-40:]}")

    # ── 판매량 (품목 전체 기준) ──
    # 판매량은 화면에 쓰지 않음
    sm = re.search(r"([+-]?\d+(?:\.\d+)?)% 변화", sf.get("reason") or "")
    if sm and abs(float(sm.group(1))) >= 40:
        add("이상", f"판매량 예측 {sm.group(1)}% (품목 전체 기준 · 과한 예측일 수 있음)")

    # ── 경쟁 제품 ──
    c = comp.get("competitor")
    if not c:
        add("빈값", "경쟁 제품 없음")
    else:
        if c.get("model_number") and c.get("model_number") == r.get("model_number"):
            add("이상", f"경쟁 제품이 같은 모델 ({c.get('model_number')})")
        if cur and c.get("price") and not (0.3 <= c["price"] / cur <= 3):
            add("이상", f"경쟁 제품 가격 {c['price']:,}원이 현재가와 3배 넘게 차이")
        if FULL and not (comp.get("selected_pros") or comp.get("selected_cons")):
            add("빈값", "선택 제품 장단점 없음")

    # ── 5개 구성 (가격 위치 · 비슷한 제품) ──
    pp = r.get("price_position")
    if not pp:
        add("빈값", "같은 품목 가격 위치 없음")
    elif cur and pp.get("current") != cur:
        add("오류", f"가격 위치의 현재가 {pp.get('current')} ≠ 제품 카드 {cur}")
    sims = r.get("similar_products") or []
    if not sims:
        add("빈값", "비슷한 제품 없음")
    elif len(sims) < 3:
        add("이상", f"비슷한 제품 {len(sims)}개뿐")
    if any(sp.get("model_number") and sp["model_number"] == r.get("model_number") for sp in sims):
        add("이상", "비슷한 제품에 같은 모델이 들어감")

    # ── 리뷰 ──
    n_rev = (rs.get("pos") or 0) + (rs.get("neg") or 0)
    if n_rev == 0:
        add("빈값", "리뷰 감성 분석 0건")
    elif n_rev < 3:
        add("이상", f"리뷰 {n_rev}건뿐 (감성 점수 신뢰 낮음)")
    if FULL and n_rev and not (rs.get("positive_summary") or rs.get("negative_summary")):
        add("빈값", "리뷰 요약 없음")
    return out


def short(r: dict) -> dict:
    """보고서 · 재분석에 필요한 값만 남긴다 (리뷰 원문 등 큰 값 제외)"""
    info = r.get("product_info") or {}
    pf = r.get("price_fairness") or {}
    pc = r.get("price_change") or {}
    return {
        "category": r.get("category"), "model": r.get("model_number"), "info": info,
        "conclusion": (r.get("ai_report") or {}).get("conclusion_label"),
        "summary": (r.get("ai_report") or {}).get("summary"),
        "fairness": {k: pf.get(k) for k in ("type", "label", "vs_hist_pct", "current_price", "hist_avg_price", "reason")},
        "price_change": {"n": len(pc.get("history") or []), "change_pct": pc.get("change_pct"),
                         "range_pct": pc.get("range_pct"), "reason": pc.get("reason"),
                         "history": [(h["date"], h["min_price"]) for h in (pc.get("history") or [])][-15:]},
        "interest": {"keyword": r.get("trend_keyword"), "n": len((r.get("interest_forecast") or {}).get("history") or []),
                     "reason": (r.get("interest_forecast") or {}).get("reason")},
        "sales_reason": (r.get("sales_forecast") or {}).get("reason"),
        "competitor": {k: ((r.get("competitor_comparison") or {}).get("competitor") or {}).get(k)
                       for k in ("title", "price", "model_number")},
        "reviews": {k: (r.get("review_sentiment") or {}).get(k) for k in ("score", "pos", "neg")},
        "n_reviews": len((r.get("review_sentiment") or {}).get("reviews") or []),
        "price_position": r.get("price_position"),
        "similar": [(p.get("brand"), p.get("title"), p.get("price")) for p in (r.get("similar_products") or [])],
    }


async def main():
    from app.routers import b2b_search_analysis as sa
    from app.routers.b2b_search_analysis import get_product_search, _search_analysis
    if not FULL:
        # 빠른 모드: AI · 블로그 원문은 건너뛴다 (분석 함수는 AI가 실패한 것처럼 규칙 문장으로 채운다)
        async def _no_ai(*a, **k):
            raise RuntimeError("audit fast mode")

        async def _none(*a, **k):
            return None
        sa._groq_create = _no_ai
        sa._fetch_full_review_text = _none
        sa._classify_reviews_sentiment = _none
    os.makedirs(OUT_DIR, exist_ok=True)
    done = set()
    if os.path.exists(RESULTS):
        with open(RESULTS, encoding="utf-8") as f:
            done = {json.loads(line)["title"] for line in f if line.strip()}

    targets = []
    for q in QUERIES:
        try:
            items = (await get_product_search(q, {}))["items"]
        except Exception as e:
            print(f"[목록 실패] {q}: {e}")
            continue
        for i in PICKS:
            if i < len(items):
                targets.append((q, items[i]))
    print(f"점검 대상 {len(targets)}개 · 이미 끝난 것 {len(done)}개\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()

    async def one(n, q, it):
        title = it["title"]
        if title in done or (ONLY and n not in ONLY):
            return
        async with sem:
            t0 = time.time()
            try:
                r = await asyncio.wait_for(_search_analysis(title, q, True), timeout=180)
            except Exception as e:
                r = {"_error": f"{type(e).__name__}: {e}"[:200]}
            iss = issues_of(r, it)
            row = {"n": n, "query": q, "title": title, "list_price": it["price"], "sec": round(time.time() - t0),
                   "mode": "full" if FULL else "fast", "issues": iss,
                   "data": short(r) if not r.get("_error") and not r.get("unsupported") else r}
            async with lock:
                with open(RESULTS, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            print(f"[{n}/{len(targets)}] {row['sec']}초 · 문제 {len(iss)}개 · {title[:40]}")
            if FULL:
                await asyncio.sleep(3)   # AI 호출 한도 보호

    await asyncio.gather(*[one(n, q, it) for n, (q, it) in enumerate(targets, 1)])
    write_report()


def write_report():
    rows = []
    with open(RESULTS, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    from collections import Counter
    cnt = Counter()
    for r in rows:
        for level, msg in r["issues"]:
            cnt[(level, re.sub(r"[\d,.+\-]+%?|\(.*?\)|'.*?'|:.*", "", msg).strip())] += 1
    lines = [f"# B2B 분석 일괄 점검 ({date.today()}) · 상품 {len(rows)}개", "", "## 문제 종류별 개수", ""]
    for (level, kind), c in sorted(cnt.items(), key=lambda x: (["오류", "이상", "빈값"].index(x[0][0]), -x[1])):
        lines.append(f"- [{level}] {kind} — {c}개")
    lines += ["", "## 상품별", ""]
    for r in rows:
        lines.append(f"### {r['n']}. {r['title'][:60]} ({r['query']} · 목록가 {r['list_price']:,}원)")
        if not r["issues"]:
            lines.append("- 문제 없음")
        for level, msg in r["issues"]:
            lines.append(f"- [{level}] {msg}")
        lines.append("")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n보고서: {REPORT}")


if __name__ == "__main__":
    if "--report" in sys.argv:
        write_report()
    else:
        asyncio.run(main())
