# 가전무쌍 (Appliance Trend Insight)

가전제품 B2B 유통사를 위한 AI 기반 시장 분석 플랫폼입니다.  
네이버 DataLab 검색 트렌드 + 공공데이터를 결합해 수요 예측, 매입 타이밍 신호, AI 전략 리포트를 제공합니다.

---

## 배포

| 구분 | URL | 플랫폼 |
|------|-----|--------|
| **서비스 (Frontend)** | https://appliance-trend-insight.vercel.app | Vercel |
| **DB** | Supabase (PostgreSQL + pgvector) | Supabase |

> Render 무료 플랜은 15분 비활동 시 서버가 슬립되며, 첫 요청 시 30~50초 대기가 발생할 수 있습니다.

### Backend 배포 (Render)

Render Web Service · Python 런타임 · Root Directory `backend` · 시작 명령 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
`.env`에 정의된 환경 변수는 Render 대시보드의 Environment에 동일하게 등록합니다.
`backend/Dockerfile`로 컨테이너 배포도 가능합니다.

### Frontend 배포 (Vercel)

`frontend/vercel.json`의 SPA 라우팅 설정을 사용하며, 빌드된 백엔드 URL을 `VITE_API_BASE` 환경 변수로 주입합니다.

```env
# frontend/.env.production
VITE_API_BASE=https://your-backend-name.onrender.com
```

---

## 주요 기능

### B2B 분석 대시보드
- **시장 현황 분석**: 네이버 검색 관심도 추이, 브랜드 경쟁 구도, 소비자 키워드
- **외부 환경 신호**: 기상청 기온·습도, 에어코리아 PM2.5, 에너지공단 1등급 비율 기반 수요 신호 (공공데이터)
- **AI 시장 리포트**: Groq LLM(gpt-oss-120b) → Cerebras 폴백, 매입 전략·타이밍 자동 생성

### 수요 예측 (Demand Forecast)
- **Holt-Winters 시계열 예측**: 감쇠 추세 지수평활 — 주간 검색량은 2년치 이상이면 52주 연간 계절성까지 반영, 월간 판매 지수는 추세만 사용 (과적합 방지)
  - 평활 계수(α·β·γ·φ)는 1스텝 예측 오차가 가장 작은 조합을 자동 선택, 과거 오차로 신뢰구간 계산
  - 처음엔 Prophet을 썼으나 Render 무료 인스턴스(512MB)에서 메모리 초과로 서버가 재시작되어 순수 파이썬 구현으로 교체 (예측 1회 0.05초 · 추가 메모리 거의 없음)
- **계절성 분석**: 월별 영향도, 선형회귀 기울기, 피크 타이밍 자동 탐지
- **매입 타이밍 신호**: 수요 피크 D-N일 알림, 변곡점 탐지

### 소비자 인사이트
- 네이버 쇼핑·뉴스·블로그 기반 불만 분석 (RAG + pgvector)
- 소비자원 공식 피해 접수 데이터 연동 (한국소비자원 API)
- 가격 신호 분석 (네이버 쇼핑 API)

### 지원 카테고리
에어컨 · 냉장고 · 세탁기 · 건조기 · TV · 선풍기 · 공기청정기 · 제습기 · 가습기 · 로봇청소기 · 식기세척기 · 에어프라이어 · 전기밥솥

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 18, Vite, React Router |
| Backend | FastAPI, Python 3.11 |
| DB / 캐시 | Supabase (PostgreSQL + pgvector) |
| AI / LLM | Groq (openai/gpt-oss-120b → openai/gpt-oss-20b), Cerebras (gpt-oss-120b) |
| 임베딩 | HuggingFace Inference API (sentence-transformers/all-MiniLM-L6-v2, 384차원) |
| 예측 모델 | Holt-Winters 지수평활 (순수 파이썬 구현), 선형회귀 추세선 |
| 외부 데이터 | 네이버 DataLab, 기상청 ASOS, 에어코리아, 한국소비자원, 에너지공단 KEMCO, 통계청 KOSIS |
| 배포 | Render (Backend), Vercel (Frontend) |

---

## 프로젝트 구조

```
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── b2b_ai.py        # 수요예측·AI리포트·환경신호 API
│   │   │   ├── b2b_dashboard.py # 대시보드 데이터 API
│   │   │   ├── b2b_price.py     # 가격 신호 분석
│   │   │   └── auth.py          # 인증 (JWT)
│   │   ├── services/
│   │   │   ├── public_data.py   # 공공데이터 수집 + 백그라운드 갱신 루프
│   │   │   ├── naver_cache.py   # Supabase 캐시 레이어
│   │   │   └── email_service.py
│   │   └── main.py              # lifespan: 공공데이터 자동갱신 루프 등록
│   └── scripts/
│       ├── refresh_ext_data.py      # 공공데이터 수동 수집 (선택)
│       └── seed_rag_local.py        # RAG 문서 로컬 시딩
└── frontend/
    └── src/
        ├── pages/
        │   ├── B2BDashboard.jsx   # 시장 현황 대시보드
        │   ├── B2BForecast.jsx    # 수요 예측
        │   ├── B2BReport.jsx      # AI 전략 리포트
        │   └── B2BPrice.jsx       # 가격 분석
        └── components/
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

# Supabase
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
| 검색량 추이 (주간) | 네이버 데이터랩 검색어 트렌드 | 최근 **730일** (주 단위) | B2B 수요 예측 — Holt-Winters로 **22주** 예측 |
| 쇼핑 클릭 추이 (월간) | 네이버 데이터랩 쇼핑인사이트 | 최근 **730일** (월 단위) | B2B 판매 예측 — Holt-Winters로 **8개월** 예측 |
| 검색량 추이 (일간) | 네이버 데이터랩 검색어 트렌드 | 최근 **30일** (일 단위) | 트렌드 TOP10 · 제품 리포트 · 구매 타이밍 관심도 |
| 제품 가격 이력 | 다나와 가격 이력 + 매일 자체 수집 | 다나와 최대 **24개월** / 화면은 최근 **30일** | 구매 타이밍 · 출시가 대비 할인율 |
| 카테고리 가격 통계 | 다나와 검색 (매일 자체 수집) | 수집 시작일부터 누적 | B2B 시장 분석 · 매입 적기 알림 |
| 기온 · 습도 | 기상청 ASOS | 최근 **730일** | 계절 가전 수요와 날씨 상관 |
| 미세먼지 PM2.5 · PM10 | 에어코리아 | 최근 **90일** | 공기청정기 · 가습기 수요 신호 |
| 소비자물가지수 | 통계청 KOSIS | 최근 **24개월** | AI 리포트 경기 맥락 |
| 위해 피해 접수 | 한국소비자원 | 카테고리 12개 최근 접수 건 | 제품 안전 이슈 |
| 에너지효율 등급 | 한국에너지공단 | 카테고리 7개 1등급 비율 + 모델별 등급 | 효율 등급 표시 · AI 리포트 |

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

### 1. 카테고리별 외부 환경 변수

`backend/app/services/public_data.py` → `get_ext_dataframe(category, ds_dates)`

> 현재 수요 예측(Holt-Winters)은 검색량·판매 지수만으로 예측합니다. 아래 외부 변수는 예측 모델 입력이 아니라 외부 환경 신호와 AI 리포트 컨텍스트에 쓰이며, 변수를 넣는 회귀 모델로 확장할 때를 위해 수집 함수를 남겨두었습니다.

| 카테고리 | 외부 변수 | 데이터 출처 |
|----------|-----------|-------------|
| 에어컨 | 기온(℃), 습도(%), 전기요금, CPI | 기상청 ASOS, 한전, KOSIS |
| 냉장고 | 기온(℃), 전기요금, CPI | 기상청 ASOS, 한전, KOSIS |
| 세탁기·건조기 | 전기요금, CPI | 한전, KOSIS |
| 선풍기 | 기온(℃), CPI | 기상청 ASOS, KOSIS |
| 제습기·가습기 | 기온(℃), 습도(%), CPI | 기상청 ASOS, KOSIS |
| 공기청정기 | PM2.5, PM10(㎍/㎥), CPI | 에어코리아, KOSIS |
| TV | 수입 물량(kg), CPI | 관세청, KOSIS |
| 로봇청소기·식기세척기·에어프라이어·전기밥솥 | CPI | KOSIS |

미래 구간은 월별 역사 평균값(month_avg)으로 외부 변수를 채우도록 되어 있습니다.

### 2. AI 리포트 프롬프트 컨텍스트

`backend/app/routers/b2b_ai.py` → `get_ai_report()`

LLM 프롬프트 생성 전에 Supabase 캐시에서 최신 환경 데이터를 로드해 `■ 외부 환경 신호` 섹션으로 주입합니다.

```
■ 외부 환경 신호 (공공데이터 기준)
  기온 24.7℃ · 습도 65.3% · PM2.5 23㎍/㎥(보통) · 에너지 1등급 비율 38.2% (총 3526개 인증제품 중)
  → 🌤 기온 24.7℃ — 수요 준비 구간 /  에너지 1등급 비율 38.2% — 효율등급 경쟁 확대 중
```

한국소비자원 공식 피해접수 데이터(KCA)가 캐시에 있으면 기존 네이버 스크래핑 불만 데이터를 보강합니다.

### 3. 대시보드 외부 환경 신호 카드

`GET /api/b2b/env-signal?category=에어컨`

카테고리별 최근 7일 평균값을 기준으로 신호 등급을 산출합니다.

| 신호 등급 | 조건 | 표시 |
|-----------|------|------|
| high | 에어컨·선풍기 · 기온 ≥ 27°C | 🔥 수요 상승 신호 |
| mid | 에어컨·선풍기 · 기온 ≥ 20°C | 🌤 수요 준비 구간 |
| low | 에어컨·선풍기 · 기온 < 20°C | ❄️ 비수기 |
| high | 공기청정기 · PM2.5 ≥ 36 | 🌫 나쁨 — 수요 상승 |
| high | 에너지 1등급 비율 ≥ 50% |  고효율 프리미엄 제품 선호 뚜렷 |
| mid | 에너지 1등급 비율 ≥ 25% |  효율등급 경쟁 확대 중 |
| low | 에너지 1등급 비율 < 25% |  보급형 중심 시장 |

---

## Supabase pgvector 활용

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
Supabase rag_documents 테이블에 pgvector 형식으로 저장
        ↓
AI 리포트·수요예측 생성 시 코사인 유사도 검색 (<=> 연산자)
        ↓
상위 N개 청크를 LLM 프롬프트 컨텍스트로 주입
```

### 캐시 레이어 (naver_cache)

| 캐시 키 패턴 | 내용 | TTL |
|---|---|---|
| `naver_dashboard:{category}:{period}` | DataLab 트렌드·브랜드·키워드 | 8시간 |
| `ai_report:v8:{category}:{period}` | AI 전략 리포트 전문 | 8시간 |
| `ext:kma:history` | 기상청 기온·습도 2년치 | 30시간 |
| `ext:airkorea:history` | 에어코리아 PM2.5·PM10 | 30시간 |
| `ext:kosis:cpi` | 통계청 소비자물가지수 24개월치 | 30일 |
| `ext:kca:{category}` | 소비자원 피해접수 | 7일 |
| `ext:kemco:{category}` | 에너지공단 1등급 비율 | 30일 |

---

## 공공데이터 API 출처

| 데이터 | 제공기관 | 신청처 |
|--------|----------|--------|
| 기온·습도 (ASOS 일자료) | 기상청 | data.go.kr |
| PM2.5·PM10 (실시간) | 한국환경공단 에어코리아 | data.go.kr |
| 소비자 피해 접수 | 한국소비자원 | data.go.kr |
| 에너지소비효율 등급 | 한국에너지공단 KEMCO | data.go.kr |
| 소비자물가지수 (2020=100) | 통계청 | kosis.kr |
| TV·에어컨 수출입통계 | 관세청 | unipass.customs.go.kr |
