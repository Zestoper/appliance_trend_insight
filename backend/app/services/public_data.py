"""
공공데이터 API 수집 서비스
- 기상청 (KMA): 기온/습도 이력
- 에어코리아: PM2.5/PM10 이력
- 통계청 KOSIS: 소비자물가지수
- 관세청: 수출입 물량 (TV/에어컨/냉장고 HS코드)
- 한전 KEPCO: 전기요금 지수
- 에너지공단 KEMCO: 에너지효율등급 비율
- 소비자원 KCA: 피해구제 접수
"""
import os
import asyncio
import logging
from datetime import date, timedelta, datetime

import httpx

logger = logging.getLogger(__name__)

PUBLIC_DATA_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")
KOSIS_KEY       = os.getenv("KOSIS_API_KEY", "")
KEPCO_KEY       = os.getenv("KEPCO_API_KEY", "")

# 카테고리별 사용할 외부 변수
EXT_VARS: dict[str, list[str]] = {
    "에어컨":     ["kma_temp", "kma_humidity", "kepco_rate"],
    "선풍기":     ["kma_temp"],
    "제습기":     ["kma_temp", "kma_humidity"],
    "가습기":     ["kma_humidity"],
    "공기청정기": ["air_pm25", "air_pm10"],
    "냉장고":     ["kma_temp", "kepco_rate"],
    "세탁기":     ["kepco_rate"],
    "건조기":     ["kepco_rate"],
    "TV":         ["customs_tv"],
    "로봇청소기": [],
    "식기세척기": [],
    "에어프라이어": [],
    "전기밥솥":   [],
}

# 관세청 HS 코드
HS_CODES = {
    "TV":   "8528",  # 영상기기
    "에어컨": "8415",  # 에어컨
    "냉장고": "8418",  # 냉장고
}


def _base_params(extra: dict) -> dict:
    return {"serviceKey": PUBLIC_DATA_KEY, "dataType": "JSON", **extra}


async def fetch_kma_history(days: int = 730) -> list[dict]:
    """기상청 ASOS 일자료: 기온/습도 (서울 108번 관측소)"""
    if not PUBLIC_DATA_KEY:
        return []
    end   = date.today()
    start = end - timedelta(days=days)
    url = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
    params = _base_params({
        "numOfRows": days + 5,
        "pageNo":    1,
        "dataCd":    "ASOS",
        "dateCd":    "DAY",
        "startDt":   start.strftime("%Y%m%d"),
        "endDt":     end.strftime("%Y%m%d"),
        "stnIds":    "108",  # 서울
    })
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, params=params)
        items = r.json()["response"]["body"]["items"]["item"]
        return [
            {
                "date":     item["tm"],           # YYYYMMDD
                "temp":     float(item.get("avgTa") or 0),
                "humidity": float(item.get("avgRhm") or 0),
            }
            for item in items
            if item.get("avgTa") not in (None, "")
        ]
    except Exception as e:
        logger.warning("[KMA] 기상청 이력 수집 실패: %s", e)
        return []


async def fetch_airkorea_history(days: int = 90) -> list[dict]:
    """에어코리아 대기오염 이력 (종로구, 최근 90일)"""
    if not PUBLIC_DATA_KEY:
        return []
    url = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"
    # dataTerm: DAILY(24h) / MONTH(1개월) / 3MONTH(3개월)
    term = "3MONTH" if days >= 60 else "MONTH"
    params = _base_params({
        "stationName": "종로구",
        "dataTerm":    term,
        "pageNo":      1,
        "numOfRows":   200,
        "ver":         "1.3",
    })
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, params=params)
        items = r.json()["response"]["body"]["items"]
        return [
            {
                "date":  item["dataTime"][:10].replace("-", ""),  # YYYYMMDD
                "pm25":  float(item.get("pm25Value") or 0),
                "pm10":  float(item.get("pm10Value") or 0),
            }
            for item in items
            if item.get("pm25Value") not in (None, "-", "")
        ]
    except Exception as e:
        logger.warning("[AirKorea] 이력 수집 실패: %s", e)
        return []


async def fetch_kosis_cpi() -> list[dict]:
    """통계청 KOSIS: 소비자물가지수 월별 (최근 2년)"""
    if not KOSIS_KEY:
        return []
    end_ym   = date.today().strftime("%Y%m")
    start_ym = (date.today() - timedelta(days=730)).strftime("%Y%m")
    url = "https://kosis.kr/openapi/statisticsData.do"
    params = {
        "method":      "getList",
        "apiKey":      KOSIS_KEY,
        "objId":       "DT_1J20005",   # 소비자물가지수
        "itmId":       "T10",          # 종합지수
        "prdSe":       "M",            # 월별
        "startPrdDe":  start_ym,
        "endPrdDe":    end_ym,
        "format":      "json",
        "jsonVD":      "Y",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, params=params)
        items = r.json()
        return [
            {
                "ym":  item["PRD_DE"],     # YYYYMM
                "cpi": float(item["DT"]),
            }
            for item in items
            if item.get("DT")
        ]
    except Exception as e:
        logger.warning("[KOSIS] CPI 수집 실패: %s", e)
        return []


async def fetch_customs_trade(category: str) -> list[dict]:
    """관세청 수출입 통계: 카테고리별 수입 물량 (월별)"""
    hs = HS_CODES.get(category)
    if not hs or not PUBLIC_DATA_KEY:
        return []
    end   = date.today()
    start = end - timedelta(days=730)
    url   = "https://unipass.customs.go.kr/openapi/rest/trtImpExpStatsService/getTrtImpExpStatsInfo"
    params = {
        "crkyCn":    PUBLIC_DATA_KEY,
        "strtMmDt":  start.strftime("%Y%m"),
        "endMmDt":   end.strftime("%Y%m"),
        "hsSgn":     hs,
        "impExpTp":  "1",   # 수입
        "statSgn":   "2",   # 물량(kg)
        "pageIndex": "1",
        "pageSize":  "30",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, params=params)
        items = r.json().get("trtImpExpStatsInfo", [])
        return [
            {
                "ym":     item["mmDt"],
                "volume": float(item.get("wegt") or 0),
            }
            for item in items
        ]
    except Exception as e:
        logger.warning("[관세청] %s 수집 실패: %s", category, e)
        return []


async def fetch_kepco_rate() -> list[dict]:
    """한전 전기요금 변동 이력 (분기별 kWh 단가)"""
    if not KEPCO_KEY:
        return []
    url = "https://bigdata.kepco.co.kr/openapi/v1/powerUsage/powerCost/getList.do"
    params = {
        "apiKey":    KEPCO_KEY,
        "numOfRows": 20,
        "pageNo":    1,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, params=params)
        items = r.json().get("data", [])
        return [
            {
                "ym":   item.get("basYm"),
                "rate": float(item.get("tcoAmt") or 0),
            }
            for item in items
        ]
    except Exception as e:
        logger.warning("[KEPCO] 전기요금 수집 실패: %s", e)
        return []


async def fetch_kemco_efficiency(category: str) -> dict:
    """에너지공단: 카테고리별 에너지효율 1등급 비율"""
    if not PUBLIC_DATA_KEY:
        return {}
    cat_code_map = {
        "에어컨":  "1",
        "냉장고":  "2",
        "세탁기":  "4",
        "TV":      "5",
        "건조기":  "10",
    }
    code = cat_code_map.get(category)
    if not code:
        return {}
    url = "https://apis.data.go.kr/B552895/eficiencyRatingInfoService/getEfficProductList"
    params = _base_params({"numOfRows": 200, "pageNo": 1, "prductClsfNo": code})
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, params=params)
        items = r.json()["response"]["body"]["items"]["item"]
        total = len(items)
        grade1 = sum(1 for i in items if str(i.get("energyGrade", "")) == "1")
        return {
            "total_products": total,
            "grade1_ratio":   round(grade1 / total * 100, 1) if total else 0,
            "fetched_at":     date.today().isoformat(),
        }
    except Exception as e:
        logger.warning("[KEMCO] %s 효율등급 수집 실패: %s", category, e)
        return {}


async def fetch_kca_complaints(category: str) -> list[dict]:
    """소비자원: 위해 피해 접수 건수 (카테고리별)"""
    if not PUBLIC_DATA_KEY:
        return []
    url = "https://apis.data.go.kr/1130000/CsHarmInfoService/getHarmInfoList"
    params = _base_params({
        "numOfRows": 100,
        "pageNo":    1,
        "srchWrd":   category,
    })
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.get(url, params=params)
        body = r.json()["response"]["body"]
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        return [
            {
                "date":    item.get("rceptDt", "")[:10],
                "content": item.get("harmCntn", ""),
                "product": item.get("prductNm", ""),
            }
            for item in items
        ]
    except Exception as e:
        logger.warning("[KCA] %s 소비자원 수집 실패: %s", category, e)
        return []


async def get_ext_dataframe(category: str, ds_dates) -> "pd.DataFrame | None":
    """
    Prophet/XGBoost df에 merge할 외부 변수 DataFrame 반환.
    ds_dates: pd.DatetimeIndex (학습 df의 날짜 목록)
    반환: DataFrame(ds, 외부변수들) 또는 None
    """
    vars_needed = EXT_VARS.get(category, [])
    if not vars_needed:
        return None

    try:
        import pandas as pd
        from app.services.naver_cache import get_db_cache as _get_cache

        rows: dict[str, dict] = {}  # date_str -> {var: val}

        # KMA 기온/습도
        if any(v.startswith("kma_") for v in vars_needed):
            kma = await _get_cache("ext:kma:history")
            if kma and kma.get("items"):
                for item in kma["items"]:
                    d = item["date"]
                    rows.setdefault(d, {})
                    rows[d]["kma_temp"]     = item.get("temp", 0)
                    rows[d]["kma_humidity"] = item.get("humidity", 0)

        # 에어코리아 PM2.5/PM10
        if any(v.startswith("air_") for v in vars_needed):
            air = await _get_cache("ext:airkorea:history")
            if air and air.get("items"):
                for item in air["items"]:
                    d = item["date"]
                    rows.setdefault(d, {})
                    rows[d]["air_pm25"] = item.get("pm25", 0)
                    rows[d]["air_pm10"] = item.get("pm10", 0)

        # 통계청 CPI (월별 → 일별 forward fill)
        if "cpi" in vars_needed:
            cpi_data = await _get_cache("ext:kosis:cpi")
            if cpi_data and cpi_data.get("items"):
                for item in cpi_data["items"]:
                    ym = item["ym"]  # YYYYMM
                    for d in range(1, 32):
                        try:
                            dt = datetime.strptime(f"{ym}{d:02d}", "%Y%m%d")
                            rows.setdefault(dt.strftime("%Y%m%d"), {})
                            rows[dt.strftime("%Y%m%d")]["cpi"] = item["cpi"]
                        except ValueError:
                            pass

        # 한전 요금 (분기 → forward fill)
        if "kepco_rate" in vars_needed:
            kepco = await _get_cache("ext:kepco:rate")
            if kepco and kepco.get("items"):
                sorted_items = sorted(kepco["items"], key=lambda x: x.get("ym", ""))
                for item in sorted_items:
                    ym = item.get("ym", "")
                    if ym:
                        for d in range(1, 32):
                            try:
                                dt = datetime.strptime(f"{ym}{d:02d}", "%Y%m%d")
                                rows.setdefault(dt.strftime("%Y%m%d"), {})
                                rows[dt.strftime("%Y%m%d")]["kepco_rate"] = item["rate"]
                            except ValueError:
                                pass

        # 관세청 수입물량 (월별)
        customs_var = next((v for v in vars_needed if v.startswith("customs_")), None)
        if customs_var:
            customs = await _get_cache(f"ext:customs:{category}")
            if customs and customs.get("items"):
                for item in customs["items"]:
                    ym = item.get("ym", "")
                    vol = item.get("volume", 0)
                    for d in range(1, 32):
                        try:
                            dt = datetime.strptime(f"{ym}{d:02d}", "%Y%m%d")
                            rows.setdefault(dt.strftime("%Y%m%d"), {})
                            rows[dt.strftime("%Y%m%d")][customs_var] = vol
                        except ValueError:
                            pass

        if not rows:
            return None

        ext_df = pd.DataFrame(
            [{"ds": datetime.strptime(k, "%Y%m%d"), **v} for k, v in rows.items()]
        ).sort_values("ds")

        # 주별 집계 (Prophet 학습 df가 주별이므로)
        ext_df["week"] = ext_df["ds"].dt.to_period("W").dt.start_time
        agg_dict = {c: "mean" for c in ext_df.columns if c not in ("ds", "week")}
        ext_weekly = ext_df.groupby("week").agg(agg_dict).reset_index()
        ext_weekly = ext_weekly.rename(columns={"week": "ds"})

        # 학습 df 날짜에 nearest join (주별 경계 불일치 허용 ±4일)
        result_rows = []
        for ds in ds_dates:
            diff = abs(ext_weekly["ds"] - ds)
            idx  = diff.idxmin()
            if diff[idx].days <= 4:
                row = {"ds": ds}
                for col in ext_weekly.columns:
                    if col != "ds":
                        row[col] = ext_weekly.at[idx, col]
                result_rows.append(row)
            else:
                result_rows.append({"ds": ds})

        result = pd.DataFrame(result_rows)
        ext_cols = [c for c in result.columns if c != "ds"]
        if not ext_cols:
            return None

        # 결측 → 컬럼별 평균으로 채움
        for col in ext_cols:
            result[col] = pd.to_numeric(result[col], errors="coerce")
            result[col].fillna(result[col].mean(), inplace=True)

        # 실제 데이터 있는 컬럼만 반환 (전부 NaN이면 제외)
        valid_cols = ["ds"] + [c for c in ext_cols if result[c].notna().any()]
        return result[valid_cols] if len(valid_cols) > 1 else None

    except Exception as e:
        logger.warning("[PublicData] ext_dataframe 생성 실패 (%s): %s", category, e)
        return None
