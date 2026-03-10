"""
Loan Routes
POST /api/loans/                  – create loan + generate EMI schedule
GET  /api/loans/                  – list loans for current customer
GET  /api/loans/<id>              – loan detail
PUT  /api/loans/<id>/status       – update loan status (admin)
"""

import logging
import random
import string
from datetime import date

from flask import Blueprint, jsonify, request, session

from models.db import execute_query
from utils.emi_engine import calculate_emi, generate_emi_schedule, compute_loan_summary
from utils.security import login_required

logger   = logging.getLogger(__name__)
loans_bp = Blueprint('loans', __name__)


def _loan_number() -> str:
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"LN-{suffix}"


def _serialize(row: dict) -> dict:
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
    return row


@loans_bp.route('/', methods=['GET'])
@login_required
def list_loans():
    customer_id = session['customer_id']
    rows = execute_query(
        """SELECT l.id, l.loan_number, l.loan_amount, l.interest_rate,
                  l.tenure_months, l.outstanding_balance, l.loan_status,
                  l.disbursement_date, l.loan_type, l.purpose
           FROM Loan l
           WHERE l.customer_id = %s
           ORDER BY l.id DESC""",
        (customer_id,), fetch_all=True
    ) or []
    return jsonify([_serialize(r) for r in rows])


@loans_bp.route('/<int:loan_id>', methods=['GET'])
@login_required
def get_loan(loan_id):
    row = execute_query(
        """SELECT l.*, c.full_name AS customer_name, c.email AS customer_email
           FROM Loan l JOIN Customer c ON c.id = l.customer_id
           WHERE l.id = %s""",
        (loan_id,), fetch_one=True
    )
    if not row:
        return jsonify({'error': 'Loan not found.'}), 404

    if row['customer_id'] != session['customer_id'] and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403

    summary = compute_loan_summary(
        float(row['loan_amount']),
        float(row['interest_rate']),
        int(row['tenure_months'])
    )
    return jsonify({**_serialize(row), 'financial_summary': summary})


@loans_bp.route('/', methods=['POST'])
@login_required
def create_loan():
    data     = request.get_json(force=True)
    required = ['loan_amount', 'interest_rate', 'tenure_months', 'loan_type']
    missing  = [f for f in required if data.get(f) is None]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400

    customer_id   = session['customer_id']
    principal     = float(data['loan_amount'])
    annual_rate   = float(data['interest_rate'])
    tenure        = int(data['tenure_months'])

    if principal <= 0 or annual_rate < 0 or tenure <= 0:
        return jsonify({'error': 'Invalid loan parameters.'}), 400

    emi        = calculate_emi(principal, annual_rate, tenure)
    loan_num   = _loan_number()
    start_date = date.today()

    loan_id = execute_query(
        """INSERT INTO Loan
               (customer_id, loan_number, loan_amount, interest_rate, tenure_months,
                emi_amount, outstanding_balance, loan_status,
                disbursement_date, loan_type, purpose)
           VALUES (%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s,%s,%s)""",
        (customer_id, loan_num, principal, annual_rate, tenure,
         emi, principal, start_date,
         data['loan_type'], data.get('purpose', '')),
        commit=True
    )

    # Generate full amortisation schedule
    schedule = generate_emi_schedule(loan_id, principal, annual_rate, tenure, start_date)

    insert_query = """
        INSERT INTO EMI_Schedule
            (loan_id, installment_number, due_date, emi_amount,
             principal_component, interest_component, outstanding_balance,
             risk_level, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    db = None
    from models.db import get_db
    db = get_db()
    with db.cursor() as cur:
        for inst in schedule:
            cur.execute(insert_query, (
                inst['loan_id'], inst['installment_number'], inst['due_date'],
                inst['emi_amount'], inst['principal_component'],
                inst['interest_component'], inst['outstanding_balance'],
                inst['risk_level'], inst['status']
            ))
        db.commit()

    logger.info(f"Loan {loan_num} created | id={loan_id} | EMI={emi}")
    return jsonify({
        'message'   : 'Loan created and EMI schedule generated.',
        'loan_id'   : loan_id,
        'loan_number': loan_num,
        'emi_amount': emi
    }), 201


@loans_bp.route('/<int:loan_id>/status', methods=['PUT'])
@login_required
def update_loan_status(loan_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Admin access required.'}), 403

    data   = request.get_json(force=True)
    status = data.get('loan_status', '').upper()
    valid  = {'ACTIVE', 'CLOSED', 'DEFAULTED', 'RESTRUCTURED'}
    if status not in valid:
        return jsonify({'error': f'Invalid status. Valid: {valid}'}), 400

    execute_query(
        "UPDATE Loan SET loan_status = %s WHERE id = %s",
        (status, loan_id), commit=True
    )
    return jsonify({'message': f'Loan status updated to {status}.'})
