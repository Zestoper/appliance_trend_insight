#!/usr/bin/env python3
"""
로컬(한국 IP)에서 실행 — Naver 데이터를 Supabase에 캐시합니다.

사용법:
    cd backend
    python -m scripts.refresh_naver_cache

옵션:
    python -m scripts.refresh_naver_cache --categories 에어컨 냉장고
    python -m scripts.refresh_naver_cache --periods 3m 6m
"""
import asyncio
import os
import sys
import argparse
from datetime import date, timedelta
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import httpx

DEFAULT_CATEGORIES = [
    "에어컨", "냉장고", "세탁기", "건조기", "공기청정기",
    "로봇청소기", "식기세척기", "에어프라이어", "TV", "전기밥솥",
    "선풍기", "가습기", "제습기",
]
DEFAULT_PERIODS = ["1m", "3m", "6m", "1y"]


async def fetch_trend(client, category, start_date, end_date, time_unit, dl_headers):
    try:
        body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate":   end_date.strftime("%Y-%m-%d"),
            "timeUnit":  time_unit,
            "keywordGroups": [{"groupName": category, "keywords": [category]}],
        }
        resp = await client.post("https://openapi.naver.com/v1/datalab/search", json=body, headers=dl_headers, timeout=10.0)
        payload = resp.json()
        results = payload.get("results", [])
        return results[0]["data"] if results else []
    except Exception as e:
        print(f"    trend 실패: {e}")
        return []


async def fetch_brand(client, category, naver_headers):
    try:
        resp = await client.get(
            "https://openapi.naver.com/v1/search/shop.json",
            headers=naver_headers,
            params={"query": category, "display": 100, "sort": "sim"},
            timeout=8.0,
        )
        items = resp.json().get("items", [])
        counts = {}
        for it in items:
            key = it.get("maker", "").strip() or it.get("brand", "").strip()
            if key:
                counts[key] = counts.get(key, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
        total = sum(v for _, v in top)
        return [{"brand": k, "count": v, "pct": round(v / total * 100) if total else 0} for k, v in top]
    except Exception as e:
        print(f"    brand 실패: {e}")
        return []


async def fetch_age(client, category, age_codes, start_date, end_date, dl_headers):
    try:
        body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate":   end_date.strftime("%Y-%m-%d"),
            "timeUnit":  "month",
            "keywordGroups": [{"groupName": category, "keywords": [category]}],
            "ages": age_codes,
        }
        resp = await client.post("https://openapi.naver.com/v1/datalab/search", json=body, headers=dl_headers, timeout=10.0)
        payload = resp.json()
        results = payload.get("results", [])
        data = results[0]["data"] if results else []
        return sum(d["ratio"] for d in data) / len(data) if data else 0.0
    except Exception as e:
        print(f"    age 실패: {e}")
        return 0.0


async def fetch_keywords(client, category, naver_headers):
    import re
    try:
        resp = await client.get(
            "https://openapi.naver.com/v1/search/shop.json",
            headers=naver_headers,
            params={"query": category, "display": 30, "sort": "sim"},
            timeout=8.0,
        )
        items = resp.json().get("items", [])
        stop = {"미포함", "포함", "설치비포함", "설치비별도", "방문설치", "무료설치", "무료",
                "별도", "이하", "이상", "할인", "택배", "직접", "기사", "배송", "셀프"}
        counts = {}
        for it in items:
            title = re.sub(r"<[^>]+>", "", it.get("title", ""))
            for tok in re.sub(r"[^가-힣a-zA-Z\s]", " ", title).split():
                if len(tok) >= 2 and tok != category and tok not in stop:
                    if not re.match(r"^[A-Za-z]{1,4}$", tok) and not any(c.isdigit() for c in tok):
                        counts[tok] = counts.get(tok, 0) + 1
        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
        return [{"word": w, "count": c, "examples": []} for w, c in top]
    except Exception as e:
        print(f"    keywords 실패: {e}")
        return []


async def fetch_review_count(client, category, naver_headers):
    try:
        blog_r, cafe_r = await asyncio.gather(
            client.get("https://openapi.naver.com/v1/search/blog.json",
                       headers=naver_headers, params={"query": f"{category} 리뷰", "display": 1}, timeout=6.0),
            client.get("https://openapi.naver.com/v1/search/cafearticle.json",
                       headers=naver_headers, params={"query": f"{category} 리뷰", "display": 1}, timeout=6.0),
        )
        blog_total = blog_r.json().get("total", 0) if blog_r.status_code == 200 else 0
        cafe_total = cafe_r.json().get("total", 0) if cafe_r.status_code == 200 else 0
        return blog_total + cafe_total
    except Exception as e:
        print(f"    review_count 실패: {e}")
        return 0


async def fetch_category_period(category: str, period: str, naver_headers: dict) -> dict:
    days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = days_map.get(period, 90)
    time_unit = "week" if days > 30 else "date"
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    dl_headers = {**naver_headers, "Content-Type": "application/json"}

    age_groups = [["2"], ["3", "4"], ["5", "6"], ["7", "8"], ["9", "10", "11"]]
    age_labels = ["10대", "20대", "30대", "40대", "50대+"]

    async with httpx.AsyncClient() as client:
        trend_data, brand_data, keywords, review_count = await asyncio.gather(
            fetch_trend(client, category, start_date, end_date, time_unit, dl_headers),
            fetch_brand(client, category, naver_headers),
            fetch_keywords(client, category, naver_headers),
            fetch_review_count(client, category, naver_headers),
        )
        age_raw = []
        for g in age_groups:
            await asyncio.sleep(0.3)
            age_raw.append(await fetch_age(client, category, g, start_date, end_date, dl_headers))

    age_total = sum(age_raw)
    age_dist = [
        {"label": lbl, "value": round(v, 1), "pct": round(v / age_total * 100) if age_total else 0}
        for lbl, v in zip(age_labels, age_raw)
    ]

    ratios  = [d["ratio"] for d in trend_data]
    current = round(ratios[-1], 1) if ratios else 0
    avg_val = round(sum(ratios) / len(ratios), 1) if ratios else 0
    half    = len(ratios) // 2
    old_avg = sum(ratios[:half]) / max(half, 1)
    new_avg = sum(ratios[half:]) / max(len(ratios) - half, 1)
    growth  = round((new_avg - old_avg) / max(old_avg, 1) * 100, 1)

    risk = "낮음" if growth > -15 else ("중간" if growth > -30 else "높음")
    summary = f"{category} 시장의 최근 {period} 트렌드 데이터를 분석한 결과입니다."

    return {
        "category": category,
        "period":   period,
        "trend":    trend_data,
        "brands":   brand_data,
        "age_distribution": age_dist,
        "keywords": keywords,
        "complaints": [],
        "complaint_summary": [],
        "youtube_videos": [],
        "news_sources": [],
        "review_mention_count": review_count,
        "market_report": {
            "trend_score": current,
            "avg_score":   avg_val,
            "growth_rate": growth,
            "risk":        risk,
            "summary":     summary,
            "review_mention_count": review_count,
        },
        "_fetched_at": time.time(),
    }


async def main(categories, periods):
    from app.database import get_pool, close_pool
    from app.services.naver_cache import set_db_cache
    from app.config import NAVER_HEADERS

    await get_pool()
    total = len(categories) * len(periods)
    done = 0

    for category in categories:
        for period in periods:
            done += 1
            print(f"[{done}/{total}] {category} / {period} ...", end=" ", flush=True)
            try:
                data = await fetch_category_period(category, period, NAVER_HEADERS)
                await set_db_cache(f"naver_dashboard:{category}:{period}", data, ttl_hours=12)
                print(f"✓ (trend:{len(data['trend'])}개, brand:{len(data['brands'])}개)")
            except Exception as e:
                print(f"✗ {e}")
            await asyncio.sleep(0.5)

    await close_pool()
    print(f"\n완료! {done}개 캐시 저장됨 → Render에서 Naver API 없이 서비스 가능")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naver 데이터 Supabase 캐시 갱신")
    parser.add_argument("--categories", nargs="+", default=DEFAULT_CATEGORIES)
    parser.add_argument("--periods",    nargs="+", default=DEFAULT_PERIODS)
    args = parser.parse_args()
    asyncio.run(main(args.categories, args.periods))
