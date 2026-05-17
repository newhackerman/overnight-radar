CREATE TABLE IF NOT EXISTS us_market_daily (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  trade_date DATE NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  name VARCHAR(128),
  close_price DECIMAL(18,4),
  prev_close DECIMAL(18,4),
  pct_change DECIMAL(10,4),
  volume BIGINT,
  amount DECIMAL(24,4),
  market_cap DECIMAL(24,4),
  sector VARCHAR(128),
  source VARCHAR(32),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_us_daily (trade_date, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS us_top_turnover (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  trade_date DATE NOT NULL,
  rank_no INT NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  name VARCHAR(128),
  close_price DECIMAL(18,4),
  pct_change DECIMAL(10,4),
  volume BIGINT,
  amount DECIMAL(24,4),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_top_turnover (trade_date, symbol),
  KEY idx_trade_rank (trade_date, rank_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cn_market_daily (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  trade_date DATE NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  name VARCHAR(128),
  close_price DECIMAL(18,4),
  prev_close DECIMAL(18,4),
  pct_change DECIMAL(10,4),
  volume BIGINT,
  amount DECIMAL(24,4),
  source VARCHAR(32),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_cn_daily (trade_date, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS event_reference (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  trade_date DATE NOT NULL,
  us_symbol VARCHAR(32) NOT NULL,
  title VARCHAR(512),
  source VARCHAR(128),
  url VARCHAR(1024),
  authority_level VARCHAR(32),
  published_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_event_ref (trade_date, us_symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS report_impact_item (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  report_date DATE NOT NULL,
  us_trade_date DATE NOT NULL,
  us_symbol VARCHAR(32) NOT NULL,
  us_name VARCHAR(128),
  turnover_rank INT NOT NULL,
  pct_change DECIMAL(10,4),
  amount DECIMAL(24,4),
  reason_category VARCHAR(64),
  event_summary VARCHAR(512),
  mapped_cn_targets TEXT,
  mapped_cn_symbols JSON,
  impact_direction VARCHAR(16),
  impact_strength TINYINT,
  impact_score DECIMAL(5,4),
  confidence DECIMAL(5,4),
  event_source VARCHAR(1024),
  source_type VARCHAR(32),
  ai_model VARCHAR(64),
  raw_output JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_report_symbol (report_date, us_symbol),
  KEY idx_report_date (report_date),
  KEY idx_us_trade_date (us_trade_date),
  KEY idx_direction_strength (impact_direction, impact_strength)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS us_cn_mapping_history (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  report_date DATE NOT NULL,
  us_symbol VARCHAR(32) NOT NULL,
  cn_symbol VARCHAR(32),
  cn_name VARCHAR(128),
  relation_type VARCHAR(64),
  theme VARCHAR(128),
  impact_direction VARCHAR(16),
  impact_strength TINYINT,
  impact_score DECIMAL(5,4),
  reason TEXT,
  source VARCHAR(32),
  confidence DECIMAL(5,4),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_mapping_date (report_date),
  KEY idx_us_symbol (us_symbol),
  KEY idx_cn_symbol (cn_symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS backtest_result (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  event_date DATE NOT NULL,
  cn_trade_date DATE NOT NULL,
  us_symbol VARCHAR(32) NOT NULL,
  cn_symbol VARCHAR(32) NOT NULL,
  t_return DECIMAL(10,4),
  t1_return DECIMAL(10,4),
  t3_return DECIMAL(10,4),
  t5_return DECIMAL(10,4),
  t10_return DECIMAL(10,4),
  current_return DECIMAL(10,4),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_backtest (event_date, us_symbol, cn_symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_run_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_name VARCHAR(128) NOT NULL,
  run_date DATE,
  status VARCHAR(32),
  started_at DATETIME,
  finished_at DATETIME,
  error_message TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
