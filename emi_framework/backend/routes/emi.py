"""
EMI Schedule Routes
GET  /api/emi/loan/<loan_id>            – full schedule
POST /api/emi/<emi_id>/pay              – record payment
POST /api/emi/loan/<loan_id>/refresh    – re-evaluate risk levels
GET  /api/emi/calculate                 – on-the-fly EMI calculator (no auth)
"""

import logging
from datetime import date

from flask import Blueprint, jsonify, request, session

from models.db import execute_query, get_db
from utils.emi_engine import assess_emi_risk, batch_update_risk_levels, compute_loan_summary
from utils.alert_system import auto_generate_alerts
from utils.security import login_required

logger  = logging.getLogger(__name__)
emi_bp  = Blueprint('emi', __name__)


def _serialize(row: dict) -> dict:
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
    return row


@emi_bp.route('/calculate', methods=['GET'])
def calculate():
    """Stateless EMI calculator – no authentication required."""
    try:
        principal   = float(request.args['principal'])
        annual_rate = float(request.args['annual_rate'])
        tenure      = int(request.args['tenure_months'])
    except (KeyError, ValueError):
        return jsonify({'error': 'Provide principal, annual_rate, tenure_months as query params.'}), 400

    result = compute_loan_summary(principal, annual_rate, tenure)
    return jsonify(result)


@emi_bp.route('/loan/<int:loan_id>', methods=['GET'])
@login_required
def schedule(loan_id):
    # Verify ownership
    loan = execute_query("SELECT customer_id FROM Loan WHERE id = %s", (loan_id,), fetch_one=True)
    if not loan:
        return jsonify({'error': 'Loan not found.'}), 404
    if loan['customer_id'] != session['customer_id'] and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403

    rows = execute_query(
        """SELECT id, installment_number, due_date, emi_amount,
                  principal_component, interest_component, outstanding_balance,
                  status, risk_level, payment_date
           FROM EMI_Schedule
           WHERE loan_id = %s
           ORDER BY installment_number""",
        (loan_id,), fetch_all=True
    ) or []

    total      = len(rows)
    paid       = sum(1 for r in rows if r['status'] == 'PAID')
    pending    = total - paid
    critical_c = sum(1 for r in rows if r['risk_level'] == 'CRITICAL' and r['status'] != 'PAID')
    warning_c  = sum(1 for r in rows if r['risk_level'] == 'WARNING'  and r['status'] != 'PAID')

    return jsonify({
        'loan_id'   : loan_id,
        'summary'   : {
            'total'   : total,
            'paid'    : paid,
            'pending' : pending,
            'critical': critical_c,
            'warning' : warning_c
        },
        'schedule'  : [_serialize(r) for r in rows]
    })


@emi_bp.route('/<int:emi_id>/pay', methods=['POST'])
@login_required
def pay_emi(emi_id):
    """Record payment for an EMI instalment."""
    # Verify ownership through loan → customer chain
    emi = execute_query(
        """SELECT es.*, l.customer_id, l.outstanding_balance AS loan_balance,
                  l.emi_amount
           FROM EMI_Schedule es
           JOIN Loan l ON l.id = es.loan_id
           WHERE es.id = %s""",
        (emi_id,), fetch_one=True
    )
    if not emi:
        return jsonify({'error': 'EMI record not found.'}), 404
    if emi['customer_id'] != session['customer_id'] and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403
    if emi['status'] == 'PAID':
        return jsonify({'error': 'This instalment is already paid.'}), 409

    data           = request.get_json(force=True)
    amount_paid    = float(data.get('amount_paid', float(emi['emi_amount'])))
    payment_method = data.get('payment_method', 'ONLINE')
    payment_date   = date.today()

    db = get_db()
    with db.cursor() as cur:
        # Mark EMI as paid
        cur.execute(
            """UPDATE EMI_Schedule
               SET status = 'PAID', risk_level = 'SAFE', payment_date = %s
               WHERE id = %s""",
            (payment_date, emi_id)
        )
        # Record payment
        cur.execute(
            """INSERT INTO Payment
                   (loan_id, emi_schedule_id, amount_paid, payment_date,
                    payment_method, transaction_reference)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (emi['loan_id'], emi_id, amount_paid, payment_date,
             payment_method, f"TXN{emi_id}{int(date.today().strftime('%Y%m%d'))}")
        )
        # Reduce loan outstanding balance
        cur.execute(
            "UPDATE Loan SET outstanding_balance = GREATEST(0, outstanding_balance - %s) WHERE id = %s",
            (emi['principal_component'], emi['loan_id'])
        )
        db.commit()

    logger.info(f"EMI #{emi_id} paid | loan={emi['loan_id']} | amount={amount_paid}")
    return jsonify({'message': 'Payment recorded successfully.', 'amount_paid': amount_paid})


@emi_bp.route('/loan/<int:loan_id>/refresh', methods=['POST'])
@login_required
def refresh_risk(loan_id):
    """
    Re-evaluate risk levels for all pending EMIs of a loan
    and auto-generate alerts for WARNING/CRITICAL instalments.
    """
    loan = execute_query("SELECT customer_id FROM Loan WHERE id = %s", (loan_id,), fetch_one=True)
    if not loan:
        return jsonify({'error': 'Loan not found.'}), 404
    if loan['customer_id'] != session['customer_id'] and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403

    records = execute_query(
        "SELECT id, due_date, status, risk_level FROM EMI_Schedule WHERE loan_id = %s AND status != 'PAID'",
        (loan_id,), fetch_all=True
    ) or []

    updated = batch_update_risk_levels(records)

    if updated:
        db = get_db()
        with db.cursor() as cur:
            for item in updated:
                cur.execute(
                    "UPDATE EMI_Schedule SET risk_level = %s WHERE id = %s",
                    (item['risk_level'], item['id'])
                )
            db.commit()

    alert_ids = auto_generate_alerts(loan_id)

    return jsonify({
        'message'      : 'Risk levels refreshed.',
        'updated_count': len(updated),
        'alerts_created': len(alert_ids)
    })
