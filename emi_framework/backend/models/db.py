"""
Database Connection & Initialization
Manages MySQL connection pool for the EMI Framework
"""

import os
import logging
import pymysql
from flask import g

logger = logging.getLogger(__name__)

_app = None


def init_db(app):
    """Bind the database configuration to the Flask app."""
    global _app
    _app = app
    app.teardown_appcontext(close_db)
    logger.info("Database module initialized.")


def get_db():
    """
    Open a new database connection if one does not already exist
    for the current application context.
    """
    if 'db' not in g:
        try:
            g.db = pymysql.connect(
                host=_app.config['MYSQL_HOST'],
                port=_app.config['MYSQL_PORT'],
                user=_app.config['MYSQL_USER'],
                password=_app.config['MYSQL_PASSWORD'],
                database=_app.config['MYSQL_DB'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30
            )
            logger.debug("New database connection established.")
        except pymysql.MySQLError as e:
            logger.error(f"Database connection failed: {e}")
            raise
    return g.db


def close_db(exception=None):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        logger.debug("Database connection closed.")


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Centralised query execution helper.
    Returns:
        - lastrowid  if commit=True
        - dict       if fetch_one=True
        - list[dict] if fetch_all=True
        - None       otherwise
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(query, params or ())
            if commit:
                db.commit()
                return cursor.lastrowid
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
    except pymysql.MySQLError as e:
        db.rollback()
        logger.error(f"Query execution error: {e} | Query: {query[:120]}")
        raise
