"""
Test Suite – Cloud-Based EMI Failure Prevention Framework
Run: pytest tests/ -v
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from utils.emi_engine import (
    calculate_emi, generate_emi_schedule,
    assess_emi_risk, compute_loan_summary, risk_summary_from_schedule
)
from utils.security import hash_password, verify_password
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────────────
# EMI Calculation Tests
# ──────────────────────────────────────────────────────────────────────

class TestEMICalculation:

    def test_basic_emi(self):
        """Standard 12% loan for 12 months on 100,000"""
        emi = calculate_emi(100000, 12.0, 12)
        assert abs(emi - 8884.88) < 1.0, f"Expected ~8884.88, got {emi}"

    def test_zero_interest(self):
        """Zero interest = principal / tenure"""
        emi = calculate_emi(120000, 0, 12)
        assert emi == 10000.0

    def test_long_tenure(self):
        """Home loan: 15L at 8.5% for 120 months"""
        emi = calculate_emi(1500000, 8.5, 120)
        assert 18000 < emi < 19500, f"Out of expected range: {emi}"

    def test_emi_rounding(self):
        """Result should have max 2 decimal places"""
        emi = calculate_emi(250000, 10.75, 36)
        assert emi == round(emi, 2)

    def test_schedule_length(self):
        """Generated schedule should have exactly N rows"""
        schedule = generate_emi_schedule(1, 100000, 10.0, 12, date.today())
        assert len(schedule) == 12

    def test_schedule_balance_reaches_zero(self):
        """Last instalment outstanding balance should be 0"""
        schedule = generate_emi_schedule(1, 100000, 10.0, 24, date.today())
        assert schedule[-1]['outstanding_balance'] == 0.0

    def test_schedule_totals(self):
        """Sum of principal components should equal original principal (±1 for rounding)"""
        p = 200000
        schedule = generate_emi_schedule(1, p, 9.0, 36, date.today())
        total_principal = sum(row['principal_component'] for row in schedule)
        assert abs(total_principal - p) < 2.0, f"Principal mismatch: {total_principal}"

    def test_loan_summary(self):
        """Total payment must equal EMI × tenure"""
        s = compute_loan_summary(500000, 10.0, 60)
        assert abs(s['total_payment'] - s['emi_amount'] * 60) < 2.0


# ──────────────────────────────────────────────────────────────────────
# Risk Detection Tests
# ──────────────────────────────────────────────────────────────────────

class TestRiskDetection:

    def test_paid_is_safe(self):
        rec = {'status': 'PAID', 'due_date': (date.today() - timedelta(days=5)).isoformat()}
        assert assess_emi_risk(rec) == 'SAFE'

    def test_overdue_is_critical(self):
        rec = {'status': 'PENDING', 'due_date': (date.today() - timedelta(days=1)).isoformat()}
        assert assess_emi_risk(rec) == 'CRITICAL'

    def test_due_today_is_warning(self):
        rec = {'status': 'PENDING', 'due_date': date.today().isoformat()}
        assert assess_emi_risk(rec) == 'WARNING'

    def test_due_in_2_days_is_warning(self):
        rec = {'status': 'PENDING', 'due_date': (date.today() + timedelta(days=2)).isoformat()}
        assert assess_emi_risk(rec) == 'WARNING'

    def test_due_in_30_days_is_safe(self):
        rec = {'status': 'PENDING', 'due_date': (date.today() + timedelta(days=30)).isoformat()}
        assert assess_emi_risk(rec) == 'SAFE'

    def test_due_exactly_3_days_is_warning(self):
        rec = {'status': 'PENDING', 'due_date': (date.today() + timedelta(days=3)).isoformat()}
        assert assess_emi_risk(rec) == 'WARNING'

    def test_due_in_4_days_is_safe(self):
        rec = {'status': 'PENDING', 'due_date': (date.today() + timedelta(days=4)).isoformat()}
        assert assess_emi_risk(rec) == 'SAFE'


# ──────────────────────────────────────────────────────────────────────
# Security / Password Tests
# ──────────────────────────────────────────────────────────────────────

class TestSecurity:

    def test_password_hash_is_not_plain(self):
        h = hash_password("mysecret")
        assert "mysecret" not in h

    def test_correct_password_verifies(self):
        pwd  = "StrongPassword123!"
        h    = hash_password(pwd)
        assert verify_password(pwd, h) is True

    def test_wrong_password_fails(self):
        h = hash_password("correctpassword")
        assert verify_password("wrongpassword", h) is False

    def test_hash_is_salted(self):
        """Same password → different hashes (due to random salt)"""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_hash_format(self):
        """Hash should contain salt:hash separated by colon"""
        h = hash_password("test")
        parts = h.split(':')
        assert len(parts) == 2
        assert len(parts[0]) == 64   # 32-byte hex salt
        assert len(parts[1]) > 10


# ──────────────────────────────────────────────────────────────────────
# Risk Summary Tests
# ──────────────────────────────────────────────────────────────────────

class TestRiskSummary:

    def test_summary_counts(self):
        schedule = [
            {'status': 'PAID',    'risk_level': 'SAFE'},
            {'status': 'PAID',    'risk_level': 'SAFE'},
            {'status': 'PENDING', 'risk_level': 'WARNING'},
            {'status': 'PENDING', 'risk_level': 'CRITICAL'},
            {'status': 'PENDING', 'risk_level': 'SAFE'},
        ]
        s = risk_summary_from_schedule(schedule)
        assert s['PAID']     == 2
        assert s['WARNING']  == 1
        assert s['CRITICAL'] == 1
        assert s['SAFE']     == 1
