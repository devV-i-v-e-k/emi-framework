"""
Cloud-Based EMI Failure Prevention Framework
Main Flask Application Entry Point
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from models.db import init_db
from routes.auth import auth_bp
from routes.customers import customers_bp
from routes.loans import loans_bp
from routes.emi import emi_bp
from routes.alerts import alerts_bp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)


def create_app():
    """Application Factory Pattern"""
    app = Flask(__name__)

    # ── Core Configuration ─────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'emi-framework-secret-key-2024')
    app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

    # MySQL / RDS Configuration
    app.config['MYSQL_HOST']     = os.getenv('DB_HOST', 'localhost')
    app.config['MYSQL_PORT']     = int(os.getenv('DB_PORT', 3306))
    app.config['MYSQL_USER']     = os.getenv('DB_USER', 'emi_user')
    app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD', 'emi_password')
    app.config['MYSQL_DB']       = os.getenv('DB_NAME', 'emi_framework')

    # Session / Security
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('SESSION_LIFETIME', 3600))

    # ── Extensions ────────────────────────────────────────────────────
    CORS(app, origins=os.getenv('ALLOWED_ORIGINS', '*'))

    # ── Database ──────────────────────────────────────────────────────
    init_db(app)

    # ── Blueprints ────────────────────────────────────────────────────
    app.register_blueprint(auth_bp,      url_prefix='/api/auth')
    app.register_blueprint(customers_bp, url_prefix='/api/customers')
    app.register_blueprint(loans_bp,     url_prefix='/api/loans')
    app.register_blueprint(emi_bp,       url_prefix='/api/emi')
    app.register_blueprint(alerts_bp,    url_prefix='/api/alerts')

    # ── Frontend Routes ───────────────────────────────────────────────
    from routes.frontend import frontend_bp
    app.register_blueprint(frontend_bp)

    logger.info("EMI Failure Prevention Framework started successfully.")
    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])
