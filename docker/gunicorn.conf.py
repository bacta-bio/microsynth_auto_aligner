import multiprocessing
import os
from dotenv import load_dotenv  # type: ignore
load_dotenv()

# Networking
bind = os.getenv("GUNICORN_BIND", os.getenv("PORT", "0.0.0.0:8080"))

# Workers/threads
workers = os.getenv("GUNICORN_WORKERS", max(2, multiprocessing.cpu_count()))
threads = os.getenv("GUNICORN_THREADS", 4)

# Timeouts
timeout = os.getenv("GUNICORN_TIMEOUT", 60)
keepalive = os.getenv("GUNICORN_KEEPALIVE", 5)

# Proxy headers (enable when behind proxy)
x_forwarded_for_header = "X-Forwarded-For"
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
proxy_allow_ips = os.getenv("PROXY_ALLOW_FROM", "*")

# Logging
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")