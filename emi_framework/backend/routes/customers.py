"""
Customer Routes
GET  /api/customers/               – list all (admin)
GET  /api/customers/<id>           – get one
PUT  /api/customers/<id>           – update profile
GET  /api/customers/<id>/dashboard – aggregated dashboard data
"""

import logging
from flask import Blueprint, jsonify, request, session

from models.db import execute_query
from utils.security import login_required

logger        = logging.getLogger(__name__)
customers_bp  = Blueprint('customers', __name__)


def _serialize(row: dict) -> dict:
    """Convert date/datetime objects to ISO strings."""
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
    return row


@customers_bp.route('/', methods=['GET'])
@login_required
def list_customers():
    if not session.get('is_admin'):
        return jsonify({'error': 'Admin access required.'}), 403
    rows = execute_query(
        "SELECT id, full_name, email, phone, credit_score, is_active, created_at FROM Customer ORDER BY id",
        fetch_all=True
    ) or []
    return jsonify([_serialize(r) for r in rows])


@customers_bp.route('/<int:customer_id>', methods=['GET'])
@login_required
def get_customer(customer_id):
    # Customers may only view their own profile unless admin
    if session['customer_id'] != customer_id and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403

    row = execute_query(
        """SELECT id, full_name, email, phone, date_of_birth,
                  address, credit_score, is_active, created_at
           FROM Customer WHERE id = %s""",
        (customer_id,), fetch_one=True
    )
    if not row:
        return jsonify({'error': 'Customer not found.'}), 404
    return jsonify(_serialize(row))


@customers_bp.route('/<int:customer_id>', methods=['PUT'])
@login_required
def update_customer(customer_id):
    if session['customer_id'] != customer_id and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403

    data    = request.get_json(force=True)
    allowed = ['full_name', 'phone', 'address']
    updates = {k: v for k, v in data.items() if k in allowed and v}

    if not updates:
        return jsonify({'error': 'No valid fields to update.'}), 400

    set_clause = ', '.join(f"{k} = %s" for k in updates)
    values     = list(updates.values()) + [customer_id]
    execute_query(f"UPDATE Customer SET {set_clause} WHERE id = %s", values, commit=True)
    return jsonify({'message': 'Profile updated successfully.'})


@customers_bp.route('/<int:customer_id>/dashboard', methods=['GET'])
@login_required
def dashboard(customer_id):
    """Aggregated dashboard: loan counts, total outstanding, risk summary, recent alerts."""
    if session['customer_id'] != customer_id and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403

    # Loan summary
    loans = execute_query(
        """SELECT id, loan_number, loan_amount, outstanding_balance,
                  loan_status, interest_rate, tenure_months
           FROM Loan WHERE customer_id = %s""",
        (customer_id,), fetch_all=True
    ) or []

    total_outstanding = sum(float(l.get('outstanding_balance') or 0) for l in loans)
    active_loans      = [l for l in loans if l['loan_status'] == 'ACTIVE']

    # Risk summary across all active loans
    risk_counts = {'SAFE': 0, 'WARNING': 0, 'CRITICAL': 0, 'PAID': 0}
    if active_loans:
        loan_ids     = tuple(l['id'] for l in active_loans)
        placeholders = ','.join(['%s'] * len(loan_ids))
        emi_rows     = execute_query(
            f"SELECT risk_level, status FROM EMI_Schedule WHERE loan_id IN ({placeholders})",
            loan_ids, fetch_all=True
        ) or []
        for e in emi_rows:
            st = (e.get('status') or '').upper()
            rl = (e.get('risk_level') or 'SAFE').upper()
            if st == 'PAID':
                risk_counts['PAID'] += 1
            else:
                risk_counts[rl] = risk_counts.get(rl, 0) + 1

    # Recent alerts
    recent_alerts = execute_query(
        """SELECT a.alert_type, a.message, a.created_at, l.loan_number
           FROM Alert a JOIN Loan l ON l.id = a.loan_id
           WHERE l.customer_id = %s
           ORDER BY a.created_at DESC LIMIT 5""",
        (customer_id,), fetch_all=True
    ) or []

    return jsonify({
        'total_loans'      : len(loans),
        'active_loans'     : len(active_loans),
        'total_outstanding': round(total_outstanding, 2),
        'risk_summary'     : risk_counts,
        'loans'            : [_serialize(l) for l in loans],
        'recent_alerts'    : [_serialize(a) for a in recent_alerts]
    })
