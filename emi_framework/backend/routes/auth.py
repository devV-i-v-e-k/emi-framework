"""
Authentication Routes
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/register
GET  /api/auth/me
"""

import logging
from flask import Blueprint, request, jsonify, session

from models.db import execute_query
from utils.security import hash_password, verify_password, login_required

logger   = logging.getLogger(__name__)
auth_bp  = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(force=True)
    required = ['full_name', 'email', 'phone', 'password', 'dob', 'address']
    missing  = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing fields: {", ".join(missing)}'}), 400

    # Duplicate email check
    existing = execute_query(
        "SELECT id FROM Customer WHERE email = %s", (data['email'],), fetch_one=True
    )
    if existing:
        return jsonify({'error': 'Email already registered.'}), 409

    pwd_hash = hash_password(data['password'])

    customer_id = execute_query(
        """INSERT INTO Customer (full_name, email, phone, password_hash,
                                date_of_birth, address, credit_score, is_active)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (data['full_name'], data['email'], data['phone'], pwd_hash,
         data['dob'], data['address'], data.get('credit_score', 700), True),
        commit=True
    )
    logger.info(f"New customer registered id={customer_id}")
    return jsonify({'message': 'Registration successful', 'customer_id': customer_id}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data  = request.get_json(force=True)
    email = data.get('email', '').strip().lower()
    pwd   = data.get('password', '')

    if not email or not pwd:
        return jsonify({'error': 'Email and password are required.'}), 400

    customer = execute_query(
        "SELECT id, full_name, email, password_hash, is_active, is_admin FROM Customer WHERE email = %s",
        (email,), fetch_one=True
    )

    if not customer or not verify_password(pwd, customer['password_hash']):
        return jsonify({'error': 'Invalid email or password.'}), 401

    if not customer['is_active']:
        return jsonify({'error': 'Account is inactive. Contact support.'}), 403

    session.clear()
    session.permanent = True
    session['customer_id'] = customer['id']
    session['full_name']   = customer['full_name']
    session['email']       = customer['email']
    session['is_admin']    = bool(customer.get('is_admin', False))

    logger.info(f"Customer login: id={customer['id']} email={email}")
    return jsonify({
        'message'    : 'Login successful',
        'customer_id': customer['id'],
        'full_name'  : customer['full_name'],
        'is_admin'   : session['is_admin']
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    customer_id = session.get('customer_id')
    session.clear()
    logger.info(f"Customer logout: id={customer_id}")
    return jsonify({'message': 'Logged out successfully.'})


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    customer = execute_query(
        """SELECT id, full_name, email, phone, date_of_birth,
                  address, credit_score, created_at
           FROM Customer WHERE id = %s""",
        (session['customer_id'],), fetch_one=True
    )
    if not customer:
        return jsonify({'error': 'Customer not found.'}), 404

    # Serialise dates
    if customer.get('date_of_birth'):
        customer['date_of_birth'] = str(customer['date_of_birth'])
    if customer.get('created_at'):
        customer['created_at'] = str(customer['created_at'])

    return jsonify(customer)
