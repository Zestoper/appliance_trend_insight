# 가전무쌍 (Appliance Trend Insight)

가전제품 B2B 유통사를 위한 AI 기반 시장 분석 플랫폼입니다.  
네이버 DataLab 검색 트렌드 + 공공데이터를 결합해 수요 예측, 매입 타이밍 신호, AI 전략 리포트를 제공합니다.

---

## 주요 기능

### B2B 분석 대시보드
- **시장 현황 분석**: 네이버 검색 관심도 추이, 브랜드 경쟁 구도, 소비자 키워드
- **외부 환경 신호**: 기상청 기온·습도, 에어코리아 PM2.5 기반 수요 신호 (공공데이터)
- **AI 시장 리포트**: Groq LLM(llama-3.3-70b) → Cerebras 폴백, 매입 전략·타이밍 자동 생성

### 수요 예측 (Demand Forecast)
- **Prophet + XGBoost 앙상블**: 2년치 주별 트렌드 학습, RMSE 기반 가중치 자동 조정
- **공공데이터 외부 변수**: 기온·습도·PM2.5를 Prophet `add_regressor` / XGBoost feature로 주입
- **계절성 분석**: 월별 영향도, 선형회귀 기울기, 피크 타이밍 자동 탐지
- **매입 타이밍 신호**: 수요 피크 D-N일 알림, 변곡점 탐지

### 소비자 인사이트
- 네이버 쇼핑·뉴스·블로그 기반 불만 분석 (RAG + pgvector)
- 소비자원 공식 피해 접수 데이터 연동 (한국소비자원 API)
- 가격 신호 분석 (네이버 쇼핑 API)

### 지원 카테고리
에어컨 · 냉장고 · 세탁기 · 건조기 · 공기청정기 · 로봇청소기 · 식기세척기 · TV

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 18, Vite, React Router |
| Backend | FastAPI, Python 3.11 |
| DB / 캐시 | Supabase (PostgreSQL + pgvector) |
| AI / LLM | Groq (llama-3.3-70b-versatile → llama-3.1-8b-instant), Cerebras (gpt-oss-120b) |
| 임베딩 | HuggingFace Inference API (sentence-transformers/all-MiniLM-L6-v2, 384차원) |
| 예측 모델 | Prophet, XGBoost, NumPy/Pandas |
| 외부 데이터 | 네이버 DataLab, 기상청 ASOS, 에어코리아, 한국소비자원, 통계청 KOSIS |
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
│   │   └── services/
│   │       ├── public_data.py   # 공공데이터 수집 (기상청·에어코리아 등)
│   │       ├── naver_cache.py   # Supabase 캐시 레이어
│   │       └── email_service.py
│   └── scripts/
│       ├── refresh_naver_cache.py   # 네이버 DataLab 사전 수집
│       └── refresh_ext_data.py      # 공공데이터 사전 수집
└── frontend/
    └── src/
        ├── pages/
        │   ├── B2BDashboard.jsx   # 시장 현황 대시보드
        │   ├── B2BForecast.jsx    # 수요 예측
        │   └── B2BReport.jsx      # AI 전략 리포트
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

### 공공데이터 초기 수집 (최초 1회)
```bash
cd backend
python -m scripts.refresh_ext_data --type kma airkorea kca kemco
```

---

## 데이터 수집 스케줄 (crontab)

```cron
# 네이버 DataLab (Render 해외 차단 → 로컬 Mac에서 실행)
0 */8 * * *  python3 -m scripts.refresh_naver_cache --periods 1m 3m 6m 1y

# 공공데이터
0 * * * *    python3 -m scripts.refresh_ext_data --type airkorea
0 */3 * * *  python3 -m scripts.refresh_ext_data --type kma
0 7 * * *    python3 -m scripts.refresh_ext_data --type kca
0 6 * * 1    python3 -m scripts.refresh_ext_data --type kemco kosis
0 5 1 * *    python3 -m scripts.refresh_ext_data --type customs kepco
```

---

## 공공데이터 활용 상세

공공데이터는 세 곳에서 활용됩니다.

### 1. 수요 예측 모델 외부 변수 (Prophet · XGBoost)

`backend/app/services/public_data.py` → `get_ext_dataframe(category, ds_dates)`

Supabase에 사전 수집된 공공데이터를 카테고리별로 로드해 Prophet `add_regressor` / XGBoost feature vector에 주입합니다.

| 카테고리 | 외부 변수 | 데이터 출처 |
|----------|-----------|-------------|
| 에어컨·선풍기 | 기온(℃), 습도(%) | 기상청 ASOS |
| 냉장고 | 기온(℃) | 기상청 ASOS |
| 제습기 | 기온(℃), 습도(%) | 기상청 ASOS |
| 가습기 | 습도(%) | 기상청 ASOS |
| 공기청정기 | PM2.5, PM10(㎍/㎥) | 에어코리아 |
| TV | 수입 물량(kg) | 관세청 수출입통계 |
| 세탁기·건조기 | 전기요금(원/kWh) | 한국전력공사 |

미래 예측 구간은 월별 역사 평균값(month_avg)으로 외부 변수를 채워 과거 계절 패턴을 반영합니다.

### 2. AI 리포트 프롬프트 컨텍스트

`backend/app/routers/b2b_ai.py` → `get_ai_report()`

LLM 프롬프트 생성 전에 Supabase 캐시에서 최신 환경 데이터를 로드해 `■ 외부 환경 신호` 섹션으로 주입합니다.

```
■ 외부 환경 신호 (공공데이터 기준)
  기온 24.7°C · 습도 65.3% · PM2.5 23㎍/㎥(보통)
  → 🌤 기온 24.7°C — 수요 준비 구간
```

한국소비자원 공식 피해접수 데이터(KCA)가 캐시에 있으면 기존 네이버 스크래핑 불만 데이터를 보강합니다.

### 3. 대시보드 외부 환경 신호 카드

`GET /api/b2b/env-signal?category=에어컨`

카테고리별 최근 7일 평균값을 기준으로 신호 등급을 산출합니다.

| 신호 등급 | 조건 예시 | 표시 |
|-----------|-----------|------|
| high (빨강) | 에어컨 · 기온 ≥ 27°C | 🔥 수요 상승 신호 |
| mid (노랑) | 에어컨 · 기온 ≥ 20°C | 🌤 수요 준비 구간 |
| low (회색) | 에어컨 · 기온 < 20°C | ❄️ 비수기 |
| high (빨강) | 공기청정기 · PM2.5 ≥ 36 | 🌫 나쁨 — 수요 상승 |

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

**임베딩 생성**: HuggingFace Inference API (배치 8개씩, 최대 3회 재시도)

**벡터 검색 쿼리**:
```sql
SELECT text
FROM rag_documents
ORDER BY embedding <=> $1::vector
LIMIT $2
```

### 캐시 레이어 (naver_cache)

Render 서버는 Naver/공공데이터 API가 해외 IP 차단되므로, 로컬 Mac crontab에서 사전 수집 후 Supabase에 저장합니다. Render는 캐시만 읽어 응답합니다.

| 캐시 키 패턴 | 내용 | TTL |
|---|---|---|
| `naver_dashboard:{category}:{period}` | DataLab 트렌드·브랜드·키워드 | 8시간 |
| `ai_report:v8:{category}:{period}` | AI 전략 리포트 전문 | 8시간 |
| `ext:kma:history` | 기상청 기온·습도 2년치 | 6시간 |
| `ext:airkorea:history` | 에어코리아 PM2.5·PM10 | 2시간 |
| `ext:kca:{category}` | 소비자원 피해접수 | 24시간 |

---

## 공공데이터 API 출처

| 데이터 | 제공기관 | 신청처 |
|--------|----------|--------|
| 기온·습도 (ASOS 일자료) | 기상청 | data.go.kr |
| PM2.5·PM10 (실시간) | 한국환경공단 에어코리아 | data.go.kr |
| 소비자 피해 접수 | 한국소비자원 | data.go.kr |
| 에너지소비효율 등급 | 한국에너지공단 | data.go.kr |
| 소비자물가지수 | 통계청 | kosis.kr |
| TV·에어컨 수출입통계 | 관세청 | unipass.customs.go.kr |
