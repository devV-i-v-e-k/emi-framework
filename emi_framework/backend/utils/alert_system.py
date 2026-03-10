"""
Alert Generation & Notification System
Automatically creates alerts and simulates email notifications
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from models.db import execute_query

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# ALERT CREATION
# ──────────────────────────────────────────────────────────────────────────────

ALERT_MESSAGES = {
    'CRITICAL': "🔴 CRITICAL: Your EMI instalment #{} is OVERDUE since {}. Immediate action required to avoid penalties.",
    'WARNING' : "🟡 WARNING: Your EMI instalment #{} of ₹{:.2f} is due on {}. Please ensure funds are ready.",
    'SAFE'    : "🟢 INFO: Your EMI instalment #{} of ₹{:.2f} is scheduled for {}. Everything looks good."
}


def create_alert(loan_id: int, emi_id: int, alert_type: str,
                 installment_no: int, due_date: str, emi_amount: float,
                 customer_email: str = None) -> int:
    """
    Insert an alert record into the Alert table.

    Returns:
        alert_id (int) of the newly created record
    """
    message = ALERT_MESSAGES.get(alert_type, "EMI alert notification.").format(
        installment_no, emi_amount, due_date
    )

    query = """
        INSERT INTO Alert (loan_id, emi_schedule_id, alert_type, message, created_at, is_sent)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    alert_id = execute_query(
        query,
        params=(loan_id, emi_id, alert_type, message, datetime.utcnow(), False),
        commit=True
    )

    logger.info(f"Alert #{alert_id} created | loan={loan_id} type={alert_type}")

    # Attempt email notification
    if customer_email:
        _send_email_notification(customer_email, alert_type, message)

    return alert_id


def auto_generate_alerts(loan_id: int) -> list:
    """
    Scan all non-PAID EMI instalments for a loan and auto-create
    WARNING / CRITICAL alerts where none already exist today.

    Returns list of alert_ids created.
    """
    query = """
        SELECT es.id, es.installment_number, es.due_date,
               es.emi_amount, es.risk_level,
               c.email AS customer_email
        FROM   EMI_Schedule es
        JOIN   Loan l ON l.id = es.loan_id
        JOIN   Customer c ON c.id = l.customer_id
        WHERE  es.loan_id = %s
          AND  es.status  != 'PAID'
          AND  es.risk_level IN ('WARNING', 'CRITICAL')
    """
    instalments = execute_query(query, params=(loan_id,), fetch_all=True)

    created_ids = []
    for inst in instalments:
        # Avoid duplicate alerts for the same instalment on the same day
        exists = execute_query(
            "SELECT id FROM Alert WHERE emi_schedule_id = %s AND DATE(created_at) = CURDATE()",
            params=(inst['id'],), fetch_one=True
        )
        if not exists:
            aid = create_alert(
                loan_id        = loan_id,
                emi_id         = inst['id'],
                alert_type     = inst['risk_level'],
                installment_no = inst['installment_number'],
                due_date       = str(inst['due_date']),
                emi_amount     = float(inst['emi_amount']),
                customer_email = inst.get('customer_email')
            )
            created_ids.append(aid)

    return created_ids


def get_alerts_for_customer(customer_id: int, limit: int = 50) -> list:
    """Fetch recent alerts for a customer across all loans."""
    query = """
        SELECT a.id, a.alert_type, a.message, a.is_sent,
               a.created_at, l.loan_number, es.installment_number,
               es.due_date, es.emi_amount
        FROM   Alert a
        JOIN   Loan l         ON l.id = a.loan_id
        JOIN   EMI_Schedule es ON es.id = a.emi_schedule_id
        WHERE  l.customer_id = %s
        ORDER  BY a.created_at DESC
        LIMIT  %s
    """
    return execute_query(query, params=(customer_id, limit), fetch_all=True) or []


def mark_alert_sent(alert_id: int) -> None:
    execute_query(
        "UPDATE Alert SET is_sent = TRUE WHERE id = %s",
        params=(alert_id,), commit=True
    )


# ──────────────────────────────────────────────────────────────────────────────
# EMAIL NOTIFICATION (simulated / real SMTP)
# ──────────────────────────────────────────────────────────────────────────────

def _send_email_notification(recipient: str, alert_type: str, message: str) -> bool:
    """
    Send an email notification.
    - If SMTP credentials are configured in .env, sends a real email.
    - Otherwise logs the simulation for development/testing.
    """
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASSWORD')
    sender    = os.getenv('SMTP_FROM', 'no-reply@emi-framework.com')

    subject_map = {
        'CRITICAL': '🔴 URGENT: EMI Payment Overdue',
        'WARNING' : '🟡 Reminder: EMI Payment Due Soon',
        'SAFE'    : '🟢 EMI Schedule Update'
    }
    subject = subject_map.get(alert_type, 'EMI Notification')

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif; padding:20px;">
      <div style="max-width:600px; margin:auto; border:1px solid #e0e0e0; border-radius:8px; overflow:hidden;">
        <div style="background:#1a3c5e; color:white; padding:20px;">
          <h2 style="margin:0;">EMI Failure Prevention Framework</h2>
        </div>
        <div style="padding:20px;">
          <p style="font-size:16px;">{message}</p>
          <hr>
          <p style="color:#777; font-size:12px;">
            This is an automated alert from the Cloud-Based EMI Failure Prevention System.
            Please do not reply to this email.
          </p>
        </div>
      </div>
    </body></html>
    """

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = sender
            msg['To']      = recipient
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(sender, recipient, msg.as_string())

            logger.info(f"Email sent to {recipient} | type={alert_type}")
            return True
        except Exception as e:
            logger.error(f"Email send failed to {recipient}: {e}")
            return False
    else:
        # Simulation mode
        logger.info(
            f"[EMAIL SIMULATION] To: {recipient} | Subject: {subject}\n{message}"
        )
        return True  # Simulate success
