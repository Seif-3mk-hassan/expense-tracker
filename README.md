# Xpens — personal expense tracker

Django 5 + PostgreSQL (prod) / SQLite (dev). Dark-themed, desktop-first.

## Setup (dev)

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000 — sign up, log in. Admin at `/admin/`.

## Production

```bash
cp .env.example .env   # then fill in values
set DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py migrate
```

Required env: `DJANGO_SECRET_KEY`, `DATABASE_URL` (postgres://…),
`DJANGO_ALLOWED_HOSTS` (comma-separated). Postgres needs `psycopg`
(shipped in requirements) and `ssl_require=True` is enforced.

## Tests

```bash
python manage.py test
```
