"""가격 알림: 등록 규칙 · 개수 제한 · 매일 확인 푸시 판단. 실행: python -m pytest tests/test_price_alerts.py"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test")

import app.database as db  # noqa: E402
from app.services import price_alerts as pa  # noqa: E402

NOW = datetime(2026, 11, 22, tzinfo=timezone.utc)


def run(c):
    return asyncio.run(c)


class FakeDB:
    """create_alert · list_alerts · _evaluate가 쓰는 쿼리만 흉내 낸다."""

    def __init__(self, user_type="b2c", status="active", tier="free", active_count=0, dup=False):
        self.user = {"user_type": user_type, "status": status}
        self.tier = tier
        self.active_count = active_count
        self.dup = dup
        self.updates = []
        self.inserted = None

    def install(self, monkeypatch):
        async def fetchone(sql, args=None):
            if "FROM users" in sql:
                return self.user
            if "COUNT(*)" in sql:
                return {"n": self.active_count}
            if "SELECT alert_id FROM price_alert" in sql:
                return {"alert_id": 1} if self.dup else None
            return None

        async def fetchall(sql, args=None):
            if "product_signal_state" in sql:
                return [{"product_key": "RS84DB5002CW", "category": "냉장고", "image": "img", "min_price": 1500000,
                         "hist_avg_price": 1700000, "vs_hist_pct": -11.8, "signal_type": "buy", "demand_slope": 0.5,
                         "history": '[{"date": "2026-11-21", "min_price": 1500000}]', "updated_at": NOW}]
            if "FROM price_alert" in sql:
                return [{"alert_id": 9, "user_id": 7, "product_name": "삼성 냉장고 RS84DB5002CW",
                         "product_key": "RS84DB5002CW", "target_price": None, "is_active": True,
                         "last_signal_type": "buy", "last_notified_price": None, "signal_notified_at": None}]
            return []

        async def execute(sql, args=None):
            self.updates.append((sql, args))
            return 1

        async def returning(sql, args=None):
            self.inserted = args
            return 9

        async def tier(uid):
            return self.tier

        monkeypatch.setattr(db, "fetchone", fetchone)
        monkeypatch.setattr(db, "fetchall", fetchall)
        monkeypatch.setattr(db, "execute", execute)
        monkeypatch.setattr(db, "_execute_returning", returning)
        monkeypatch.setattr(db, "get_user_tier", tier)
        return self


def test_personal_needs_target(monkeypatch):
    FakeDB("b2c").install(monkeypatch)
    with pytest.raises(HTTPException) as e:
        run(pa.create_alert(7, "삼성 냉장고 RS84DB5002CW", None, 0, "", "below"))
    assert e.value.status_code == 400


def test_pending_business_is_personal(monkeypatch):
    FakeDB("b2b", status="pending").install(monkeypatch)
    with pytest.raises(HTTPException) as e:
        run(pa.create_alert(7, "삼성 냉장고 RS84DB5002CW", None, 0, "", "below"))
    assert e.value.status_code == 400


def test_business_needs_target_too(monkeypatch):
    FakeDB("b2b").install(monkeypatch)
    with pytest.raises(HTTPException) as e:
        run(pa.create_alert(7, "삼성 냉장고 RS84DB5002CW", None, 0, "", "below", hint="냉장고"))
    assert e.value.status_code == 400


def test_business_list_fields_without_signal(monkeypatch):
    fake = FakeDB("b2b").install(monkeypatch)
    item = run(pa.create_alert(7, "삼성 냉장고 RS84DB5002CW", 1400000, 0, "", "below", hint="냉장고"))
    assert fake.inserted[6] == "RS84DB5002CW" and fake.inserted[2] == 1400000
    # 매입 신호(매입 추천 · 관망)는 목록에 내려주지 않는다 · 실제 값만
    assert "signal" not in item and "signal_type" not in item
    assert item["min_price"] == 1500000
    assert item["history"] == [{"date": "2026-11-21", "min_price": 1500000}]
    assert "last_signal_type" not in item


def test_personal_list_has_no_signal(monkeypatch):
    FakeDB("b2c").install(monkeypatch)
    item = run(pa.list_alerts(7))[0]
    assert item["min_price"] == 1500000 and "signal_type" not in item


@pytest.mark.parametrize("tier,count,limit,label", [("free", 3, 3, "무료"), ("silver", 10, 10, "실버")])
def test_business_limit_402(monkeypatch, tier, count, limit, label):
    FakeDB("b2b", tier=tier, active_count=count).install(monkeypatch)
    with pytest.raises(HTTPException) as e:
        run(pa.create_alert(7, "LG 세탁기 F24WDWP", 900000, 0, "", "below"))
    assert e.value.status_code == 402
    assert e.value.detail == f"가격 알림은 {label} 등급에서 {limit}개까지 등록할 수 있어요"
    assert "결제" not in e.value.detail and "구독" not in e.value.detail


def test_duplicate_409(monkeypatch):
    FakeDB("b2c", dup=True).install(monkeypatch)
    with pytest.raises(HTTPException) as e:
        run(pa.create_alert(7, "삼성 냉장고 RS84DB5002CW", 1000000, 0, "", "below"))
    assert e.value.status_code == 409


# ── 매일 확인 판단 ──

def row(**kw):
    base = {"alert_id": 9, "user_id": 7, "product_name": "삼성 냉장고", "user_type": "b2c", "status": "active",
            "target_price": None, "last_notified_price": None, "last_signal_type": None, "signal_notified_at": None}
    base.update(kw)
    return base


def block(price, sig="wait", pct=0.0):
    return {"min_price": price, "signal_type": sig, "vs_hist_pct": pct}


def test_target_first_then_only_lower(monkeypatch):
    FakeDB().install(monkeypatch)
    assert run(pa._evaluate(row(target_price=1000000), block(990000), NOW))[0] == "target"
    # 같은 가격이면 다시 안 보냄 · 더 내려가면 보냄
    assert run(pa._evaluate(row(target_price=1000000, last_notified_price=990000), block(990000), NOW)) is None
    assert run(pa._evaluate(row(target_price=1000000, last_notified_price=990000), block(950000), NOW))[0] == "target"


def test_target_rebound_resets(monkeypatch):
    fake = FakeDB().install(monkeypatch)
    assert run(pa._evaluate(row(target_price=1000000, last_notified_price=990000), block(1100000), NOW)) is None
    assert any("last_notified_price = NULL" in s for s, _ in fake.updates)


def test_signal_push_off(monkeypatch):
    FakeDB().install(monkeypatch)
    biz = dict(user_type="b2b")
    # 매입 신호가 buy로 바뀌어도 푸시하지 않는다 (실제 데이터만 보여주기로 해서 끔)
    assert run(pa._evaluate(row(**biz, last_signal_type="wait"), block(900000, "buy", -8.2), NOW)) is None


def test_signal_only_for_active_business(monkeypatch):
    FakeDB().install(monkeypatch)
    assert run(pa._evaluate(row(last_signal_type="wait"), block(900000, "buy"), NOW)) is None
    assert run(pa._evaluate(row(user_type="b2b", status="pending", last_signal_type="wait"),
                            block(900000, "buy"), NOW)) is None


def test_target_and_signal_same_day_one_push(monkeypatch):
    FakeDB().install(monkeypatch)
    push = run(pa._evaluate(row(user_type="b2b", target_price=1000000, last_signal_type="wait"),
                            block(900000, "buy", -8.0), NOW))
    assert push[0] == "target"


def test_new_product_checked_right_after_register(monkeypatch):
    FakeDB("b2c").install(monkeypatch)

    async def no_state(keys):
        return {}
    called = []
    monkeypatch.setattr(pa, "_states", no_state)
    monkeypatch.setattr(pa, "_spawn", lambda coro: (called.append(1), coro.close()))
    run(pa.create_alert(7, "LG전자 스탠바이미2 Max 32LX6BPGA", 979000, 1278780, "", "below"))
    # 처음 보는 제품이면 등록 직후 지금 가격을 한 번 확인한다 (다음 날 새벽까지 '확인하지 못했어요' 방지)
    assert called == [1]
