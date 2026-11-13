#!/usr/bin/env bash
# Локальная сборка фронтенда перед загрузкой релиза: на сервере Node не нужен.
set -euo pipefail
cd "$(dirname "$0")/../web"
npm ci --no-audit --no-fund --loglevel=error
npm run build
