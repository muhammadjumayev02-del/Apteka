#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -f .env ]]; then
    echo '.env topilmadi. DEPLOYMENT.md dagi lokal sozlash buyruqlarini bajaring.' >&2
    exit 1
fi
set -a
source .env
set +a
if [[ "${DJANGO_DEBUG:-0}" != 1 ]]; then
    echo 'Bu skript faqat lokal HTTP uchun: .env ichida DJANGO_DEBUG=1 belgilang.' >&2
    exit 1
fi
: "${DJANGO_SECRET_KEY:? .env ichida DJANGO_SECRET_KEY ni belgilang (DEPLOYMENT.md).}"
exec .venv/bin/python manage.py runserver 127.0.0.1:8000 "$@"
