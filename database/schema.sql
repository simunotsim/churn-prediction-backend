-- =============================================================================
-- Churn Prediction Analytics - MySQL Schema
-- Run this in MySQL Workbench after connecting to your AWS RDS instance
-- =============================================================================

-- Create database (if not exists)
CREATE DATABASE IF NOT EXISTS churn_prediction;
USE churn_prediction;

-- =============================================================================
-- USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NULL,
    company VARCHAR(255) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    
    INDEX idx_users_email (email),
    INDEX idx_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- DATASET UPLOADS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dataset_uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- Dataset metadata
    filename VARCHAR(255) NOT NULL,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT NULL,
    
    -- Dataset statistics
    total_customers INT DEFAULT 0,
    total_revenue DOUBLE DEFAULT 0.0,
    
    -- Churn analysis results
    predicted_churners INT DEFAULT 0,
    churn_rate DOUBLE DEFAULT 0.0,
    high_risk_count INT DEFAULT 0,
    critical_risk_count INT DEFAULT 0,
    revenue_at_risk DOUBLE DEFAULT 0.0,
    
    -- Segment breakdown (stored as JSON)
    segment_stats JSON NULL,
    
    -- Raw predictions (stored as JSON for comparison)
    predictions_summary JSON NULL,
    
    -- Foreign key constraint
    CONSTRAINT fk_dataset_user 
        FOREIGN KEY (user_id) REFERENCES users(id) 
        ON DELETE CASCADE,
    
    INDEX idx_dataset_user (user_id),
    INDEX idx_dataset_upload_date (upload_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- DATASET COMPARISONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS dataset_comparisons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    
    -- Dataset references
    dataset_1_id INT NOT NULL,
    dataset_2_id INT NOT NULL,
    
    -- Comparison date
    comparison_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Comparison metrics
    customer_change INT DEFAULT 0,
    revenue_change DOUBLE DEFAULT 0.0,
    churn_rate_change DOUBLE DEFAULT 0.0,
    risk_change DOUBLE DEFAULT 0.0,
    
    -- Profit/Loss indicator
    is_improvement BOOLEAN DEFAULT FALSE,
    profit_loss_amount DOUBLE DEFAULT 0.0,
    
    -- Detailed analysis (JSON)
    detailed_comparison JSON NULL,
    
    -- Foreign key constraints
    CONSTRAINT fk_comparison_user 
        FOREIGN KEY (user_id) REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_comparison_dataset1 
        FOREIGN KEY (dataset_1_id) REFERENCES dataset_uploads(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_comparison_dataset2 
        FOREIGN KEY (dataset_2_id) REFERENCES dataset_uploads(id) 
        ON DELETE CASCADE,
    
    INDEX idx_comparison_user (user_id),
    INDEX idx_comparison_date (comparison_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- VERIFY TABLES CREATED
-- =============================================================================
SHOW TABLES;

-- View table structures
DESCRIBE users;
DESCRIBE dataset_uploads;
DESCRIBE dataset_comparisons;
