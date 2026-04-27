"""
Gunicorn configuration for Render deployment.
Tuned to survive free-tier cold starts and handle concurrent requests.
"""

import os

# Server socket
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# Worker processes
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
worker_class = "sync"

# Timeouts — critical for Render free-tier cold starts
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# Preload application to reduce memory and speed up worker startup
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None
