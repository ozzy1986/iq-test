#!/usr/bin/env bash
# Серверная конфигурация (идемпотентно): оба vhost'а, сертификат, systemd-юнит.
# Вызывается deploy.sh после переключения релиза; вручную от root:
#   bash /var/www/iq.ozzy1986.com/current/deploy/setup-server.sh
set -euo pipefail
ROOT=/var/www/iq.ozzy1986.com
CUR=$ROOT/current
DOMAIN=iq.ozzy1986.com

[ -L "$CUR" ] || { echo "нет $CUR — сначала deploy/deploy.sh"; exit 1; }

enable_site() {  # a2ensite отказывается работать, если в sites-enabled лежит обычный файл, а не ссылка
  local enabled="/etc/apache2/sites-enabled/$1.conf"
  if [ -e "$enabled" ] && [ ! -L "$enabled" ]; then rm -f "$enabled"; fi
  a2ensite -q "$1"
}

echo '--- apache: http vhost ---'
install -m 644 "$CUR/deploy/apache-$DOMAIN.conf" "/etc/apache2/sites-available/$DOMAIN.conf"
enable_site "$DOMAIN"

echo '--- certificate ---'
if ! certbot certificates 2>/dev/null | grep -q "Certificate Name: $DOMAIN"; then
  apache2ctl configtest && systemctl reload apache2
  certbot certonly --webroot -w "$ROOT/acme" -d "$DOMAIN" --non-interactive --agree-tos
else
  echo 'сертификат уже есть'
fi

echo '--- apache: https vhost ---'
install -m 644 "$CUR/deploy/apache-$DOMAIN-le-ssl.conf" "/etc/apache2/sites-available/$DOMAIN-le-ssl.conf"
enable_site "$DOMAIN-le-ssl"
apache2ctl configtest
systemctl reload apache2

echo '--- systemd ---'
if ! cmp -s "$CUR/deploy/iq.service" /etc/systemd/system/iq.service; then
  install -m 644 "$CUR/deploy/iq.service" /etc/systemd/system/iq.service
  systemctl daemon-reload
fi
systemctl enable iq.service >/dev/null 2>&1 || true
echo 'setup done'
