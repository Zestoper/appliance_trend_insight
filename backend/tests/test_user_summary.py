"""앱 메뉴 요약 /api/user/summary: 알림 0개 · 한도 꽉 참 · 목표가 도달 · 사업자. 실행: python -m pytest tests/test_user_summary.py"""
import asyncio
import os

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
import app.routers.user as user_router  # noqa: E402
from app.services import price_alerts as pa  # noqa: E402


def run(c):
    return asyncio.run(c)


def install(monkeypatch, user_type="b2c", status="active", tier="free", count=0, reached=0,
            nickname="준영", company="가전마트", email="jun@example.com"):
    seen = []

    async def fetchone(sql, args=None):
        seen.append(sql)
        if "SELECT user_type, email FROM users" in sql:
            return {"user_type": user_type, "email": email}
        if "SELECT user_type, status FROM users" in sql:
            return {"user_type": user_type, "status": status}
        if "SELECT tier, tier_expires_at FROM users" in sql:
            return {"tier": tier, "tier_expires_at": None}
        if "user_b2c_profiles" in sql:
            return {"nickname": nickname}
        if "user_b2b_profiles" in sql:
            return {"company_name": company}
        if "FROM price_alert" in sql:
            assert "is_active = TRUE" in sql and "triggered_at" in sql
            return {"n": count, "reached": reached}
        return None

    monkeypatch.setattr(db, "fetchone", fetchone)
    return seen


def summary():
    return run(user_router.get_my_summary({"sub": "1"}))


def test_알림_0개(monkeypatch):
    install(monkeypatch)
    s = summary()
    assert s["display_name"] == "준영" and s["user_type"] == "b2c"
    assert s["alerts"] == {"count": 0, "limit": pa.PERSONAL_LIMIT}
    assert s["alerts_reached"] == 0 and s["market_alerts_today"] is None
    assert s["tier"] == "free" and s["tier_label"] == "무료"


def test_한도_꽉_참은_등록_한도와_같은_숫자(monkeypatch):
    install(monkeypatch, count=pa.PERSONAL_LIMIT)
    s = summary()
    assert s["alerts"]["count"] == s["alerts"]["limit"] == pa.PERSONAL_LIMIT
    # 등록할 때 쓰는 한도 함수와 같은 값
    assert run(pa.alert_limit(1))[0] == s["alerts"]["limit"]


def test_목표가_도달_1건(monkeypatch):
    install(monkeypatch, count=2, reached=1)
    s = summary()
    assert s["alerts"]["count"] == 2 and s["alerts_reached"] == 1


def test_사업자는_회사_이름과_등급별_한도(monkeypatch):
    install(monkeypatch, user_type="b2b", tier="silver", count=4)
    s = summary()
    assert s["display_name"] == "가전마트" and s["user_type"] == "b2b"
    assert s["alerts"] == {"count": 4, "limit": pa.TIER_LIMITS["silver"]}
    assert s["tier_label"] == "실버"


def test_승인_대기_사업자는_개인_한도(monkeypatch):
    install(monkeypatch, user_type="b2b", status="pending", tier="gold")
    assert summary()["alerts"]["limit"] == pa.PERSONAL_LIMIT


def test_이름이_없으면_이메일_앞부분(monkeypatch):
    install(monkeypatch, nickname="")
    assert summary()["display_name"] == "jun"


def test_외부_API를_부르지_않음(monkeypatch):
    seen = install(monkeypatch)
    summary()
    assert all("danawa" not in s.lower() for s in seen)
