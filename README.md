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

## 공공데이터 API 출처

| 데이터 | 제공기관 | 신청처 |
|--------|----------|--------|
| 기온·습도 (ASOS 일자료) | 기상청 | data.go.kr |
| PM2.5·PM10 (실시간) | 한국환경공단 에어코리아 | data.go.kr |
| 소비자 피해 접수 | 한국소비자원 | data.go.kr |
| 에너지소비효율 등급 | 한국에너지공단 | data.go.kr |
| 소비자물가지수 | 통계청 | kosis.kr |
| TV·에어컨 수출입통계 | 관세청 | unipass.customs.go.kr |
