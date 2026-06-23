import os
from typing import TYPE_CHECKING

from groq import AsyncGroq
from dotenv import load_dotenv as _load_dotenv

if TYPE_CHECKING:
    from app.rag_service import RAGService

_groq_client: AsyncGroq | None = None
_groq_active_key: str | None = None

def _get_groq() -> AsyncGroq:
    global _groq_client, _groq_active_key
    _load_dotenv(override=True)
    current_key = os.getenv("GROQ_API_KEY")
    if _groq_client is None or current_key != _groq_active_key:
        _groq_active_key = current_key
        _groq_client = AsyncGroq(api_key=current_key)
    return _groq_client

_CHUNK_MAX = 150

_B2C_SYSTEM_PROMPT = """\
당신은 가전제품 소비자 구매 참고 리포트 작성 전문가입니다.

[작성 규칙]
0. 질문이 가전제품·생활가전·주방가전·계절가전·영상음향기기와 무관한 경우, 리포트 형식 없이 단 한 문장으로만 응답하세요: "가전제품 관련 질문을 입력해주세요. (예: 로봇청소기 후기, 에어컨 추천)"
1. 아래 참고 문서에 실제로 언급된 내용만 작성하세요.
2. 문서에 없는 내용은 추측하거나 단정하지 마세요. 근거 없는 항목은 생략하거나 "확인된 정보 없음"으로 표기하세요.
3. 각 주장 뒤에 출처 번호를 [1], [2] 형식으로 반드시 표기하세요.
4. 일반 소비자가 이해하기 쉬운 구어체로 작성하세요.
5. 반드시 아래 마크다운 형식으로만 응답하세요. JSON 금지.

[출력 형식]

## 소비자 구매 참고 리포트

### ✅ 주요 장점
- (장점 한 줄 [출처번호])

### ❌ 주요 단점
- (단점 한 줄 [출처번호])

### 💡 이런 분께 추천
(실제 후기 기반 추천 대상 1~2문장)

### ⚠️ 구매 전 확인사항
- (주의사항 [출처번호])

### 📝 한줄 요약
(전체를 한 문장으로 요약)
"""

_B2B_SYSTEM_PROMPT = """\
당신은 가전 시장 B2B 전략 리포트 작성 전문가입니다. 기업 기획자와 MD가 읽는 리포트를 작성합니다.

[작성 규칙]
0. 질문이 가전제품·생활가전·주방가전·계절가전·영상음향기기와 무관한 경우, 리포트 형식 없이 단 한 문장으로만 응답하세요: "가전 시장 관련 질문을 입력해주세요. (예: 에어컨 시장 트렌드, 로봇청소기 소비자 페인포인트)"
1. 아래 참고 문서에 실제로 언급된 내용만 작성하세요.
2. 문서에 없는 내용은 추측하거나 단정하지 마세요. 근거 없는 항목은 생략하거나 "확인된 정보 없음"으로 표기하세요.
3. 각 주장 뒤에 출처 번호를 [1], [2] 형식으로 반드시 표기하세요.
4. 비즈니스 관점의 인사이트와 전략적 시사점을 중심으로 작성하세요.
5. 반드시 아래 마크다운 형식으로만 응답하세요. JSON 금지.

[출력 형식]

## 시장 트렌드 리포트

### 📌 시장 동향 요약
(전체 시장 동향 2~3문장 [출처번호])

### 📈 주요 소비자 트렌드
- (트렌드 한 줄 [출처번호])

### 😤 소비자 페인포인트
- (소비자 불만 한 줄 [출처번호])

### 💼 사업 기회
- (기회 한 줄 [출처번호])

### 🎯 전략적 액션 아이템
1. (구체적 액션)
2. (구체적 액션)

### 👥 타겟 바이어 세그먼트
(주요 타겟 고객 설명)
"""

_EMPTY_REPORT = "RAG 데이터를 준비 중이에요. 잠시 후 다시 시도해주세요.\n\n서버 최초 실행 시 Naver 데이터를 수집하는 데 약 30초가 소요됩니다."


_GROQ_MODEL = "llama-3.3-70b-versatile"


async def analyze(
    query: str,
    rag: "RAGService",
    target: str = "b2b",
    top_k: int = 5,
) -> dict:
    """RAG 검색 결과를 Groq LLM에 전달해 마크다운 트렌드 리포트를 생성한다."""
    rag_query = (
        f"{query} 소비자 트렌드 구매 후기 특징"
        if target == "b2c"
        else f"{query} 시장 트렌드 소비자 반응"
    )
    chunks = await rag.query(rag_query, n_results=top_k) if rag else []

    if not chunks:
        return {
            "query": query,
            "target": target,
            "report": _EMPTY_REPORT,
            "sources": [],
        }

    numbered_chunks = [f"[{i + 1}] {chunk[:_CHUNK_MAX]}" for i, chunk in enumerate(chunks)]
    context = (
        f"[참고 문서 — {query} 관련 {len(chunks)}개]\n"
        + "\n".join(numbered_chunks)
    )
    system_prompt = _B2C_SYSTEM_PROMPT if target == "b2c" else _B2B_SYSTEM_PROMPT

    from groq import RateLimitError
    try:
        res = await _get_groq().chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"제품/카테고리: {query}\n\n{context}"},
            ],
            max_tokens=900,
            temperature=0.3,
        )
    except RateLimitError:
        return {
            "query": query,
            "target": target,
            "report": "AI 분석 요청이 일일 한도에 도달했습니다. 잠시 후 다시 시도해주세요.",
            "sources": [],
        }

    report = res.choices[0].message.content
    sources = [{"rank": i + 1, "text": chunk} for i, chunk in enumerate(chunks)]

    return {
        "query": query,
        "target": target,
        "report": report,
        "sources": sources,
    }
