import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_admin
from app.services.email_service import send_approval_email, send_rejection_email

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/pending-users")
async def admin_pending_users(_: dict = Depends(require_admin)):
    from app.database import fetchall
    rows = await fetchall(
        """
        SELECT u.user_id, u.email, u.status, u.created_at,
               p.company_name, p.business_type, p.contact_phone
        FROM users u
        LEFT JOIN user_b2b_profiles p ON p.user_id = u.user_id
        WHERE u.user_type = 'b2b' AND u.status = 'pending'
        ORDER BY u.created_at DESC
        """,
    )
    return {"users": [dict(r) for r in rows]}


@router.get("/b2b-users")
async def admin_all_b2b(status: str = "all", _: dict = Depends(require_admin)):
    from app.database import fetchall
    valid_statuses = ("pending", "active", "rejected")
    if status in valid_statuses:
        rows = await fetchall(
            """
            SELECT u.user_id, u.email, u.status, u.created_at,
                   p.company_name, p.business_type, p.contact_phone
            FROM users u
            LEFT JOIN user_b2b_profiles p ON p.user_id = u.user_id
            WHERE u.user_type = 'b2b' AND u.status = %s
            ORDER BY
              FIELD(u.status, 'pending', 'active', 'rejected'),
              u.created_at DESC
            """,
            (status,),
        )
    else:
        rows = await fetchall(
            """
            SELECT u.user_id, u.email, u.status, u.created_at,
                   p.company_name, p.business_type, p.contact_phone
            FROM users u
            LEFT JOIN user_b2b_profiles p ON p.user_id = u.user_id
            WHERE u.user_type = 'b2b'
            ORDER BY
              FIELD(u.status, 'pending', 'active', 'rejected'),
              u.created_at DESC
            """,
        )
    result = [dict(r) for r in rows]
    counts = {"pending": 0, "active": 0, "rejected": 0, "total": len(result)}
    for r in result:
        s = r.get("status", "")
        if s in counts:
            counts[s] += 1
    return {"users": result, "counts": counts}


@router.post("/users/{user_id}/approve")
async def admin_approve_user(user_id: int, _: dict = Depends(require_admin)):
    from app.database import execute, fetchone
    user = await fetchone("SELECT user_id FROM users WHERE user_id = %s AND user_type = 'b2b'", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    user_row    = await fetchone("SELECT email FROM users WHERE user_id = %s", (user_id,))
    company_row = await fetchone("SELECT company_name FROM user_b2b_profiles WHERE user_id = %s", (user_id,))
    await execute("UPDATE users SET status = 'active' WHERE user_id = %s", (user_id,))
    if user_row:
        await asyncio.to_thread(
            send_approval_email,
            user_row["email"],
            company_row["company_name"] if company_row else "",
        )
    return {"message": "승인 완료"}


@router.post("/users/{user_id}/reject")
async def admin_reject_user(user_id: int, _: dict = Depends(require_admin)):
    from app.database import execute, fetchone
    user = await fetchone("SELECT user_id FROM users WHERE user_id = %s AND user_type = 'b2b'", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    user_row    = await fetchone("SELECT email FROM users WHERE user_id = %s", (user_id,))
    company_row = await fetchone("SELECT company_name FROM user_b2b_profiles WHERE user_id = %s", (user_id,))
    await execute("UPDATE users SET status = 'rejected' WHERE user_id = %s", (user_id,))
    if user_row:
        await asyncio.to_thread(
            send_rejection_email,
            user_row["email"],
            company_row["company_name"] if company_row else "",
        )
    return {"message": "거절 완료"}
