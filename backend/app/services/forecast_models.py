"""주간 검색량 예측 후보 모델과 품목별 자동 선택.

왜 이렇게 하나
- 한 모델(Holt-Winters)로 전 품목을 예측했더니 백테스트(과거 8주를 가리고 맞혀보기)에서
  '지난주 값 유지'보다도 오차가 컸다 (평균 37.4% vs 33.8%). 품목마다 잘 맞는 방식이 달랐다
  (냉장고 · TV는 최근 수준 유지가 강하고, 제습기 · 가습기는 계절 반영이 도움).
- 그래서 품목마다 후보 모델들을 과거 여러 시점에서 백테스트하고 오차가 가장 작은 모델을 쓴다.
- 전부 순수 파이썬 · 품목당 숫자 200여 개라 메모리를 거의 쓰지 않는다 (새 라이브러리 없음).
"""
import math
from datetime import date, timedelta

HORIZON = 8                       # 백테스트에서 맞혀볼 주 수
ORIGINS = (8, 16, 24, 32)         # 끝에서 몇 주 전 시점들에서 각각 예측해볼지 (여러 계절 구간을 고르게)
SEASON = 52
MODEL_LABELS = {
    "hw": "Holt-Winters",
    "naive": "최근값 유지",
    "mean4": "최근 4주 평균",
    "season30": "최근 수준 + 작년 계절 변화 30% 반영",
    "season50": "최근 수준 + 작년 계절 변화 50% 반영",
    "season70": "최근 수준 + 작년 계절 변화 70% 반영",
    "season100": "최근 수준 + 작년 계절 변화 그대로 반영",
}


def _vals(data: list[dict]) -> list[float]:
    return [float(d["ratio"]) for d in data]


def _naive(ys: list[float], h: int) -> list[float]:
    return [ys[-1]] * h


def _mean4(ys: list[float], h: int) -> list[float]:
    tail = ys[-4:]
    return [sum(tail) / len(tail)] * h


def _season_blend(ys: list[float], h: int, weight: float) -> list[float] | None:
    """최근 4주 평균 × (1 + 작년 같은 시기 변화율 × weight).
    작년 변화율 = (작년 t+k주 값) / (작년 t 시점 앞 4주 평균) - 1"""
    n = len(ys)
    if n < SEASON + 4:
        return None
    level = sum(ys[-4:]) / 4
    base_ly = sum(ys[n - SEASON - 4:n - SEASON]) / 4
    if base_ly <= 0:
        return None
    out = []
    for k in range(1, h + 1):
        idx = n - SEASON + k - 1
        ly = ys[idx] if idx < n else ys[-1]
        change = ly / base_ly - 1
        out.append(max(0.0, level * (1 + weight * change)))
    return out


def predict(model: str, data: list[dict], h: int, hw_fn=None) -> list[float] | None:
    ys = _vals(data)
    if len(ys) < 8:
        return None
    if model == "naive":
        return _naive(ys, h)
    if model == "mean4":
        return _mean4(ys, h)
    if model.startswith("season"):
        return _season_blend(ys, h, int(model[6:]) / 100)
    if model == "hw" and hw_fn is not None:
        fc = hw_fn(data, h, "W")
        return [r["ratio"] for r in fc][:h] or None
    return None


def mape(actual: list[float], pred: list[float]) -> float | None:
    pairs = [(a, p) for a, p in zip(actual, pred) if a > 0]
    if not pairs:
        return None
    return sum(abs(a - p) / a for a, p in pairs) / len(pairs) * 100


def evaluate(data: list[dict], hw_fn=None) -> dict[str, float]:
    """후보마다 여러 시점에서 HORIZON주를 가리고 예측해 평균 오차(MAPE %)를 낸다."""
    scores: dict[str, list[float]] = {m: [] for m in MODEL_LABELS}
    for back in ORIGINS:
        if len(data) < back + 20:
            continue
        train = data[:len(data) - back]
        actual = _vals(data[len(data) - back:len(data) - back + HORIZON])
        for m in MODEL_LABELS:
            pred = predict(m, train, len(actual), hw_fn)
            if pred:
                e = mape(actual, pred)
                if e is not None:
                    scores[m].append(e)
    return {m: round(sum(v) / len(v), 1) for m, v in scores.items() if len(v) == len(ORIGINS)}


def best_model(scores: dict[str, float]) -> str:
    return min(scores, key=scores.get) if scores else "hw"


def forecast_rows(model: str, data: list[dict], periods: int, hw_fn) -> list[dict]:
    """선택된 모델로 화면용 예측(기간 · 값 · 신뢰구간)을 만든다. 형식은 Holt-Winters 결과와 같다."""
    if model == "hw":
        return hw_fn(data, periods, "W")
    pred = predict(model, data, periods)
    if not pred:
        return hw_fn(data, periods, "W")
    ys = _vals(data)
    diffs = [ys[i] - ys[i - 1] for i in range(max(1, len(ys) - 26), len(ys))]
    std = math.sqrt(sum(d * d for d in diffs) / max(len(diffs), 1))
    cap = round(max(max(ys), 1.0) * 1.3, 1)
    last = date.fromisoformat(data[-1]["period"][:10])
    rows = []
    for h, p in enumerate(pred, 1):
        band = 1.96 * std * math.sqrt(h)
        ratio = min(cap, round(p, 1))
        rows.append({
            "period": (last + timedelta(days=7 * h)).isoformat(),
            "ratio": ratio,
            "lower": min(ratio, max(0.0, round(p - band, 1))),
            "upper": min(cap, max(ratio, round(p + band, 1))),
        })
    return rows


def evaluate_weather(data: list[dict], weather: dict[str, float], model: str, hw_fn=None,
                     test_weeks: int = 26, min_fit: int = 12) -> dict | None:
    """1주 앞 예측에 날씨를 더하면 오차가 줄어드는지 백테스트한다.

    - 기본 예측: 품목별로 골라둔 모델의 1주 앞 예측
    - 날씨 반영: 기본 예측 × (1 + β × 지난주 날씨의 작년 대비 차이)
      지난주 날씨는 예측하는 시점에 이미 알고 있는 값이라 미래 정보를 몰래 쓰지 않는다.
      β는 그 시점 이전 주들만으로 '날씨 차이 vs 기본 예측이 빗나간 비율'을 맞춰 정한다.
    - 마지막 test_weeks주를 한 주씩 예측해 두 방식의 평균 오차(MAPE %)를 비교한다.
    """
    periods = [d["period"][:10] for d in data]
    ys = _vals(data)
    n = len(ys)

    def anomaly(i: int) -> float | None:
        p = periods[i]
        ly = (date.fromisoformat(p) - timedelta(days=364)).isoformat()
        if p in weather and ly in weather:
            return weather[p] - weather[ly]
        return None

    rows = []   # (t, 기본 예측, 지난주 날씨 차이, 실제값)
    for t in range(max(SEASON + 8, n - test_weeks - min_fit - 14), n):
        x = anomaly(t - 1)
        if x is None:
            continue
        base = predict(model, data[:t], 1, hw_fn)
        if not base or base[0] <= 0:
            continue
        rows.append((t, base[0], x, ys[t]))

    base_err, w_err, beta = [], [], 0.0
    for j, (t, b, x, a) in enumerate(rows):
        past = rows[:j]
        if len(past) < min_fit or t < n - test_weeks or a <= 0:
            continue
        den = sum(px * px for _, _, px, _ in past)
        beta = sum(px * (pa / pb - 1) for _, pb, px, pa in past) / den if den > 0 else 0.0
        p = max(0.0, b * (1 + beta * x))
        base_err.append(abs(a - b) / a)
        w_err.append(abs(a - p) / a)
    if len(base_err) < 8:
        return None
    return {
        "weeks": len(base_err),
        "base_mape": round(sum(base_err) / len(base_err) * 100, 1),
        "weather_mape": round(sum(w_err) / len(w_err) * 100, 1),
        "beta": round(beta, 4),
    }
