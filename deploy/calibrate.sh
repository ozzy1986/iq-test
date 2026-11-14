#!/usr/bin/env bash
# Пересчёт сложности заданий по накопленным ответам. Запускается из cron раз в сутки от iqapp
# (ставит deploy/setup-server.sh); вручную: sudo -u iqapp bash deploy/calibrate.sh
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . /var/www/iq.ozzy1986.com/shared/.env; set +a
date "+--- %F %T ---"
exec venv/bin/python -m app.calibrate
