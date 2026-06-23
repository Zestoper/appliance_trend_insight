import asyncio
import re
import time as _time
from collections import Counter
from datetime import date, timedelta, datetime

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

__all__ = [
    "asyncio", "re", "_time", "Counter", "date", "timedelta", "datetime",
    "logging", "logger", "httpx",
    "APIRouter", "Depends", "HTTPException", "Query",
    "require_b2b",
    "NAVER_HEADERS", "NAVER_SHOP_URL", "NAVER_DATALAB_URL",
    "_CATEGORY_MAP", "_POS_WORDS", "_NEG_WORDS", "_STOP",
    "YOUTUBE_API_KEY", "YOUTUBE_SEARCH_URL",
    "strip_html", "extract_model_number", "fmt_price_label",
    "search_products",
    "_SHOPPING_DISPLAY", "_RAG_CHUNK_LEN", "_CI_MULTIPLIER",
    "_calc_risk",
    "_GROQ_MODELS", "_GROQ_CACHE", "_GROQ_TTL", "_CACHE_VER",
    "_GROQ_MODEL_EXHAUSTED", "_GROQ_DAILY_LIMIT_RESET_SEC",
    "_groq_singleton", "_get_groq_client", "_is_model_exhausted", "_groq_create",
    "_has_non_korean_cjk",
]

from app.auth import require_b2b
from app.config import (
    NAVER_HEADERS, NAVER_SHOP_URL, NAVER_DATALAB_URL,
    _CATEGORY_MAP, _POS_WORDS, _NEG_WORDS, _STOP,
    B2B_SHOPPING_DISPLAY, B2B_RAG_CHUNK_LEN, B2B_CI_MULTIPLIER,
    GROQ_PRIMARY_MODEL, GROQ_FALLBACK_MODEL, GROQ_CACHE_TTL,
    YOUTUBE_API_KEY, YOUTUBE_SEARCH_URL,
)
from app.utils.helpers import strip_html, extract_model_number, fmt_price_label
from app.routers.naver import search_products

logger = logging.getLogger(__name__)

# ── 공통 상수 (config.py에서 가져옴) ──
_SHOPPING_DISPLAY = B2B_SHOPPING_DISPLAY
_RAG_CHUNK_LEN    = B2B_RAG_CHUNK_LEN
_CI_MULTIPLIER    = B2B_CI_MULTIPLIER

def _calc_risk(growth: float) -> str:
    """성장률 기반 시장 위험도 산출 (두 엔드포인트 공통)"""
    return "낮음" if growth > -15 else ("중간" if growth > -30 else "높음")

_GROQ_MODELS = (GROQ_PRIMARY_MODEL, GROQ_FALLBACK_MODEL, "gemma2-9b-it")
_GROQ_CACHE: dict = {}
_GROQ_TTL   = GROQ_CACHE_TTL
_CACHE_VER  = "v8"

# 모델별 일일 한도 소진 시각 (epoch) — 2시간 뒤 자동 재시도
_GROQ_MODEL_EXHAUSTED: dict[str, float] = {}
_GROQ_DAILY_LIMIT_RESET_SEC = 7200  # 2시간

import os as _os
from groq import AsyncGroq as _AsyncGroq
_groq_singleton: _AsyncGroq | None = None

def _get_groq_client() -> _AsyncGroq:
    global _groq_singleton
    if _groq_singleton is None:
        _groq_singleton = _AsyncGroq(api_key=_os.getenv("GROQ_API_KEY"))
    return _groq_singleton

def _is_model_exhausted(model: str) -> bool:
    exhausted_at = _GROQ_MODEL_EXHAUSTED.get(model)
    if exhausted_at is None:
        return False
    if _time.time() - exhausted_at > _GROQ_DAILY_LIMIT_RESET_SEC:
        _GROQ_MODEL_EXHAUSTED.pop(model, None)
        return False
    return True

async def _groq_create(messages: list, max_tokens: int = 600, temperature: float = 0.3):
    """모델별 일일 한도 관리. 모든 모델 소진 시 예외."""
    from groq import RateLimitError
    client = _get_groq_client()
    last_err = None
    for model in _GROQ_MODELS:
        if _is_model_exhausted(model):
            continue
        try:
            return await client.chat.completions.create(
                model=model, messages=messages,
                max_tokens=max_tokens, temperature=temperature,
            )
        except RateLimitError as e:
            err_str = str(e).lower()
            if "tokens per day" in err_str or "tpd" in err_str or "rate_limit" in err_str:
                _GROQ_MODEL_EXHAUSTED[model] = _time.time()
                logger.warning("[Groq] %s 일일 토큰 한도 소진 — 다음 모델 시도", model)
                last_err = e
                continue
            raise
    raise RuntimeError(f"Groq 모든 모델 한도 소진 ({', '.join(_GROQ_MODELS)}). 2시간 후 자동 재시도.") from last_err


def _has_non_korean_cjk(text: str) -> bool:
    """일본어(히라가나·가타카나) 또는 중국어(한자) 포함 여부 반환"""
    for ch in text:
        cp = ord(ch)
        # 히라가나: 3041-3096, 가타카나: 30A1-30F6, 반각가타카나: FF66-FF9F
        # CJK 통합한자: 4E00-9FFF, 확장A: 3400-4DBF
        if (0x3041 <= cp <= 0x3096 or 0x30A1 <= cp <= 0x30F6
                or 0xFF66 <= cp <= 0xFF9F
                or 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF):
            return True
    return False
