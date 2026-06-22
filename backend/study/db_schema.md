# DB 스키마 설명 — appliance_trend_insight

---

## users — 로그인 계정

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `user_id` | BIGINT | 유저 고유 번호 (자동 증가) |
| `email` | VARCHAR(255) | 이메일 (로그인 아이디) |
| `password_hash` | VARCHAR(255) | 암호화된 비밀번호 (평문 저장 절대 금지) |
| `user_type` | ENUM | `b2c` = 일반 소비자 / `b2b` = 사업자 |
| `is_active` | BOOLEAN | 계정 활성 여부 (탈퇴 시 false) |
| `created_at` | TIMESTAMP | 가입 일시 |

---

## user_b2c_profiles — 일반 소비자 추가정보

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `profile_id` | BIGINT | 프로필 고유 번호 |
| `user_id` | BIGINT | users 테이블 참조 (FK) |
| `nickname` | VARCHAR(100) | 닉네임 |

---

## user_b2b_profiles — 사업자 추가정보

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `profile_id` | BIGINT | 프로필 고유 번호 |
| `user_id` | BIGINT | users 테이블 참조 (FK) |
| `company_name` | VARCHAR(255) | 회사명 |
| `business_type` | VARCHAR(100) | 업종 (유통, 제조, 리테일 등) |
| `contact_phone` | VARCHAR(50) | 담당자 연락처 |

---

## integrated_market_data — 핵심 시장 데이터

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `data_id` | BIGINT | 데이터 고유 번호 (자동 증가) |
| `analysis_date` | DATE | 데이터 수집 기준일 |
| `category_name` | VARCHAR(100) | 카테고리 (냉장고, 에어컨 등) |
| `brand_name` | VARCHAR(100) | 브랜드명 (카테고리 전체 분석이면 빈 문자열 `''`) |
| `product_name` | VARCHAR(255) | 상품명 (카테고리 전체 통계면 `'ALL'`) |
| `trend_type` | ENUM | `current` = 현재 트렌드 / `future` = 미래 전망 / `potential` = 잠재 트렌드 |
| `data_sources` | JSON | 수집 소스 배열 (예: `["naver_shopping", "datalab"]`) |
| `current_price` | DECIMAL(12,2) | 현재가 또는 카테고리 평균가 |
| `market_rank` | INT | 판매/인기 순위 |
| `product_url` | TEXT | 네이버 쇼핑 링크 |
| `search_volume_ratio` | DECIMAL(5,2) | 네이버 데이터랩 검색량 지수 (0~100) |
| `search_growth_rate` | DECIMAL(6,2) | 전주/전월 대비 검색량 증가율 (%) |
| `demographics_json` | JSON | 성별·연령별 관심도 |
| `related_keywords` | JSON | 연관·급상승 검색어 배열 |
| `total_review_count` | INT | 총 리뷰 수 |
| `average_rating` | DECIMAL(3,2) | 평균 평점 (0.00~5.00) |
| `sentiment_positive_ratio` | DECIMAL(5,2) | 긍정 리뷰 비율 (%) |
| `sentiment_neutral_ratio` | DECIMAL(5,2) | 중립 리뷰 비율 (%) |
| `sentiment_negative_ratio` | DECIMAL(5,2) | 부정 리뷰 비율 (%) |
| `consumer_feedback_json` | JSON | 장단점·불만사항 요약 |
| `news_mention_count` | INT | 뉴스 언급 건수 |
| `industry_issues_json` | JSON | 주요 이슈 키워드 배열 |
| `created_at` | TIMESTAMP | 최초 저장 일시 |
| `updated_at` | TIMESTAMP | 마지막 수정 일시 (자동 갱신) |

### UNIQUE KEY 설명

```
UNIQUE KEY uq_market_snapshot (analysis_date, category_name, brand_name, product_name)
```

같은 날짜 + 카테고리 + 브랜드 + 상품명 조합이 중복 저장되지 않도록 방지.  
이미 있는 데이터를 갱신하려면 `INSERT ... ON DUPLICATE KEY UPDATE` 사용.

### INDEX 설명

| 인덱스명 | 컬럼 | 용도 |
|---|---|---|
| `idx_category_date` | category_name, analysis_date | 카테고리별 날짜 범위 조회 시 빠르게 |
| `idx_brand_date` | brand_name, analysis_date | 브랜드별 트렌드 조회 시 빠르게 |
| `idx_trend_type` | trend_type | 트렌드 유형 필터링 시 빠르게 |

---

## ai_reports — AI 생성 리포트

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `report_id` | BIGINT | 리포트 고유 번호 |
| `data_id` | BIGINT | integrated_market_data 참조 (FK) |
| `report_type` | ENUM | `b2c` = 소비자용 리포트 / `b2b` = 사업자용 리포트 |
| `content` | TEXT | AI가 생성한 리포트 전문 |
| `model_used` | VARCHAR(100) | 사용한 AI 모델명 (예: `llama-3.3-70b-versatile`) |
| `created_at` | TIMESTAMP | 리포트 생성 일시 |

> integrated_market_data와 분리한 이유: 리포트만 재생성하거나 여러 버전을 보관할 때 데이터 행 전체를 수정하지 않아도 되기 때문.

---

## price_alert — 가격 알림

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `alert_id` | BIGINT | 알림 고유 번호 |
| `user_id` | BIGINT | 알림 설정한 유저 (FK → users) |
| `product_name` | VARCHAR(255) | 감시할 상품명 |
| `target_price` | DECIMAL(12,2) | 목표 가격 (이 가격 도달 시 알림 발송) |
| `current_price` | DECIMAL(12,2) | 마지막으로 확인한 현재가 |
| `product_url` | TEXT | 상품 링크 |
| `alert_type` | ENUM | `below` = 목표가 이하로 떨어지면 / `above` = 이상이면 |
| `is_active` | BOOLEAN | 알림 활성 여부 (끄면 false) |
| `triggered_at` | TIMESTAMP | 알림이 실제로 발동된 시각 (미발동이면 NULL) |
| `created_at` | TIMESTAMP | 알림 등록 일시 |

---

## 테이블 관계 요약

```
users
 ├── user_b2c_profiles  (1:1, user_type='b2c'인 경우)
 ├── user_b2b_profiles  (1:1, user_type='b2b'인 경우)
 └── price_alert        (1:N, 유저 한 명이 여러 알림 등록 가능)

integrated_market_data
 └── ai_reports         (1:N, 같은 데이터에 b2c/b2b 리포트 각각 생성)
```
