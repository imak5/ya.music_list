#!/bin/bash
# Двойной клик по этому файлу в Finder запускает приложение.
# При первом запуске сам создаёт окружение и ставит зависимости —
# это займёт немного больше времени, чем последующие запуски.

set -e

# Переходим в папку, где лежит этот файл (даже если запущено двойным кликом)
cd "$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 не найден."
    echo "Установите его отсюда: https://www.python.org/downloads/macos/"
    echo "Нажмите Enter, чтобы закрыть окно…"
    read -r
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Первый запуск: создаю окружение и ставлю зависимости…"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "Запускаю приложение…"
python3 yamusic_library.py

echo ""
echo "Приложение закрыто. Нажмите Enter, чтобы закрыть окно…"
read -r
