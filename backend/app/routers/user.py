from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user

router = APIRouter(prefix="/api/user", tags=["user"])


class AlertCreate(BaseModel):
    product_name: str
    target_price: float
    current_price: float
    product_url: str = ""
    alert_type: str = "below"


@router.get("/me")
async def get_my_profile(payload: dict = Depends(get_current_user)):
    from app.database import fetchone
    user_id = int(payload["sub"])
    user = await fetchone(
        "SELECT user_id, email, user_type, role, status, created_at FROM users WHERE user_id = %s",
        (user_id,),
    )
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    profile = {}
    if user["user_type"] == "b2c":
        row = await fetchone("SELECT nickname FROM user_b2c_profiles WHERE user_id = %s", (user_id,))
        profile = {"nickname": row["nickname"] if row else ""}
    else:
        row = await fetchone(
            "SELECT company_name, business_type, contact_phone FROM user_b2b_profiles WHERE user_id = %s",
            (user_id,),
        )
        if row:
            profile = {
                "company_name":  row["company_name"],
                "business_type": row["business_type"],
                "contact_phone": row["contact_phone"],
            }

    return {
        "user_id":    user["user_id"],
        "email":      user["email"],
        "user_type":  user["user_type"],
        "role":       user.get("role", "user"),
        "status":     user.get("status", "active"),
        "created_at": str(user["created_at"]) if user.get("created_at") else None,
        **profile,
    }


@router.get("/alerts")
async def get_my_alerts(payload: dict = Depends(get_current_user)):
    from app.database import get_user_alerts
    user_id = int(payload["sub"])
    rows = await get_user_alerts(user_id)
    return {"alerts": [dict(r) for r in rows]}


@router.post("/alerts")
async def create_my_alert(body: AlertCreate, payload: dict = Depends(get_current_user)):
    from app.database import create_alert, fetchall
    user_id = int(payload["sub"])
    existing = await fetchall(
        "SELECT alert_id FROM price_alert WHERE user_id=%s AND product_name=%s AND is_active=TRUE",
        (user_id, body.product_name),
    )
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 알림입니다")
    alert_id = await create_alert(
        user_id, body.product_name, body.target_price,
        body.current_price, body.product_url, body.alert_type,
    )
    return {"alert_id": alert_id, "message": "알림이 등록됐습니다"}


@router.delete("/alerts/{alert_id}")
async def delete_my_alert(alert_id: int, payload: dict = Depends(get_current_user)):
    from app.database import execute, fetchone
    user_id = int(payload["sub"])
    row = await fetchone(
        "SELECT alert_id FROM price_alert WHERE alert_id=%s AND user_id=%s",
        (alert_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    await execute("UPDATE price_alert SET is_active=FALSE WHERE alert_id=%s", (alert_id,))
    return {"message": "알림이 삭제됐습니다"}
