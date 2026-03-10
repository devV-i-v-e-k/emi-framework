"""
EMI Calculation Engine & Risk Detection Algorithm
Core business logic for the EMI Failure Prevention Framework
"""

import math
import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# EMI CALCULATION
# ──────────────────────────────────────────────────────────────────────────────

def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    Calculate EMI using standard reducing-balance formula:
        EMI = [P × R × (1+R)^N] / [(1+R)^N – 1]

    Args:
        principal      : Loan amount in currency units
        annual_rate    : Annual interest rate as percentage (e.g., 12.0 for 12%)
        tenure_months  : Loan tenure in months

    Returns:
        Monthly EMI amount (rounded to 2 decimal places)
    """
    if annual_rate == 0:
        return round(principal / tenure_months, 2)

    monthly_rate = annual_rate / (12 * 100)           # R  (monthly decimal rate)
    power        = (1 + monthly_rate) ** tenure_months # (1+R)^N

    emi = (principal * monthly_rate * power) / (power - 1)
    return round(emi, 2)


def generate_emi_schedule(loan_id: int, principal: float, annual_rate: float,
                          tenure_months: int, start_date: date) -> list:
    """
    Generate a complete amortization schedule for a loan.

    Returns a list of dicts, one per instalment:
        installment_number, due_date, emi_amount,
        principal_component, interest_component, outstanding_balance,
        risk_level, status
    """
    monthly_rate = annual_rate / (12 * 100)
    emi          = calculate_emi(principal, annual_rate, tenure_months)
    schedule     = []
    balance      = Decimal(str(principal))

    for i in range(1, tenure_months + 1):
        interest_component  = float(balance) * monthly_rate
        principal_component = emi - interest_component
        balance            -= Decimal(str(principal_component))

        # Correct last instalment for rounding drift
        if i == tenure_months:
            principal_component += float(balance)
            balance = Decimal('0.00')

        due_date = start_date + timedelta(days=30 * i)
        risk     = _assess_risk_by_date(due_date)

        schedule.append({
            'loan_id'             : loan_id,
            'installment_number'  : i,
            'due_date'            : due_date.isoformat(),
            'emi_amount'          : round(emi, 2),
            'principal_component' : round(principal_component, 2),
            'interest_component'  : round(interest_component, 2),
            'outstanding_balance' : max(0.0, round(float(balance), 2)),
            'risk_level'          : risk,
            'status'              : 'PENDING'
        })

    logger.info(f"Generated {tenure_months}-month schedule for loan_id={loan_id}.")
    return schedule


# ──────────────────────────────────────────────────────────────────────────────
# RULE-BASED RISK DETECTION
# ──────────────────────────────────────────────────────────────────────────────

def _assess_risk_by_date(due_date: date) -> str:
    """
    Pure date-based risk classification used during schedule generation.
    """
    today = date.today()
    delta = (due_date - today).days

    if delta < 0:
        return 'CRITICAL'   # Already overdue
    elif delta <= 3:
        return 'WARNING'    # Due within 3 days
    else:
        return 'SAFE'


def assess_emi_risk(emi_record: dict) -> str:
    """
    Rule-Based Risk Detection Algorithm.

    Rules (evaluated in priority order):
        1. status == PAID          → SAFE
        2. due_date < today        → CRITICAL  (overdue)
        3. due_date within 3 days  → WARNING
        4. Otherwise               → SAFE

    Args:
        emi_record : dict with keys 'status', 'due_date'

    Returns:
        Risk level string: 'SAFE' | 'WARNING' | 'CRITICAL'
    """
    status   = (emi_record.get('status') or '').upper()
    due_date = emi_record.get('due_date')

    # Rule 1 – Already paid
    if status == 'PAID':
        return 'SAFE'

    # Parse due_date
    if isinstance(due_date, str):
        try:
            due_date = date.fromisoformat(due_date)
        except ValueError:
            logger.warning(f"Invalid due_date format: {due_date}")
            return 'SAFE'

    if due_date is None:
        return 'SAFE'

    today = date.today()
    delta = (due_date - today).days

    # Rule 2 – Overdue
    if delta < 0:
        return 'CRITICAL'

    # Rule 3 – Due very soon
    if delta <= 3:
        return 'WARNING'

    # Rule 4 – Default safe
    return 'SAFE'


def batch_update_risk_levels(emi_records: list) -> list:
    """
    Apply risk assessment to a list of EMI records and return
    only those whose risk_level has changed.
    """
    updated = []
    for record in emi_records:
        new_risk = assess_emi_risk(record)
        if new_risk != record.get('risk_level'):
            updated.append({
                'id'        : record['id'],
                'risk_level': new_risk
            })
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# FINANCIAL SUMMARY HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def compute_loan_summary(principal: float, annual_rate: float, tenure_months: int) -> dict:
    """Return a high-level financial summary for a loan."""
    emi        = calculate_emi(principal, annual_rate, tenure_months)
    total_pay  = round(emi * tenure_months, 2)
    total_int  = round(total_pay - principal, 2)
    int_pct    = round((total_int / principal) * 100, 2) if principal else 0

    return {
        'emi_amount'      : emi,
        'total_payment'   : total_pay,
        'total_interest'  : total_int,
        'interest_percent': int_pct,
        'principal'       : principal,
        'annual_rate'     : annual_rate,
        'tenure_months'   : tenure_months
    }


def risk_summary_from_schedule(schedule: list) -> dict:
    """Aggregate risk counts from a schedule list."""
    counts = {'SAFE': 0, 'WARNING': 0, 'CRITICAL': 0, 'PAID': 0}
    for item in schedule:
        status = item.get('status', '').upper()
        risk   = item.get('risk_level', 'SAFE').upper()
        if status == 'PAID':
            counts['PAID'] += 1
        else:
            counts[risk] = counts.get(risk, 0) + 1
    return counts
