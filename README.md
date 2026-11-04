# 가전무쌍 (Appliance Trend Insight)
## 시연 영상
https://github.com/user-attachments/assets/dbc6fe18-7f63-40eb-988b-6548a2e3a6cf



가전제품 B2B 유통사를 위한 AI 기반 시장 분석 플랫폼입니다.  
제품을 검색해 고르면 검색량 · 가격 · 리뷰 · 공공데이터를 모아 수요 예측과 매입 판단(매입 추천 · 관망)을 한 화면에 보여줍니다.

---

## 배포

| 구분 | URL | 플랫폼 |
|------|-----|--------|
| **서비스 (Frontend)** | https://appliance-trend-insight.vercel.app | Vercel |
| **Backend** | FastAPI (Python 런타임) | Render |
| **DB** | PostgreSQL + pgvector | Neon |

> Render 무료 플랜은 15분 비활동 시 서버가 슬립되며, 첫 요청 시 30~50초 대기가 발생할 수 있습니다.

### Backend 배포 (Render)

Render Web Service · Python 런타임 · Root Directory `backend` · 시작 명령 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
`.env`에 정의된 환경 변수는 Render 대시보드의 Environment에 동일하게 등록합니다.
무료 인스턴스(512MB)라 시작할 때 `mallopt`로 메모리 영역 수를 제한하고 무거운 요청은 동시에 2개까지만 처리합니다.

### Frontend 배포 (Vercel)

`frontend/vercel.json`의 SPA 라우팅 설정을 사용하며, 빌드된 백엔드 URL을 `VITE_API_BASE` 환경 변수로 주입합니다.

```env
# frontend/.env.production
VITE_API_BASE=https://your-backend-name.onrender.com
```

---

## 주요 기능

### B2B 제품 시장 분석 (`/b2b`)
제품명을 검색해 목록에서 정확한 상품 하나를 고르면 아래 카드를 한 화면에 보여줍니다.

| 카드 | 내용 | 데이터 |
|---|---|---|
| AI 종합 리포트 | 가격 · 수요 · 리뷰를 종합한 매입 판단(매입 추천 · 관망 권장 · 매입 추천하지 않음) | Groq gpt-oss-120b → Cerebras 폴백 |
| 검색량 추이 · 예측 | 주별 검색량과 22주 예측 · 신뢰구간 | 네이버 DataLab 4년치 |
| 날씨와 검색량 | 기온 · 습도 · 초미세먼지와 검색량을 겹쳐 그리고 상관계수와 "기온 1°C 오를 때 검색량 몇 %"를 설명 | 기상청 ASOS · 에어코리아 |
| 안전사고 접수 TOP 3 | 품목별로 많이 접수된 사고 원인 · 증상 | 한국소비자원 위해정보 |
| 가격 변동 · 적정성 | 실제 가격 이력과 역대 평균 대비 현재가 (튀는 가격은 자동 제외) | 다나와 이력 + 매일 자체 수집 |
| 경쟁 제품 비교 | 비슷한 가격대 다른 브랜드 제품과 장단점 비교 | 네이버 쇼핑 · 리뷰 |
| 리뷰 감성 분석 | 블로그 · 카페 후기 긍정 · 부정 요약 | 네이버 검색 |

상품 목록에는 에너지 효율 등급과 **한 달 전기료**(에너지공단 월간 소비전력량 × 한전 주택용 요금)를 함께 보여줍니다.

### 수요 예측 — 품목마다 맞는 모델을 백테스트로 자동 선택
- 후보: Holt-Winters · 최근값 유지 · 최근 4주 평균 · '최근 수준 + 작년 같은 시기 변화'를 30~100% 반영하는 방식
- 품목마다 과거 4개 시점에서 8주를 가리고 맞혀본 오차(MAPE)가 가장 작은 모델을 쓰고 매일 새벽 다시 고릅니다
  (예: 에어컨 · 제습기는 계절 반영형 · 세탁기 · TV는 최근값 유지)
- Holt-Winters는 순수 파이썬으로 구현 — 처음엔 Prophet을 썼으나 Render 무료 인스턴스(512MB)에서 메모리 초과로 서버가 재시작되어 교체
- 날씨를 1주 앞 예측에 넣으면 오차가 줄어드는지 비교하는 관리자 백테스트(`/api/b2b/backtest-weather`)도 있습니다

### 소비자(B2C) 기능
- 제품 목록 · 비교 · 추천 · 구매 타이밍 · 트렌드 TOP10 · 제품 리포트
- AI 상담 채팅: 실제 가격 이력으로 답변 · 리포트는 RAG(pgvector) 문서를 함께 참고

### 지원 카테고리
에어컨 · 냉장고 · 세탁기 · 건조기 · TV · 선풍기 · 공기청정기 · 제습기 · 가습기 · 로봇청소기 · 식기세척기 · 에어프라이어 · 전기밥솥

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 18, Vite, React Router |
| Backend | FastAPI, Python 3.11 |
| DB / 캐시 | PostgreSQL + pgvector (Neon) |
| AI / LLM | Groq (openai/gpt-oss-120b → openai/gpt-oss-20b), Cerebras (gpt-oss-120b) |
| 임베딩 | HuggingFace Inference API (sentence-transformers/all-MiniLM-L6-v2, 384차원) |
| 예측 모델 | Holt-Winters · 계절 반영형 등 후보 중 품목별 백테스트로 선택 (순수 파이썬) |
| 외부 데이터 | 네이버 DataLab · 쇼핑 · 검색, 다나와, 기상청 ASOS, 에어코리아, 한국소비자원, 에너지공단 KEMCO |
| 배포 · 자동화 | Render (Backend), Vercel (Frontend), GitHub Actions (매일 새벽 수집) |

---

## 프로젝트 구조

```
├── .github/workflows/daily-collect.yml   # 매일 03:23 KST 서버를 깨우고 수집이 끝날 때까지 유지
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── b2b_search_analysis.py  # B2B 제품 시장 분석 · 모델 자동 선택 · 관리자 백테스트
│   │   │   ├── b2b_price.py / b2b_product.py  # 가격 모니터링 · 리포트 내보내기
│   │   │   ├── analysis.py / insights.py / naver.py  # B2C 분석 · 트렌드 · 상품 검색
│   │   │   ├── admin.py / auth.py / user.py / payments.py
│   │   ├── services/
│   │   │   ├── forecast_models.py   # 예측 후보 모델 · 백테스트 · 날씨 백테스트
│   │   │   ├── public_data.py       # 공공데이터 수집 + 하루 1회 갱신
│   │   │   ├── public_insights.py   # 날씨 상관 · 안전사고 TOP 3 · 월 전기료 계산
│   │   │   ├── price_service.py     # 매일 가격 수집 (메모리 300MB 넘으면 중단)
│   │   │   ├── danawa_search.py / tracking.py / naver_cache.py
│   │   ├── rag_service.py           # pgvector RAG
│   │   └── main.py
│   └── scripts/
│       ├── refresh_ext_data.py      # 공공데이터 수동 수집 (선택)
│       └── seed_rag_local.py        # RAG 문서 로컬 시딩
└── frontend/src/pages/
    ├── B2BAnalysis.jsx              # B2B 제품 시장 분석
    ├── B2BHome.jsx / B2BPricing.jsx
    ├── Home.jsx / ProductList.jsx / Compare.jsx / Recommend.jsx / Timing.jsx / Trend.jsx / ProductReport.jsx / Chat.jsx
    └── Admin.jsx / MyPage.jsx / Login.jsx …
```

---

## 환경 변수 설정

### Backend (.env)

```env
# 네이버 API
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=

# YouTube
YOUTUBE_API_KEY=

# LLM
GROQ_API_KEY=
CEREBRAS_API_KEY=

# PostgreSQL (Neon)
DB_HOST=
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=
DB_NAME=postgres
DATABASE_URL=

# 공공데이터 (data.go.kr 통합 키)
# 필요 서비스: 기상청 ASOS / 에어코리아 / 에너지공단 효율등급 / 소비자원 위해정보
PUBLIC_DATA_API_KEY=

# 통계청 KOSIS (kosis.kr)
KOSIS_API_KEY=

# HuggingFace (RAG 임베딩 — sentence-transformers/all-MiniLM-L6-v2)
HUGGINGFACE_API_KEY=

# RAG 활성화 여부
ENABLE_RAG=true

# JWT
JWT_SECRET=

# 이메일 (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
```

---

## 로컬 실행

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

> **데이터 수집**: 별도 스크립트 없이 서버가 매일 자동으로 수집합니다. 수집 대상 · 기간 · 주기는 아래 [데이터 수집](#데이터-수집-기간--주기)을 참고하세요.

---

## 데이터 수집 (기간 · 주기)

### 수집 기간

| 데이터 | 출처 | 수집 기간 | 쓰이는 곳 |
|---|---|---|---|
| 검색량 추이 (주간) | 네이버 데이터랩 검색어 트렌드 | 최근 **4년** (주 단위 · 52주 계절성 학습) | B2B 수요 예측 — Holt-Winters로 **22주** 예측 |
| 쇼핑 클릭 추이 (월간) | 네이버 데이터랩 쇼핑인사이트 | 최근 **730일** (월 단위) | B2B 판매 예측 — Holt-Winters로 **8개월** 예측 |
| 검색량 추이 (일간) | 네이버 데이터랩 검색어 트렌드 | 최근 **30일** (일 단위) | 트렌드 TOP10 · 제품 리포트 · 구매 타이밍 관심도 |
| 제품 가격 이력 | 다나와 가격 이력 + 매일 자체 수집 | 다나와 최대 **24개월** / 화면은 최근 **30일** | 구매 타이밍 · 출시가 대비 할인율 |
| 카테고리 가격 통계 | 다나와 검색 (매일 자체 수집) | 수집 시작일부터 누적 | B2B 시장 분석 · 매입 적기 알림 |
| 기온 · 습도 | 기상청 ASOS | 최근 **730일** | 날씨와 검색량 카드 (에어컨 · 선풍기 · 제습기 · 가습기) |
| 미세먼지 PM2.5 · PM10 | 에어코리아 | 최근 **90일** | 미세먼지와 검색량 카드 (공기청정기) |
| 소비자물가지수 | 통계청 KOSIS | 최근 **24개월** | 수집만 (화면에는 아직 안 씀) |
| 위해 피해 접수 | 한국소비자원 | 최근 최대 3,000건을 품목 12개로 나눔 | 안전사고 접수 TOP 3 |
| 에너지효율 등급 | 한국에너지공단 | 카테고리 7개 모델별 등급 · 월간 소비전력량 | 효율 등급 · 한 달 전기료 |

### 수집 주기

| 주기 | 무엇을 | 방식 |
|---|---|---|
| **매일 1회** (새벽 3:23 KST) | 카테고리 24개 가격 통계 + 관련도 상위 5개 + **출시가 가장 최근인 3개** 가격 / 추적 제품(최근 7일 안에 조회됐거나 최신 제품 · 최대 150개) 가격 / 데이터랩 일간 검색량 / 매입 적기 알림 메일 | GitHub Actions가 서버를 깨우고 수집이 끝날 때까지 유지 (`.github/workflows/daily-collect.yml`) |
| **매일 1회** (가격 수집 2분 뒤) | 기상청 · 에어코리아 · KOSIS · 소비자원 · 에너지공단 | 서버 백그라운드 작업 |
| **볼 때마다** | 제품 목록 · 검색 · 비교 (다나와 실시간, 같은 검색어 30분 캐시) / 트렌드 TOP10 (30분 캐시) / 구매 타이밍 현재가 / 제품 리포트 · B2B 분석의 뉴스 · 유튜브 · 리뷰 | 요청 시 수집 |

- 20시간 안에 이미 수집했으면 다시 돌지 않습니다 (서버가 하루에 여러 번 깨어나도 1회)
- Render 무료 서버(512MB) 보호: 수집 중 메모리가 300MB를 넘으면 멈추고 다음 기동 때 다시 수집
- 실사용자가 없어도 카테고리별 최신 제품 가격 이력이 매일 쌓입니다

---

## 공공데이터 활용 상세

`backend/app/services/public_insights.py`

### 1. 날씨 · 미세먼지와 검색량
- 일별 날씨를 검색량 주(週)에 맞춰 주 평균으로 묶고 최근 104주의 상관계수와 회귀 기울기를 계산합니다
- 제품 라인 검색량은 신제품 · 광고로 튀어서 날씨와 관계가 흐려지므로 **품목('에어컨') 검색량** 기준으로 계산합니다
- 지난주 날씨를 작년 같은 주와 비교해 다음 수요를 짐작할 근거로 보여줍니다

| 품목 | 비교 변수 |
|---|---|
| 에어컨 · 선풍기 | 기온 |
| 제습기 · 가습기 | 습도 |
| 공기청정기 | 초미세먼지(PM2.5) |

### 2. 안전사고 접수 TOP 3
- 소비자원 위해정보를 한 번에 여러 페이지 받아 품목별로 나눕니다
- 원인 → 증상 → 다친 부위 순으로 '해당없음' 같은 값을 뺀 의미 있는 값이 3건 이상인 항목을 씁니다 (없으면 카드를 숨김)

### 3. 한 달 전기료
- 에너지공단 모델별 자료에서 월간 소비전력량(kWh)을 읽어 한전 주택용 2단계 요금(kWh당 214.6원)을 곱합니다 · 기본요금과 세금 제외
- 제습기는 에너지공단이 주는 월간 에너지비용을 그대로 씁니다
- 정부 API가 느려서 사용자 요청 중이 아니라 새벽 수집 때 미리 받아둡니다

---

## pgvector 활용

### 테이블 구조

| 테이블 | 용도 |
|--------|------|
| `rag_documents` | 소비자 후기·뉴스 임베딩 벡터 저장 (pgvector) |
| `naver_cache` | 네이버 DataLab·공공데이터·AI리포트 캐시 (JSONB) |

### RAG 파이프라인

`backend/app/rag_service.py`

```
네이버 뉴스·블로그 수집
        ↓
HuggingFace API (sentence-transformers/all-MiniLM-L6-v2) 로 텍스트 임베딩 (384차원)
        ↓
rag_documents 테이블에 pgvector 형식으로 저장
        ↓
AI 리포트·수요예측 생성 시 코사인 유사도 검색 (<=> 연산자)
        ↓
상위 N개 청크를 LLM 프롬프트 컨텍스트로 주입
```

### 캐시 레이어 (naver_cache)

| 캐시 키 패턴 | 내용 | TTL |
|---|---|---|
| `ext:kma:history` | 기상청 기온·습도 2년치 | 30시간 |
| `ext:airkorea:history` | 에어코리아 PM2.5·PM10 | 30시간 |
| `ext:kosis:cpi` | 통계청 소비자물가지수 24개월치 | 30일 |
| `ext:kca:{category}` | 소비자원 위해 접수 (원인 · 증상) | 7일 |
| `ext:kemco:{category}` | 에너지공단 1등급 비율 | 30일 |
| `kemco_model_grades:v2:{category}` | 모델별 등급 · 월간 소비전력량 | 7일 |
| `forecast_model_choice:v1` | 품목별 백테스트로 고른 예측 모델 | 8일 |

---

## 공공데이터 API 출처

| 데이터 | 제공기관 | 신청처 |
|--------|----------|--------|
| 기온·습도 (ASOS 일자료) | 기상청 | data.go.kr |
| PM2.5·PM10 (실시간) | 한국환경공단 에어코리아 | data.go.kr |
| 소비자 피해 접수 | 한국소비자원 | data.go.kr |
| 에너지소비효율 등급 | 한국에너지공단 KEMCO | data.go.kr |
| 소비자물가지수 (2020=100) | 통계청 | kosis.kr |
