-- Appliance Trend Insight
-- MySQL database initialization script
--
-- Usage:
--   mysql -u root -p < backend/study/mysql_setup.sql
--
-- This script does not delete existing tables or data.

CREATE DATABASE IF NOT EXISTS `appliance_trend_insight`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `appliance_trend_insight`;

CREATE TABLE IF NOT EXISTS `users` (
  `user_id` BIGINT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(255) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `user_type` ENUM('b2c', 'b2b') NOT NULL DEFAULT 'b2c',
  `status` ENUM('pending', 'active', 'rejected') NOT NULL DEFAULT 'active',
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `role` VARCHAR(20) NOT NULL DEFAULT 'user',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_b2c_profiles` (
  `profile_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `nickname` VARCHAR(100) DEFAULT NULL,
  PRIMARY KEY (`profile_id`),
  UNIQUE KEY `uq_b2c_profile_user` (`user_id`),
  CONSTRAINT `fk_b2c_profile_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user_b2b_profiles` (
  `profile_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `company_name` VARCHAR(255) NOT NULL,
  `business_type` VARCHAR(100) DEFAULT NULL,
  `contact_phone` VARCHAR(50) DEFAULT NULL,
  PRIMARY KEY (`profile_id`),
  UNIQUE KEY `uq_b2b_profile_user` (`user_id`),
  CONSTRAINT `fk_b2b_profile_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `price_alert` (
  `alert_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `product_name` VARCHAR(255) NOT NULL,
  `target_price` DECIMAL(12,2) NOT NULL,
  `current_price` DECIMAL(12,2) DEFAULT 0.00,
  `product_url` TEXT DEFAULT NULL,
  `alert_type` ENUM('below', 'above') NOT NULL DEFAULT 'below',
  `is_active` TINYINT(1) DEFAULT 1,
  `triggered_at` TIMESTAMP NULL DEFAULT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alert_id`),
  KEY `idx_price_alert_user` (`user_id`),
  CONSTRAINT `fk_price_alert_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `integrated_market_data` (
  `data_id` BIGINT NOT NULL AUTO_INCREMENT,
  `analysis_date` DATE NOT NULL,
  `category_name` VARCHAR(100) NOT NULL,
  `brand_name` VARCHAR(100) NOT NULL DEFAULT '',
  `product_name` VARCHAR(255) NOT NULL DEFAULT 'ALL',
  `trend_type` ENUM('current', 'future', 'potential') DEFAULT NULL,
  `data_sources` JSON DEFAULT NULL,
  `current_price` DECIMAL(12,2) DEFAULT 0.00,
  `market_rank` INT DEFAULT NULL,
  `product_url` TEXT DEFAULT NULL,
  `search_volume_ratio` DECIMAL(5,2) DEFAULT 0.00,
  `search_growth_rate` DECIMAL(6,2) DEFAULT 0.00,
  `demographics_json` JSON DEFAULT NULL,
  `related_keywords` JSON DEFAULT NULL,
  `total_review_count` INT DEFAULT 0,
  `average_rating` DECIMAL(3,2) DEFAULT 0.00,
  `sentiment_positive_ratio` DECIMAL(5,2) DEFAULT 0.00,
  `sentiment_neutral_ratio` DECIMAL(5,2) DEFAULT 0.00,
  `sentiment_negative_ratio` DECIMAL(5,2) DEFAULT 0.00,
  `consumer_feedback_json` JSON DEFAULT NULL,
  `news_mention_count` INT DEFAULT 0,
  `industry_issues_json` JSON DEFAULT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`data_id`),
  UNIQUE KEY `uq_market_snapshot`
    (`analysis_date`, `category_name`, `brand_name`, `product_name`),
  KEY `idx_category_date` (`category_name`, `analysis_date`),
  KEY `idx_brand_date` (`brand_name`, `analysis_date`),
  KEY `idx_trend_type` (`trend_type`)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_reports` (
  `report_id` BIGINT NOT NULL AUTO_INCREMENT,
  `data_id` BIGINT NOT NULL,
  `report_type` ENUM('b2c', 'b2b') NOT NULL,
  `content` TEXT NOT NULL,
  `model_used` VARCHAR(100) DEFAULT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`report_id`),
  KEY `idx_ai_reports_data` (`data_id`),
  CONSTRAINT `fk_ai_reports_market_data`
    FOREIGN KEY (`data_id`) REFERENCES `integrated_market_data` (`data_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `price_history` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `category` VARCHAR(50) NOT NULL,
  `snapshot_date` DATE NOT NULL,
  `avg_price` INT NOT NULL DEFAULT 0,
  `min_price` INT NOT NULL DEFAULT 0,
  `max_price` INT NOT NULL DEFAULT 0,
  `median_price` INT NOT NULL DEFAULT 0,
  `total_products` INT NOT NULL DEFAULT 0,
  `brand_data` JSON DEFAULT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cat_date` (`category`, `snapshot_date`)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `product_price_history` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `product_key` VARCHAR(200) NOT NULL,
  `product_name` VARCHAR(500) DEFAULT NULL,
  `model_number` VARCHAR(100) DEFAULT NULL,
  `min_price` INT NOT NULL DEFAULT 0,
  `max_price` INT NOT NULL DEFAULT 0,
  `avg_price` INT NOT NULL DEFAULT 0,
  `snapshot_date` DATE NOT NULL,
  `mall_data` JSON DEFAULT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prod_date` (`product_key`, `snapshot_date`)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

