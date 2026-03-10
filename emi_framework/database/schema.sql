-- ============================================================
--  Cloud-Based EMI Failure Prevention Framework
--  MySQL Database Schema – Full Setup
--  Compatible: MySQL 8.x / AWS RDS MySQL 8.x
-- ============================================================

-- Create & use the database
CREATE DATABASE IF NOT EXISTS emi_framework
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE emi_framework;

-- ============================================================
-- 1. CUSTOMER TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS Customer (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    full_name       VARCHAR(150)    NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    phone           VARCHAR(20)     NOT NULL,
    password_hash   VARCHAR(512)    NOT NULL,
    date_of_birth   DATE            NOT NULL,
    address         VARCHAR(500)    NOT NULL,
    credit_score    SMALLINT        DEFAULT 700,
    is_active       TINYINT(1)      DEFAULT 1,
    is_admin        TINYINT(1)      DEFAULT 0,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_customer_email (email),
    INDEX idx_customer_phone (phone),
    INDEX idx_customer_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 2. LOAN TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS Loan (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    customer_id         INT UNSIGNED    NOT NULL,
    loan_number         VARCHAR(30)     NOT NULL,
    loan_type           ENUM('HOME','CAR','PERSONAL','EDUCATION','BUSINESS') NOT NULL,
    loan_amount         DECIMAL(14,2)   NOT NULL,
    interest_rate       DECIMAL(5,2)    NOT NULL COMMENT 'Annual rate %',
    tenure_months       SMALLINT        NOT NULL,
    emi_amount          DECIMAL(12,2)   NOT NULL,
    outstanding_balance DECIMAL(14,2)   NOT NULL,
    loan_status         ENUM('ACTIVE','CLOSED','DEFAULTED','RESTRUCTURED') DEFAULT 'ACTIVE',
    disbursement_date   DATE            NOT NULL,
    purpose             VARCHAR(300)    DEFAULT '',
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_loan_number (loan_number),
    INDEX idx_loan_customer   (customer_id),
    INDEX idx_loan_status     (loan_status),
    INDEX idx_loan_disbursed  (disbursement_date),

    CONSTRAINT fk_loan_customer
        FOREIGN KEY (customer_id)
        REFERENCES Customer(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 3. EMI_SCHEDULE TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS EMI_Schedule (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    loan_id             INT UNSIGNED    NOT NULL,
    installment_number  SMALLINT        NOT NULL,
    due_date            DATE            NOT NULL,
    emi_amount          DECIMAL(12,2)   NOT NULL,
    principal_component DECIMAL(12,2)   NOT NULL,
    interest_component  DECIMAL(12,2)   NOT NULL,
    outstanding_balance DECIMAL(14,2)   NOT NULL,
    status              ENUM('PENDING','PAID','OVERDUE','PARTIALLY_PAID') DEFAULT 'PENDING',
    risk_level          ENUM('SAFE','WARNING','CRITICAL')                 DEFAULT 'SAFE',
    payment_date        DATE            DEFAULT NULL,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_emi_installment (loan_id, installment_number),
    INDEX idx_emi_due_date   (due_date),
    INDEX idx_emi_status     (status),
    INDEX idx_emi_risk_level (risk_level),
    INDEX idx_emi_loan       (loan_id),

    CONSTRAINT fk_emi_loan
        FOREIGN KEY (loan_id)
        REFERENCES Loan(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 4. PAYMENT TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS Payment (
    id                      INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    loan_id                 INT UNSIGNED    NOT NULL,
    emi_schedule_id         INT UNSIGNED    NOT NULL,
    amount_paid             DECIMAL(12,2)   NOT NULL,
    payment_date            DATE            NOT NULL,
    payment_method          ENUM('ONLINE','CHEQUE','CASH','AUTO_DEBIT') DEFAULT 'ONLINE',
    transaction_reference   VARCHAR(100)    DEFAULT NULL,
    remarks                 VARCHAR(300)    DEFAULT NULL,
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_payment_loan    (loan_id),
    INDEX idx_payment_emi     (emi_schedule_id),
    INDEX idx_payment_date    (payment_date),

    CONSTRAINT fk_payment_loan
        FOREIGN KEY (loan_id)
        REFERENCES Loan(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    CONSTRAINT fk_payment_emi
        FOREIGN KEY (emi_schedule_id)
        REFERENCES EMI_Schedule(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 5. ALERT TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS Alert (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    loan_id         INT UNSIGNED    NOT NULL,
    emi_schedule_id INT UNSIGNED    NOT NULL,
    alert_type      ENUM('SAFE','WARNING','CRITICAL') NOT NULL,
    message         TEXT            NOT NULL,
    is_sent         TINYINT(1)      DEFAULT 0,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    INDEX idx_alert_loan     (loan_id),
    INDEX idx_alert_emi      (emi_schedule_id),
    INDEX idx_alert_type     (alert_type),
    INDEX idx_alert_created  (created_at),

    CONSTRAINT fk_alert_loan
        FOREIGN KEY (loan_id)
        REFERENCES Loan(id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_alert_emi
        FOREIGN KEY (emi_schedule_id)
        REFERENCES EMI_Schedule(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- SAMPLE DATA
-- Passwords are hashed using PBKDF2-SHA256.
-- Plain-text for testing:
--   john.doe@example.com → password123
--   jane.smith@example.com → securepass
--   admin@emi-framework.com → admin123
-- (Run the app's /api/auth/register to get proper hashes)
-- ============================================================

-- Temporary: insert with placeholder hashes (update via API)
INSERT INTO Customer (full_name, email, phone, password_hash, date_of_birth, address, credit_score, is_active, is_admin)
VALUES
('John Doe',
 'john.doe@example.com',
 '9876543210',
 'placeholder_hash_run_register_api',
 '1990-05-15',
 '45 Nehru Street, Chennai, Tamil Nadu 600001',
 740, 1, 0),

('Jane Smith',
 'jane.smith@example.com',
 '9123456789',
 'placeholder_hash_run_register_api',
 '1988-11-22',
 '12 MG Road, Bengaluru, Karnataka 560001',
 710, 1, 0),

('Admin User',
 'admin@emi-framework.com',
 '9000000001',
 'placeholder_hash_run_register_api',
 '1985-01-10',
 'Head Office, Mumbai, Maharashtra 400001',
 800, 1, 1);


-- Sample Loans (use app to generate proper EMI schedules)
INSERT INTO Loan (customer_id, loan_number, loan_type, loan_amount, interest_rate,
                  tenure_months, emi_amount, outstanding_balance,
                  loan_status, disbursement_date, purpose)
VALUES
(1, 'LN-DEMO0001', 'HOME',     1500000.00, 8.50, 120, 18585.37, 1450000.00, 'ACTIVE', CURDATE() - INTERVAL 2 MONTH, 'Home purchase'),
(1, 'LN-DEMO0002', 'CAR',       600000.00, 9.00,  48, 14921.85,  580000.00, 'ACTIVE', CURDATE() - INTERVAL 1 MONTH, 'New car'),
(2, 'LN-DEMO0003', 'PERSONAL',  200000.00, 12.00, 24,  9415.19,  195000.00, 'ACTIVE', CURDATE() - INTERVAL 15 DAY,  'Medical expenses');


-- ============================================================
-- RISK UPDATE QUERY
-- Run this periodically (e.g., daily via cron / Lambda)
-- Updates risk_level based on due_date and status
-- ============================================================

/*
UPDATE EMI_Schedule
SET risk_level = CASE
    WHEN status = 'PAID'                       THEN 'SAFE'
    WHEN due_date < CURDATE()                  THEN 'CRITICAL'
    WHEN due_date BETWEEN CURDATE()
                      AND CURDATE() + INTERVAL 3 DAY THEN 'WARNING'
    ELSE 'SAFE'
END
WHERE status != 'PAID';
*/

-- Stored Procedure: daily risk refresh
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS sp_refresh_all_risk_levels()
BEGIN
    UPDATE EMI_Schedule
    SET risk_level = CASE
        WHEN status = 'PAID'                                     THEN 'SAFE'
        WHEN due_date < CURDATE()                                THEN 'CRITICAL'
        WHEN due_date BETWEEN CURDATE() AND CURDATE() + INTERVAL 3 DAY THEN 'WARNING'
        ELSE 'SAFE'
    END
    WHERE status != 'PAID';

    SELECT ROW_COUNT() AS rows_updated;
END$$

DELIMITER ;


-- Event: auto-run risk refresh every day at midnight
CREATE EVENT IF NOT EXISTS evt_daily_risk_refresh
ON SCHEDULE EVERY 1 DAY
STARTS (CURRENT_TIMESTAMP + INTERVAL 1 DAY)
DO CALL sp_refresh_all_risk_levels();


-- ============================================================
-- USEFUL VIEWS
-- ============================================================

CREATE OR REPLACE VIEW vw_customer_risk_summary AS
SELECT
    c.id            AS customer_id,
    c.full_name,
    c.email,
    l.id            AS loan_id,
    l.loan_number,
    l.loan_status,
    COUNT(es.id)                                                AS total_instalments,
    SUM(es.status = 'PAID')                                     AS paid_count,
    SUM(es.risk_level = 'WARNING'  AND es.status != 'PAID')     AS warning_count,
    SUM(es.risk_level = 'CRITICAL' AND es.status != 'PAID')     AS critical_count,
    l.outstanding_balance
FROM Customer c
JOIN Loan l          ON l.customer_id = c.id
JOIN EMI_Schedule es ON es.loan_id = l.id
WHERE l.loan_status = 'ACTIVE'
GROUP BY c.id, c.full_name, c.email, l.id, l.loan_number, l.loan_status, l.outstanding_balance;


CREATE OR REPLACE VIEW vw_overdue_emis AS
SELECT
    es.id               AS emi_id,
    es.loan_id,
    l.loan_number,
    c.full_name,
    c.email,
    c.phone,
    es.installment_number,
    es.due_date,
    es.emi_amount,
    DATEDIFF(CURDATE(), es.due_date) AS days_overdue
FROM EMI_Schedule es
JOIN Loan l     ON l.id = es.loan_id
JOIN Customer c ON c.id = l.customer_id
WHERE es.status != 'PAID'
  AND es.due_date < CURDATE()
ORDER BY days_overdue DESC;
