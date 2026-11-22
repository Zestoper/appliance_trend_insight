"""검색 분석 화면의 숫자가 원본 데이터와 맞는지 다시 계산해서 비교한다.
- 검색량 추이 · 예측 / 가격 변동 분석 / 가격 적정성 / 수요 예측
실행: cd backend && python scripts/check_analysis.py "삼성전자 비스포크 김치플러스 RQ33DG71J2ET"
(화면에서 분석을 연 것과 같아서 오늘 가격 한 줄이 가격 이력에 저장된다)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("JWT_SECRET", "check")


def pct(a, b):
    return round((a - b) / max(b, 1) * 100, 1)


def mark(ok):
    return "✓" if ok else "✗ 다름"


async def main(q: str):
    from app.routers.b2b_search_analysis import _search_analysis
    r = await _search_analysis(q, "", True)
    if r.get("unsupported"):
        print("지원하지 않는 카테고리:", r.get("message"))
        return

    print("=" * 70, "\n[검색량 추이 · 예측]")
    f = r["interest_forecast"]
    hist, fc = f["history"], f["prophet_forecast"]
    print(f"모델: {f['model']} · 실제 {len(hist)}주 · 예측 {len(fc)}주")
    print("실제:", [(h["period"][5:10], h["ratio"]) for h in hist])
    if hist:
        print(f"실제 최댓값 {max(h['ratio'] for h in hist)} (데이터랩은 기간 최댓값=100이어야 함)")
    if fc:
        print("예측 앞 5주:", [(x["period"][5:10], x["ratio"], x.get("lower"), x.get("upper")) for x in fc[:5]])
        print("예측 끝:", (fc[-1]["period"], fc[-1]["ratio"], fc[-1].get("lower"), fc[-1].get("upper")))
        print(f"예측 범위 상단 최댓값 {max(x.get('upper', x['ratio']) for x in fc)}")
        if hist:
            print(f"재계산: 마지막 실제 {hist[-1]['ratio']} → 예측 끝 {fc[-1]['ratio']} = {pct(fc[-1]['ratio'], hist[-1]['ratio'])}%")
    print("문장:", f["reason"])

    print("=" * 70, "\n[가격 변동 분석]")
    pc = r["price_change"]
    ph = pc["history"]
    print(f"점 {len(ph)}개")
    for h in ph:
        print(f"  {h['date']}  최저 {h['min_price']:>10,}  평균 {h['avg_price']:>10,}")
    if len(ph) >= 2:
        avgs = [h["min_price"] for h in ph]
        c = pct(ph[-1]["min_price"], ph[0]["min_price"])
        rg = round((max(avgs) - min(avgs)) / max(min(avgs), 1) * 100, 1)
        print(f"순변동 화면 {pc['change_pct']}% / 재계산 {c}% {mark(c == pc['change_pct'])}")
        print(f"변동폭 화면 {pc['range_pct']}% / 재계산 {rg}% {mark(rg == pc['range_pct'])}")
    print("문장:", pc["reason"])

    print("=" * 70, "\n[가격 적정성 · 매입 신호]")
    pf = r["price_fairness"]
    import datetime as _dt
    today = str(_dt.date.today())
    prior = [h for h in ph if h["date"] != today]
    if prior and pf["current_price"]:
        ha = int(sum(h["min_price"] for h in prior) / len(prior))
        v = pct(pf["current_price"], ha)
        print(f"현재가 {pf['current_price']:,} · 역대 평균 화면 {pf['hist_avg_price']:,} / 재계산 {ha:,} {mark(ha == pf['hist_avg_price'])}")
        print(f"평균 대비 화면 {pf['vs_hist_pct']}% / 재계산 {v}% {mark(v == pf['vs_hist_pct'])}")
    print(f"적정성 {pf['label']} · 결론 {r['ai_report']['conclusion_label']}")

    print("=" * 70, "\n[수요 예측]")
    d = r["demand_forecast"]
    print(f"가격 추세 {d['price_trend_pct']}% (가격 변동 순변동 {pc['change_pct']}%와 같아야 함) {mark(d['price_trend_pct'] == pc['change_pct'])}")
    print("헤드라인:", d["headline"])
    print("이유:", d["reason"])

    print("=" * 70, "\n[판매량 추이]")
    s = r["sales_forecast"]
    print("실제:", [(h["period"][:7], h["ratio"]) for h in s["history"]])
    print("예측:", [(h["period"][:7], h["ratio"]) for h in s["prophet_forecast"]])
    print("문장:", s["reason"])


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "삼성전자 비스포크 김치플러스 RQ33DG71J2ET"))
