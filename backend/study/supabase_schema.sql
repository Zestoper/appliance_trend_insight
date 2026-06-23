-- Supabase (PostgreSQL) 스키마
-- Supabase > SQL Editor 에서 실행하세요

CREATE TABLE IF NOT EXISTS users (
  user_id       BIGSERIAL PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  user_type     VARCHAR(10)  NOT NULL DEFAULT 'b2c' CHECK (user_type IN ('b2c', 'b2b')),
  status        VARCHAR(20)  NOT NULL DEFAULT 'active' CHECK (status IN ('pending', 'active', 'rejected')),
  is_active     BOOLEAN      DEFAULT TRUE,
  created_at    TIMESTAMPTZ  DEFAULT NOW(),
  role          VARCHAR(20)  NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS user_b2c_profiles (
  profile_id BIGSERIAL PRIMARY KEY,
  user_id    BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
  nickname   VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS user_b2b_profiles (
  profile_id     BIGSERIAL PRIMARY KEY,
  user_id        BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
  company_name   VARCHAR(255) NOT NULL,
  business_type  VARCHAR(100),
  contact_phone  VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS price_alert (
  alert_id      BIGSERIAL PRIMARY KEY,
  user_id       BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  product_name  VARCHAR(255) NOT NULL,
  target_price  NUMERIC(12,2) NOT NULL,
  current_price NUMERIC(12,2) DEFAULT 0,
  product_url   TEXT,
  alert_type    VARCHAR(10) NOT NULL DEFAULT 'below' CHECK (alert_type IN ('below', 'above')),
  is_active     BOOLEAN DEFAULT TRUE,
  triggered_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_price_alert_user ON price_alert(user_id);

CREATE TABLE IF NOT EXISTS integrated_market_data (
  data_id                  BIGSERIAL PRIMARY KEY,
  analysis_date            DATE NOT NULL,
  category_name            VARCHAR(100) NOT NULL,
  brand_name               VARCHAR(100) NOT NULL DEFAULT '',
  product_name             VARCHAR(255) NOT NULL DEFAULT 'ALL',
  trend_type               VARCHAR(20) CHECK (trend_type IN ('current', 'future', 'potential')),
  data_sources             JSONB,
  current_price            NUMERIC(12,2) DEFAULT 0,
  market_rank              INT,
  product_url              TEXT,
  search_volume_ratio      NUMERIC(5,2) DEFAULT 0,
  search_growth_rate       NUMERIC(6,2) DEFAULT 0,
  demographics_json        JSONB,
  related_keywords         JSONB,
  total_review_count       INT DEFAULT 0,
  average_rating           NUMERIC(3,2) DEFAULT 0,
  sentiment_positive_ratio NUMERIC(5,2) DEFAULT 0,
  sentiment_neutral_ratio  NUMERIC(5,2) DEFAULT 0,
  sentiment_negative_ratio NUMERIC(5,2) DEFAULT 0,
  consumer_feedback_json   JSONB,
  news_mention_count       INT DEFAULT 0,
  industry_issues_json     JSONB,
  created_at               TIMESTAMPTZ DEFAULT NOW(),
  updated_at               TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (analysis_date, category_name, brand_name, product_name)
);

CREATE TABLE IF NOT EXISTS ai_reports (
  report_id   BIGSERIAL PRIMARY KEY,
  data_id     BIGINT NOT NULL REFERENCES integrated_market_data(data_id) ON DELETE CASCADE,
  report_type VARCHAR(10) NOT NULL CHECK (report_type IN ('b2c', 'b2b')),
  content     TEXT NOT NULL,
  model_used  VARCHAR(100),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_history (
  id             SERIAL PRIMARY KEY,
  category       VARCHAR(50) NOT NULL,
  snapshot_date  DATE NOT NULL,
  avg_price      INT NOT NULL DEFAULT 0,
  min_price      INT NOT NULL DEFAULT 0,
  max_price      INT NOT NULL DEFAULT 0,
  median_price   INT NOT NULL DEFAULT 0,
  total_products INT NOT NULL DEFAULT 0,
  brand_data     JSONB,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (category, snapshot_date)
);

CREATE TABLE IF NOT EXISTS product_price_history (
  id            SERIAL PRIMARY KEY,
  product_key   VARCHAR(200) NOT NULL,
  product_name  VARCHAR(500),
  model_number  VARCHAR(100),
  min_price     INT NOT NULL DEFAULT 0,
  max_price     INT NOT NULL DEFAULT 0,
  avg_price     INT NOT NULL DEFAULT 0,
  snapshot_date DATE NOT NULL,
  snapshot_hour SMALLINT NOT NULL DEFAULT 0,
  mall_data     JSONB,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (product_key, snapshot_date, snapshot_hour)
);

CREATE TABLE IF NOT EXISTS b2b_prediction_log (
  id               SERIAL PRIMARY KEY,
  category         VARCHAR(50) NOT NULL,
  signal_type      VARCHAR(50) NOT NULL,
  price_at_pred    INT NOT NULL,
  predicted_at     DATE NOT NULL,
  verified_at      DATE,
  price_at_verify  INT,
  price_change_pct FLOAT,
  was_correct      BOOLEAN,
  UNIQUE (category, predicted_at)
);
