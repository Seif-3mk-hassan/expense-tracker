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
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py check --deploy
```

Required env: `DJANGO_SECRET_KEY`, `DATABASE_URL` (postgres://…),
`DJANGO_ALLOWED_HOSTS` (comma-separated). Postgres needs `psycopg`
(shipped in requirements) and `ssl_require=True` is enforced.
Serve behind gunicorn or similar; never use `runserver` in production.

## Backup and restore

- Postgres: `pg_dump $DATABASE_URL > xpens-backup.sql`, restore with `psql`.
- App-level backup any time: Settings → Data → Export JSON (per user).
- Dev SQLite: copy `db.sqlite3` while the server is stopped.

## Demo script (under 15 minutes)

```bash
python -m venv .venv && .\.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --user demo   # demo/demo1234, 16 rows, 12,450 EGP
python manage.py test                    # expect all green
python manage.py runserver
```

Log in as demo: dashboard hero, weekly chart, donut, budgets with one
near-limit warning, insights tip, then Settings → Export JSON round-trip.

## Tests

```bash
python manage.py test
```
