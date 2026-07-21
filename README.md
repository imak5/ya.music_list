# Yandex Music Library Viewer

Небольшое кроссплатформенное GUI-приложение на Python для просмотра своей медиатеки Яндекс Музыки: авторизация через Яндекс ID по QR-коду и вывод списка лайкнутых треков («Мне нравится») с возможностью экспорта в CSV/TXT.

![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)
![python](https://img.shields.io/badge/python-3.9%2B-yellow)
![license](https://img.shields.io/badge/license-MIT-green)

## Возможности

- 🔐 Авторизация через Яндекс ID по официальному OAuth Device Flow — сканируете QR-код телефоном или переходите по ссылке, вводите код, подтверждаете доступ. Пароль в приложение не вводится и не хранится.
- 💾 Токен сохраняется локально после первого входа — повторно логиниться не нужно.
- 🎵 Список треков из раздела «Мне нравится»: исполнитель, название, альбом, длительность.
- 📤 Экспорт списка в `.csv` или `.txt`.
- 🔄 Обновление списка и выход из аккаунта прямо из интерфейса.
- 🖥️ Работает на macOS и Windows (обычный tkinter, без сторонних GUI-фреймворков).

## Скриншот

<img width="920" height="608" alt="Снимок экрана — 2026-07-21 в 14 16 33" src="https://github.com/user-attachments/assets/7aa75f13-9880-4e86-b10b-670713b85964" />

## Требования

- Python 3.9+
- Пакеты из [`requirements.txt`](requirements.txt): [`yandex-music`](https://github.com/MarshalX/yandex-music-api), `qrcode`, `Pillow`
- tkinter (на macOS иногда нужно доустановить отдельно, см. ниже; на Windows идёт в комплекте с python.org-установщиком)

## Установка и запуск

### macOS

Проще всего — двойной клик по `Run.command` в Finder (при первом запуске он сам создаст окружение и поставит зависимости).

Либо вручную:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 yamusic_library.py
```

Если Python не видит tkinter (`No module named tkinter`): `brew install python-tk`, либо ставьте Python с [python.org](https://www.python.org/downloads/macos/) — там Tcl/Tk уже включён.

### Windows

Проще всего — двойной клик по `run_windows.bat` в Проводнике (при первом запуске он сам создаст окружение и поставит зависимости).

Либо вручную (PowerShell / cmd):

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python yamusic_library.py
```

Python ставьте с [python.org/downloads/windows](https://www.python.org/downloads/windows/) — при установке обязательно включите **«Add python.exe to PATH»**. Tkinter входит в установщик по умолчанию.

## Как проходит авторизация

1. Нажмите **«Войти через Яндекс ID»**.
2. Приложение получает от Яндекса код устройства и показывает QR-код + короткий код подтверждения, одновременно открывая страницу подтверждения в браузере по умолчанию.
3. Отсканируйте QR камерой телефона (или используйте открывшуюся вкладку браузера), войдите под своим Яндекс ID, введите код и разрешите доступ.
4. Токен сохраняется локально:
   - macOS: `~/.yandex_music_gui/token.json`
   - Windows: `C:\Users\<имя>\.yandex_music_gui\token.json`

Используется официальный OAuth Device Flow, встроенный в библиотеку [`yandex-music`](https://github.com/MarshalX/yandex-music-api) — без ввода пароля и без хранения учётных данных приложением.

## Структура репозитория

```
.
├── yamusic_library.py     # основной скрипт приложения
├── requirements.txt       # зависимости
├── Run.command            # запуск в один клик (macOS)
├── run_windows.bat        # запуск в один клик (Windows)
├── LICENSE                # текст лицензии MIT
├── .gitignore             # venv/, __pycache__/, сохранённый токен
└── README.md
```

## Перенос в Spotify

Экспортированный из приложения `.csv`/`.txt` можно загрузить на
[TuneMyMusic](https://www.tunemymusic.com/ru/transfer) — сервис принимает
файл со списком треков (поддерживает TXT, CSV и другие форматы) и
переносит их в плейлист Spotify (или другой сервис) автоматически, без
ручного поиска каждого трека.

## Ограничения

- Показывается только раздел «Мне нравится» (лайкнутые треки). Треки из отдельных плейлистов сейчас не подтягиваются — при желании легко добавить через `client.users_playlists_list()`.
- [`yandex-music`](https://github.com/MarshalX/yandex-music-api) — неофициальная, поддерживаемая сообществом библиотека для работы с API Яндекс Музыки по персональному OAuth-токену.

## Лицензия

MIT — используйте и модифицируйте свободно. См. файл [LICENSE](LICENSE).
