"""
Frontend Routes - serve HTML dashboard pages
Uses absolute paths so it works on Windows, Linux, and macOS.
"""

import os
from flask import Blueprint, render_template, redirect, url_for, session

# Build absolute paths regardless of OS or working directory
_HERE      = os.path.dirname(os.path.abspath(__file__))   # .../backend/routes/
_BACKEND   = os.path.dirname(_HERE)                        # .../backend/
_PROJECT   = os.path.dirname(_BACKEND)                     # .../emi_framework/
_TEMPLATES = os.path.join(_PROJECT, 'frontend', 'templates')
_STATIC    = os.path.join(_PROJECT, 'frontend', 'static')

frontend_bp = Blueprint('frontend', __name__,
                        template_folder=_TEMPLATES,
                        static_folder=_STATIC)


@frontend_bp.route('/')
def index():
    if 'customer_id' in session:
        return redirect(url_for('frontend.dashboard'))
    return redirect(url_for('frontend.login'))


@frontend_bp.route('/login')
def login():
    if 'customer_id' in session:
        return redirect(url_for('frontend.dashboard'))
    return render_template('login.html')


@frontend_bp.route('/dashboard')
def dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('frontend.login'))
    return render_template('dashboard.html',
                           customer_name=session.get('full_name', 'Customer'),
                           customer_id=session['customer_id'])


@frontend_bp.route('/loans')
def loans():
    if 'customer_id' not in session:
        return redirect(url_for('frontend.login'))
    return render_template('loans.html', customer_name=session.get('full_name'))


@frontend_bp.route('/loans/<int:loan_id>')
def loan_detail(loan_id):
    if 'customer_id' not in session:
        return redirect(url_for('frontend.login'))
    return render_template('loan_detail.html',
                           loan_id=loan_id,
                           customer_name=session.get('full_name'))


@frontend_bp.route('/emi/<int:loan_id>')
def emi_schedule(loan_id):
    if 'customer_id' not in session:
        return redirect(url_for('frontend.login'))
    return render_template('emi_schedule.html',
                           loan_id=loan_id,
                           customer_name=session.get('full_name'))


@frontend_bp.route('/alerts')
def alerts():
    if 'customer_id' not in session:
        return redirect(url_for('frontend.login'))
    return render_template('alerts.html', customer_name=session.get('full_name'))


@frontend_bp.route('/calculator')
def calculator():
    return render_template('calculator.html', customer_name=session.get('full_name', ''))
