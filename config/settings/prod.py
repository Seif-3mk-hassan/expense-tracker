"""Production settings: Postgres via DATABASE_URL, no insecure defaults."""
import dj_database_url

from .base import *

DEBUG = False
ALLOWED_HOSTS = [
    host for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if host
]

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL", conn_max_age=600, ssl_require=True
    )
}

if not os.environ.get("DJANGO_SECRET_KEY"):
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")
