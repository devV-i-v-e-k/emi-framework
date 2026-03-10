# gunicorn.conf.py
# Production Gunicorn configuration for EMI Framework
# Usage: gunicorn -c gunicorn.conf.py app:app

import os
import multiprocessing

# ── Binding ────────────────────────────────────────────────
bind    = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# ── Worker Processes ───────────────────────────────────────
# Recommended: (2 × CPU_count) + 1
workers          = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class     = 'sync'
worker_connections = 1000
timeout          = 120
keepalive        = 5
max_requests     = 1000
max_requests_jitter = 100

# ── Logging ────────────────────────────────────────────────
accesslog  = '-'       # stdout → captured by CloudWatch
errorlog   = '-'       # stderr
loglevel   = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Security ───────────────────────────────────────────────
limit_request_line   = 4096
limit_request_fields = 100

# ── Process Naming ─────────────────────────────────────────
proc_name = 'emi-framework'
