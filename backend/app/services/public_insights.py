"""공공데이터를 화면에 쓰는 기능 3가지.

1. 날씨 · 미세먼지와 검색량 (기상청 · 에어코리아)
   - 같은 주의 날씨와 검색량이 얼마나 같이 움직였는지(상관계수)와
     "기온 1도 오를 때 검색량 몇 %"를 계산한다.
   - 1주 앞 예측에 '지난주 날씨가 작년보다 얼마나 더웠나'를 반영하면 오차가 줄어드는지 백테스트한다
     (forecast_models.evaluate_weather).
2. 소비자원 위해(안전사고) 접수 TOP 3
3. 에너지공단 월간 소비전력량 × 전기요금 → 한 달 전기료
"""
import math
from collections import Counter
from datetime import date, timedelta

from app.services.naver_cache import get_db_cache_stale

# 품목 → (날씨 값 키, 화면 이름, 단위, '이만큼 오를 때' 기준 폭, 캐시 키)
WEATHER_VARS: dict[str, tuple[str, str, str, float, str]] = {
    "에어컨":     ("temp",     "기온",       "°C",   1,  "ext:kma:history"),
    "선풍기":     ("temp",     "기온",       "°C",   1,  "ext:kma:history"),
    "제습기":     ("humidity", "습도",       "%",    10, "ext:kma:history"),
    "가습기":     ("humidity", "습도",       "%",    10, "ext:kma:history"),
    "공기청정기": ("pm25",     "초미세먼지", "㎍/㎥", 10, "ext:airkorea:history"),
}

# 한전 주택용(저압) 전력량요금 2단계(201~400kWh) 단가 — 기본요금 · 부가세 · 기금 제외.
# 보통 가정의 한 달 사용량이 2단계 구간이라 가전 하나를 더 쓸 때 붙는 요금에 가장 가깝다.
ELECTRICITY_WON_PER_KWH = 214.6


def _to_date(s: str) -> date | None:
    s = (s or "").replace("-", "")[:8]
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (ValueError, IndexError):
        return None


def weekly_weather(daily: list[dict], key: str, periods: list[str]) -> dict[str, float]:
    """일별 날씨를 검색량 주(period 시작일부터 7일)에 맞춰 주 평균으로 묶는다."""
    starts = {p[:10] for p in periods}
    buckets: dict[str, list[float]] = {}
    for it in daily:
        d = _to_date(it.get("date", ""))
        v = it.get(key)
        if d is None or v is None:
            continue
        for back in range(7):
            p = (d - timedelta(days=back)).isoformat()
            if p in starts:
                buckets.setdefault(p, []).append(float(v))
                break
    return {p: sum(v) / len(v) for p, v in buckets.items() if len(v) >= 4}


async def load_weekly_weather(category: str, periods: list[str]) -> tuple[dict[str, float], tuple] | None:
    spec = WEATHER_VARS.get(category or "")
    if not spec:
        return None
    cached = await get_db_cache_stale(spec[4])
    items = (cached or {}).get("items") or []
    if not items:
        return None
    return weekly_weather(items, spec[0], periods), spec


def _josa(word: str, with_batchim: str, without: str) -> str:
    """받침 유무에 맞는 조사 (기온과 / 습도와)."""
    code = ord(word[-1]) - 0xAC00
    return word + (with_batchim if 0 <= code <= 11171 and code % 28 else without)


def _corr(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


async def weather_signal(category: str | None, weekly_search: list[dict], keyword: str | None = None) -> dict | None:
    """검색량(주별)과 날씨가 같이 움직인 정도를 계산해 화면용으로 돌려준다."""
    if not weekly_search:
        return None
    loaded = await load_weekly_weather(category, [d["period"] for d in weekly_search])
    if not loaded:
        return None
    wk, (key, label, unit, step, _) = loaded
    pairs = [(d["period"][:10], wk[d["period"][:10]], float(d["ratio"]))
             for d in weekly_search if d["period"][:10] in wk]
    if len(pairs) < 10:
        return None
    xs = [p[1] for p in pairs]
    ys = [p[2] for p in pairs]
    r = _corr(xs, ys)
    if r is None:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    per_step_pct = round(slope * step / max(my, 1e-6) * 100, 1)

    strength = "강하게" if abs(r) >= 0.7 else ("어느 정도" if abs(r) >= 0.4 else "약하게")
    direction = "같은 방향으로" if r > 0 else "반대 방향으로"
    step_txt = f"{int(step)}{unit}" if unit != "%" else f"{int(step)}%p"
    text = (f"최근 {len(pairs)}주 동안 검색량은 {_josa(label, '과', '와')} {direction} {strength} 움직였어요 "
            f"(상관계수 {r:+.2f}). {_josa(label, '이', '가')} {step_txt} 높을수록 검색량이 평균 "
            f"{abs(per_step_pct)}% {'많았어요' if per_step_pct >= 0 else '적었어요'}.")

    # 지난주 날씨를 작년 같은 주와 비교 (다음 주 수요를 미리 짐작하는 근거)
    latest = None
    last_p = pairs[-1][0]
    ly_p = (date.fromisoformat(last_p) - timedelta(days=364)).isoformat()
    if ly_p in wk:
        diff = round(wk[last_p] - wk[ly_p], 1)
        latest = {"period": last_p, "value": round(wk[last_p], 1), "last_year": round(wk[ly_p], 1), "diff": diff}
        gap = f"{abs(diff)}{unit if unit != '%' else '%p'}"
        compare = "작년 같은 주와 같아요" if diff == 0 else f"작년 같은 주보다 {gap} {'높아요' if diff > 0 else '낮아요'}"
        text += f" 지난주 평균 {_josa(label, '은', '는')} {latest['value']}{unit}로 {compare}."

    return {
        "variable": key,
        "keyword": keyword or category,
        "label": label,
        "title": f"{_josa(label, '과', '와')} 검색량",
        "unit": unit,
        "weeks": len(pairs),
        "corr": round(r, 2),
        "per_step_pct": per_step_pct,
        "step": step,
        "latest": latest,
        "series": [{"period": p, "value": round(v, 1), "ratio": s} for p, v, s in pairs[-52:]],
        "text": text,
    }


async def safety_top(category: str | None) -> dict | None:
    """소비자원 위해(안전사고) 접수 중 이 품목에서 많이 나온 증상 TOP 3."""
    if not category:
        return None
    cached = await get_db_cache_stale(f"ext:kca:{category}")
    items = (cached or {}).get("items") or []
    skip = {"", "-", "기타", "해당없음", "해당 없음", "불명", "없음", "미상", "None", "null"}
    basis, labels = None, []
    # 원인(예: 화재 · 감전)이 있으면 원인으로, 없으면 증상(예: 화상)으로 센다
    for field, name in (("cause", "원인"), ("content", "증상"), ("injury", "다친 부위")):
        vals = [(it.get(field) or "").strip() for it in items]
        vals = [v for v in vals if v not in skip]
        if len(vals) >= 3:
            basis, labels = name, vals
            break
    if not labels:
        return None
    total = len(labels)
    top = [{"label": k, "count": c, "pct": round(c / total * 100)} for k, c in Counter(labels).most_common(3)]
    return {
        "total": total,
        "basis": basis,
        "top": top,
        "text": f"소비자원에 접수된 {category} 안전사고 {total}건을 {basis}별로 보면 '{top[0]['label']}'"
                f"{_josa(top[0]['label'], '이', '가')[len(top[0]['label']):]} 가장 많아요({top[0]['pct']}%).",
    }


def monthly_cost(kwh_month: float | None = None, won_month: float | None = None) -> int | None:
    """한 달 전기료(원). 에너지공단이 월간 에너지비용을 직접 주면 그 값, 아니면 kWh × 단가."""
    if won_month and won_month > 0:
        return int(round(won_month, -1))
    if kwh_month and kwh_month > 0:
        return int(round(kwh_month * ELECTRICITY_WON_PER_KWH, -1))
    return None
