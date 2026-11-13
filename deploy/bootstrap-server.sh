#!/usr/bin/env bash
# Разовая подготовка сервера (от root, идемпотентно): системный пользователь, каталоги,
# роль и база в PostgreSQL, shared/.env со сгенерированным паролем. Секреты в git не попадают.
#   ssh root@host 'bash -s' < deploy/bootstrap-server.sh
set -euo pipefail
ROOT=/var/www/iq.ozzy1986.com
APP_USER=iqapp
DB=iq

id "$APP_USER" >/dev/null 2>&1 || useradd --system --home-dir "$ROOT" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$ROOT/releases" "$ROOT/shared" "$ROOT/acme" "$ROOT/backups"
chmod 755 "$ROOT" "$ROOT/releases" "$ROOT/acme"
chown "$APP_USER:$APP_USER" "$ROOT/releases" "$ROOT/shared" "$ROOT/backups"
chmod 700 "$ROOT/shared" "$ROOT/backups"

if [ ! -f "$ROOT/shared/.env" ]; then
  PASS=$(openssl rand -hex 24)
  if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB'" | grep -q 1; then
    sudo -u postgres psql -qc "ALTER ROLE $DB LOGIN PASSWORD '$PASS'"
  else
    sudo -u postgres psql -qc "CREATE ROLE $DB LOGIN PASSWORD '$PASS'"
  fi
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'" | grep -q 1 \
    || sudo -u postgres createdb -O "$DB" "$DB"
  umask 077
  echo "DATABASE_URL=postgresql+psycopg://$DB:$PASS@127.0.0.1:5432/$DB" > "$ROOT/shared/.env"
  chown "$APP_USER:$APP_USER" "$ROOT/shared/.env"
  chmod 600 "$ROOT/shared/.env"
  echo 'создана база и shared/.env'
else
  echo 'shared/.env уже есть — базу не трогаем'
fi
echo 'bootstrap done'
