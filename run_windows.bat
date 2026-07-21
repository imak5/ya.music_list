@echo off
chcp 65001 >nul
REM Двойной клик по этому файлу в Проводнике запускает приложение.
REM При первом запуске сам создаёт окружение и ставит зависимости —
REM это займёт немного больше времени, чем последующие запуски.

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python не найден.
    echo Установите его отсюда: https://www.python.org/downloads/windows/
    echo ВАЖНО: на первом экране установщика поставьте галочку "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist venv (
    echo Первый запуск: создаю окружение и ставлю зависимости...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo Запускаю приложение...
python yamusic_library.py

echo.
echo Приложение закрыто.
pause
