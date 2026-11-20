import html
import re


def strip_html(text: str) -> str:
    """네이버 API가 섞어 보내는 <b> 태그를 지우고 &quot; &amp; 같은 특수문자를 원래 글자로 바꾼다."""
    return html.unescape(re.sub(r"<[^>]+>", "", text or ""))


def extract_model_number(title: str) -> str | None:
    patterns = [
        r'\b([A-Z]{2,}[0-9]{3,}[A-Z0-9]*)\b',
        r'\b([A-Z]{2,}-[A-Z0-9]{3,}[A-Z0-9\-]*)\b',
        r'\b([0-9]{2,}[A-Z]{2,}[0-9A-Z]{3,})\b',
    ]
    for pat in patterns:
        m = re.search(pat, title)
        if m and len(m.group(1)) >= 6:
            return m.group(1)
    return None


def fmt_price_label(won: int) -> str:
    if won >= 10000:
        return f"{won // 10000}만"
    return str(won)
