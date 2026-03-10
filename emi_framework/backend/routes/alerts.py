"""
Alerts Routes
GET  /api/alerts/              – list alerts for current customer
GET  /api/alerts/summary       – risk summary counts
PUT  /api/alerts/<id>/read     – mark alert as sent/read
POST /api/alerts/trigger/<lid> – manually trigger alert generation for a loan
"""

import logging
from flask import Blueprint, jsonify, session

from models.db import execute_query
from utils.alert_system import auto_generate_alerts, get_alerts_for_customer, mark_alert_sent
from utils.security import login_required

logger    = logging.getLogger(__name__)
alerts_bp = Blueprint('alerts', __name__)


def _serialize(row: dict) -> dict:
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
    return row


@alerts_bp.route('/', methods=['GET'])
@login_required
def list_alerts():
    alerts = get_alerts_for_customer(session['customer_id'])
    return jsonify([_serialize(a) for a in alerts])


@alerts_bp.route('/summary', methods=['GET'])
@login_required
def alert_summary():
    rows = execute_query(
        """SELECT a.alert_type, COUNT(*) AS cnt
           FROM Alert a
           JOIN Loan l ON l.id = a.loan_id
           WHERE l.customer_id = %s
           GROUP BY a.alert_type""",
        (session['customer_id'],), fetch_all=True
    ) or []

    summary = {'CRITICAL': 0, 'WARNING': 0, 'SAFE': 0}
    for r in rows:
        summary[r['alert_type']] = int(r['cnt'])
    return jsonify(summary)


@alerts_bp.route('/<int:alert_id>/read', methods=['PUT'])
@login_required
def mark_read(alert_id):
    # Verify ownership
    alert = execute_query(
        """SELECT a.id FROM Alert a JOIN Loan l ON l.id = a.loan_id
           WHERE a.id = %s AND l.customer_id = %s""",
        (alert_id, session['customer_id']), fetch_one=True
    )
    if not alert:
        return jsonify({'error': 'Alert not found or access denied.'}), 404

    mark_alert_sent(alert_id)
    return jsonify({'message': 'Alert marked as read.'})


@alerts_bp.route('/trigger/<int:loan_id>', methods=['POST'])
@login_required
def trigger_alerts(loan_id):
    loan = execute_query("SELECT customer_id FROM Loan WHERE id = %s", (loan_id,), fetch_one=True)
    if not loan:
        return jsonify({'error': 'Loan not found.'}), 404
    if loan['customer_id'] != session['customer_id'] and not session.get('is_admin'):
        return jsonify({'error': 'Access denied.'}), 403

    ids = auto_generate_alerts(loan_id)
    return jsonify({'message': f'{len(ids)} alert(s) generated.', 'alert_ids': ids})
