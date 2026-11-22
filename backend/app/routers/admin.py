import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_admin
from app.services.email_service import send_approval_email, send_rejection_email
from app.services.push import push_in_background

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
              CASE u.status WHEN 'pending' THEN 1 WHEN 'active' THEN 2 WHEN 'rejected' THEN 3 END,
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
              CASE u.status WHEN 'pending' THEN 1 WHEN 'active' THEN 2 WHEN 'rejected' THEN 3 END,
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


_mail_tasks: set = set()


def _mail_in_background(send, email: str, company: str):
    """승인 · 거절 안내 메일은 뒤에서 보낸다.
    예전에는 메일을 다 보낼 때까지 응답을 기다려서 관리자 화면 버튼이 '처리중…'에 오래 멈췄고,
    메일이 실패하면 상태는 이미 바뀌었는데 화면에는 오류가 떴다."""
    async def run():
        try:
            await asyncio.to_thread(send, email, company)
        except Exception as e:
            print(f"[admin] 안내 메일 실패 {email}: {type(e).__name__}: {e}")
    task = asyncio.create_task(run())
    _mail_tasks.add(task)
    task.add_done_callback(_mail_tasks.discard)


@router.post("/users/{user_id}/approve")
async def admin_approve_user(user_id: int, _: dict = Depends(require_admin)):
    from app.database import execute, fetchone
    user = await fetchone("SELECT user_id FROM users WHERE user_id = %s AND user_type = 'b2b'", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    user_row    = await fetchone("SELECT email FROM users WHERE user_id = %s", (user_id,))
    company_row = await fetchone("SELECT company_name FROM user_b2b_profiles WHERE user_id = %s", (user_id,))
    await execute("UPDATE users SET status = 'active' WHERE user_id = %s", (user_id,))
    push_in_background(user_id, "사업자 승인 완료", "가전무쌍 비즈니스 기능을 이제 이용할 수 있어요.",
                       {"type": "b2b_status", "status": "active"})
    if user_row:
        _mail_in_background(send_approval_email, user_row["email"], company_row["company_name"] if company_row else "")
    return {"message": "승인 완료"}


@router.post("/users/{user_id}/reject")
async def admin_reject_user(user_id: int, admin: dict = Depends(require_admin)):
    from app.database import execute, fetchone
    if str(admin.get("sub") or admin.get("user_id")) == str(user_id):
        raise HTTPException(status_code=400, detail="본인 계정은 승인 취소할 수 없습니다")
    user = await fetchone("SELECT user_id FROM users WHERE user_id = %s AND user_type = 'b2b'", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    user_row    = await fetchone("SELECT email FROM users WHERE user_id = %s", (user_id,))
    company_row = await fetchone("SELECT company_name FROM user_b2b_profiles WHERE user_id = %s", (user_id,))
    await execute("UPDATE users SET status = 'rejected' WHERE user_id = %s", (user_id,))
    push_in_background(user_id, "사업자 승인 결과 안내", "사업자 승인이 거절됐어요. 자세한 내용은 메일을 확인해 주세요.",
                       {"type": "b2b_status", "status": "rejected"})
    if user_row:
        _mail_in_background(send_rejection_email, user_row["email"], company_row["company_name"] if company_row else "")
    return {"message": "거절 완료"}
