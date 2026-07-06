import base64
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_b2b
from app.config import SKIP_PAYMENT_VERIFICATION, TIER_NAMES, TIER_PRICES, TOSS_SECRET_KEY

router = APIRouter(prefix="/api/payments", tags=["payments"])

TOSS_CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"


class OrderRequest(BaseModel):
    tier: str


class ConfirmRequest(BaseModel):
    paymentKey: str
    orderId: str
    amount: int


@router.post("/order")
async def create_order(body: OrderRequest, payload: dict = Depends(require_b2b)):
    if body.tier not in TIER_PRICES:
        raise HTTPException(status_code=400, detail="유효하지 않은 등급입니다")
    from app.database import create_payment_order

    user_id = int(payload["sub"])
    amount = TIER_PRICES[body.tier]
    order_id = f"order_{uuid.uuid4().hex}"
    await create_payment_order(user_id, order_id, body.tier, amount)
    return {
        "orderId":   order_id,
        "amount":    amount,
        "orderName": f"가전무쌍 {TIER_NAMES[body.tier]} 등급 (1개월)",
    }


@router.post("/confirm")
async def confirm_payment(body: ConfirmRequest, payload: dict = Depends(get_current_user)):
    from app.database import get_payment_by_order, mark_payment_paid

    order = await get_payment_by_order(body.orderId)
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다")
    if order["user_id"] != int(payload["sub"]):
        raise HTTPException(status_code=403, detail="본인의 주문만 결제할 수 있습니다")
    if order["status"] == "paid":
        raise HTTPException(status_code=409, detail="이미 처리된 주문입니다")
    if order["amount"] != body.amount:
        raise HTTPException(status_code=400, detail="결제 금액이 일치하지 않습니다")

    if SKIP_PAYMENT_VERIFICATION:
        result = await mark_payment_paid(body.orderId, "dev_bypass")
        return result

    if not TOSS_SECRET_KEY:
        raise HTTPException(status_code=500, detail="결제 서버 설정이 완료되지 않았습니다")

    auth_header = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TOSS_CONFIRM_URL,
            json={"paymentKey": body.paymentKey, "orderId": body.orderId, "amount": body.amount},
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        detail = resp.json().get("message", "결제 승인에 실패했습니다")
        raise HTTPException(status_code=400, detail=detail)

    result = await mark_payment_paid(body.orderId, body.paymentKey)
    return result
