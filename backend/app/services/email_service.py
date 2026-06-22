import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _smtp_config():
    return {
        "user": os.getenv("SMTP_USER") or os.getenv("SMTP_EMAIL"),
        "password": os.getenv("SMTP_PASSWORD"),
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
    }


def _send_smtp(cfg: dict, to_email: str, msg: MIMEMultipart):
    if cfg["port"] == 465:
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"]) as s:
            s.login(cfg["user"], cfg["password"])
            s.sendmail(cfg["user"], to_email, msg.as_string())
    else:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as s:
            s.ehlo()
            s.starttls()
            s.login(cfg["user"], cfg["password"])
            s.sendmail(cfg["user"], to_email, msg.as_string())


def send_verification_email(to_email: str, code: str):
    cfg = _smtp_config()
    if not cfg["user"] or not cfg["password"]:
        print(f"\n[DEV] 인증코드 → {to_email} : {code}\n")
        return

    msg = MIMEMultipart()
    msg["From"] = cfg["user"]
    msg["To"] = to_email
    msg["Subject"] = "[가전무쌍] 이메일 인증코드"

    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0f0f18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f18;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
        style="background:#1a1a2e;border-radius:20px;border:1px solid rgba(99,102,241,0.25);overflow:hidden;max-width:480px;width:100%;">

        <tr><td style="background:linear-gradient(135deg,#6366f1,#a855f7);padding:32px 40px;text-align:center;">
          <div style="display:inline-flex;align-items:center;gap:10px;">
            <div style="width:32px;height:32px;background:rgba(255,255,255,0.2);border-radius:8px;
              display:inline-flex;align-items:center;justify-content:center;
              font-size:14px;font-weight:900;color:white;">A</div>
            <span style="font-size:20px;font-weight:800;color:white;letter-spacing:-0.5px;">가전무쌍</span>
          </div>
        </td></tr>

        <tr><td style="padding:40px 40px 32px;">
          <p style="margin:0 0 8px;font-size:22px;font-weight:800;color:white;letter-spacing:-0.5px;">
            이메일 인증코드
          </p>
          <p style="margin:0 0 32px;font-size:14px;color:#a0a0b8;line-height:1.6;">
            아래 인증코드를 입력해 이메일을 인증하세요.<br>코드는 <strong style="color:#c4b5fd;">10분간</strong> 유효합니다.
          </p>

          <div style="background:rgba(99,102,241,0.1);border:1.5px solid rgba(99,102,241,0.35);
            border-radius:16px;padding:28px;text-align:center;margin-bottom:32px;">
            <div style="display:flex;justify-content:center;gap:8px;">
              {"".join(f'<span style="display:inline-block;width:44px;height:52px;line-height:52px;background:rgba(255,255,255,0.07);border-radius:10px;font-size:24px;font-weight:800;color:white;text-align:center;">{c}</span>' for c in code)}
            </div>
          </div>

          <p style="margin:0;font-size:12px;color:#6b6b80;line-height:1.6;">
            본인이 요청하지 않은 경우 이 이메일을 무시하세요.<br>
            계정 보안을 위해 인증코드를 타인과 공유하지 마세요.
          </p>
        </td></tr>

        <tr><td style="padding:20px 40px 28px;border-top:1px solid rgba(255,255,255,0.06);">
          <p style="margin:0;font-size:11px;color:#4a4a60;text-align:center;">
            © 2025 가전무쌍 · 국내 가전 트렌드 인사이트
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    msg.attach(MIMEText(html, "html", "utf-8"))
    _send_smtp(cfg, to_email, msg)


def send_rejection_email(to_email: str, company_name: str):
    cfg = _smtp_config()
    if not cfg["user"] or not cfg["password"]:
        print(f"\n[DEV] 거절 이메일 → {to_email} ({company_name})\n")
        return

    msg = MIMEMultipart()
    msg["From"] = cfg["user"]
    msg["To"] = to_email
    msg["Subject"] = "[가전무쌍] 사업자 계정 가입 심사 결과 안내"
    display = company_name or "귀사"

    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0f0f18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f18;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
        style="background:#1a1a2e;border-radius:20px;border:1px solid rgba(239,68,68,0.25);overflow:hidden;max-width:480px;width:100%;">

        <tr><td style="background:linear-gradient(135deg,#ef4444,#dc2626);padding:32px 40px;text-align:center;">
          <div style="display:inline-flex;align-items:center;gap:10px;">
            <div style="width:32px;height:32px;background:rgba(255,255,255,0.2);border-radius:8px;
              display:inline-flex;align-items:center;justify-content:center;
              font-size:14px;font-weight:900;color:white;">A</div>
            <span style="font-size:20px;font-weight:800;color:white;letter-spacing:-0.5px;">가전무쌍</span>
          </div>
          <p style="margin:16px 0 0;font-size:14px;color:rgba(255,255,255,0.8);">사업자 계정 심사 결과</p>
        </td></tr>

        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:22px;font-weight:800;color:white;">심사 결과 안내</p>
          <p style="margin:0 0 24px;font-size:14px;color:#9ca3af;line-height:1.7;">
            <strong style="color:#e5e7eb;">{display}</strong> 사업자 계정 가입 신청을 검토한 결과,<br>
            아쉽게도 이번 심사에서 승인이 어렵게 되었습니다.
          </p>

          <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);border-radius:14px;padding:20px 24px;margin-bottom:24px;">
            <p style="margin:0;font-size:13px;color:#fca5a5;line-height:1.7;">
              📋 가입 심사 기준에 부합하지 않아 승인이 거절되었습니다.<br>
              문의사항이 있으시면 관리자에게 직접 연락해 주세요.
            </p>
          </div>

          <p style="margin:0;font-size:12px;color:#4a4a60;line-height:1.6;">
            개인(B2C) 계정으로는 언제든지 가입하실 수 있습니다.<br>
            가전무쌍을 이용해 주셔서 감사합니다.
          </p>
        </td></tr>

        <tr><td style="padding:20px 40px 28px;border-top:1px solid rgba(255,255,255,0.06);">
          <p style="margin:0;font-size:11px;color:#4a4a60;text-align:center;">
            © 2025 가전무쌍 · 국내 가전 트렌드 인사이트
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    msg.attach(MIMEText(html, "html", "utf-8"))
    _send_smtp(cfg, to_email, msg)


def send_approval_email(to_email: str, company_name: str):
    cfg = _smtp_config()
    if not cfg["user"] or not cfg["password"]:
        print(f"\n[DEV] 승인 이메일 → {to_email} ({company_name})\n")
        return

    msg = MIMEMultipart()
    msg["From"] = cfg["user"]
    msg["To"] = to_email
    msg["Subject"] = "[가전무쌍] 사업자 계정이 승인되었습니다 🎉"
    display = company_name or "귀사"

    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0f0f18;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f18;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
        style="background:#1a1a2e;border-radius:20px;border:1px solid rgba(99,102,241,0.25);overflow:hidden;max-width:480px;width:100%;">

        <tr><td style="background:linear-gradient(135deg,#6366f1,#a855f7);padding:32px 40px;text-align:center;">
          <div style="display:inline-flex;align-items:center;gap:10px;">
            <div style="width:32px;height:32px;background:rgba(255,255,255,0.2);border-radius:8px;
              display:inline-flex;align-items:center;justify-content:center;
              font-size:14px;font-weight:900;color:white;">A</div>
            <span style="font-size:20px;font-weight:800;color:white;letter-spacing:-0.5px;">가전무쌍</span>
          </div>
          <p style="margin:16px 0 0;font-size:14px;color:rgba(255,255,255,0.8);">사업자 계정 승인 완료</p>
        </td></tr>

        <tr><td style="padding:36px 40px;">
          <p style="margin:0 0 8px;font-size:22px;font-weight:800;color:white;">🎉 승인되었습니다!</p>
          <p style="margin:0 0 24px;font-size:14px;color:#9ca3af;line-height:1.7;">
            <strong style="color:#e5e7eb;">{display}</strong> 사업자 계정이 승인되었습니다.<br>
            이제 가전무쌍의 모든 B2B 기능을 이용하실 수 있습니다.
          </p>

          <div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);border-radius:14px;padding:20px 24px;margin-bottom:24px;">
            <p style="margin:0;font-size:13px;color:#c4b5fd;line-height:1.8;">
              ✅ 가전 트렌드 AI 리포트 이용 가능<br>
              ✅ 제품 비교 분석 이용 가능<br>
              ✅ AI 추천 서비스 이용 가능
            </p>
          </div>

          <p style="margin:0;font-size:12px;color:#4a4a60;line-height:1.6;">
            지금 바로 로그인하여 서비스를 이용해보세요.
          </p>
        </td></tr>

        <tr><td style="padding:20px 40px 28px;border-top:1px solid rgba(255,255,255,0.06);">
          <p style="margin:0;font-size:11px;color:#4a4a60;text-align:center;">
            © 2025 가전무쌍 · 국내 가전 트렌드 인사이트
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    msg.attach(MIMEText(html, "html", "utf-8"))
    _send_smtp(cfg, to_email, msg)
