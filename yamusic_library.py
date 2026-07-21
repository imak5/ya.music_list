#!/usr/bin/env python3
"""
Yandex Music — просмотр медиатеки («Мне нравится»).

Авторизация — через официальный OAuth Device Flow библиотеки yandex-music:
приложение показывает QR-код (страницу подтверждения) и короткий код
для ввода на этой странице. Отсканируйте QR телефоном (или откройте
ссылку в браузере на компьютере), введите показанный код и подтвердите
вход под своим Яндекс ID. После этого токен сохраняется локально
(~/.yandex_music_gui/token.json), чтобы не логиниться заново при
следующих запусках.

Установка:
    pip install -r requirements.txt

Запуск:
    python3 yamusic_library.py

Примечание про tkinter на macOS:
    Если увидите ошибку "No module named tkinter" — переустановите Python
    с python.org (там Tcl/Tk идёт в комплекте) либо, если используете
    Homebrew: brew install python-tk
"""

from __future__ import annotations

import csv
import json
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import qrcode
from PIL import Image, ImageTk
from yandex_music import Client
from yandex_music.exceptions import DeviceAuthError

CONFIG_DIR = Path.home() / ".yandex_music_gui"
TOKEN_FILE = CONFIG_DIR / "token.json"
APP_TITLE = "Яндекс Музыка — медиатека"


# ---------------------------------------------------------------------------
# Локальное хранение токена
# ---------------------------------------------------------------------------

def save_token(token: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps({"token": token}), encoding="utf-8")
    try:
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass


def load_token() -> Optional[str]:
    if not TOKEN_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        return data.get("token")
    except (json.JSONDecodeError, OSError):
        return None


def clear_token() -> None:
    try:
        TOKEN_FILE.unlink()
    except FileNotFoundError:
        pass


def ms_to_mmss(duration_ms) -> str:
    if not duration_ms:
        return "—"
    seconds = duration_ms // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


# ---------------------------------------------------------------------------
# Приложение
# ---------------------------------------------------------------------------

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("920x580")
        self.root.minsize(700, 400)

        self.event_queue: "queue.Queue[tuple]" = queue.Queue()
        self.client: Optional[Client] = None
        self.tracks_data: list[dict] = []

        self._build_ui()
        self.root.after(100, self._poll_queue)

        existing_token = load_token()
        if existing_token:
            self.status_var.set("Найден сохранённый вход, подключаюсь…")
            self._start_client_with_token(existing_token)
        else:
            self.status_var.set("Не авторизован")

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        self.login_btn = ttk.Button(top, text="Войти через Яндекс ID", command=self.start_login)
        self.login_btn.pack(side="left")

        self.refresh_btn = ttk.Button(top, text="Обновить", command=self.load_library, state="disabled")
        self.refresh_btn.pack(side="left", padx=6)

        self.export_btn = ttk.Button(top, text="Экспортировать в файл…", command=self.export_tracks,
                                      state="disabled")
        self.export_btn.pack(side="left")

        self.logout_btn = ttk.Button(top, text="Выйти", command=self.logout, state="disabled")
        self.logout_btn.pack(side="left", padx=6)

        info = ttk.Frame(self.root, padding=(10, 0))
        info.pack(fill="x")

        self.status_var = tk.StringVar(value="")
        ttk.Label(info, textvariable=self.status_var).pack(anchor="w")

        # Панель входа по QR-коду (видна только во время авторизации)
        self.login_panel = ttk.Frame(self.root, padding=10)
        self._qr_photo = None  # держим ссылку, иначе tkinter удалит картинку из памяти

        self.qr_label = ttk.Label(self.login_panel)
        self.qr_label.pack(side="left", padx=(0, 16))

        text_col = ttk.Frame(self.login_panel)
        text_col.pack(side="left", anchor="w")

        ttk.Label(text_col, text="1. Отсканируйте QR-код камерой телефона",
                  font=("TkDefaultFont", 11)).pack(anchor="w")
        ttk.Label(text_col, text="   (или откройте ссылку ниже в браузере на компьютере)",
                  font=("TkDefaultFont", 10)).pack(anchor="w")

        self.url_var = tk.StringVar(value="")
        ttk.Label(text_col, textvariable=self.url_var, font=("TkDefaultFont", 10)).pack(anchor="w", pady=(2, 10))

        ttk.Label(text_col, text="2. Введите на этой странице код:",
                  font=("TkDefaultFont", 11)).pack(anchor="w")

        self.code_var = tk.StringVar(value="")
        ttk.Label(text_col, textvariable=self.code_var,
                  font=("TkDefaultFont", 22, "bold")).pack(anchor="w", pady=(2, 0))

        table_frame = ttk.Frame(self.root, padding=10)
        table_frame.pack(fill="both", expand=True)
        self.table_frame = table_frame

        # login_panel располагаем между info и таблицей, но по умолчанию скрыт
        self.login_panel.pack(fill="x", before=self.table_frame)
        self.login_panel.pack_forget()

        columns = ("num", "artist", "title", "album", "duration")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headers = {"num": "№", "artist": "Исполнитель", "title": "Название",
                   "album": "Альбом", "duration": "Длит."}
        widths = {"num": 40, "artist": 200, "title": 260, "album": 220, "duration": 70}
        anchors = {"num": "center", "duration": "center"}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor=anchors.get(col, "w"))
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.count_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.count_var, padding=(10, 0, 10, 8)).pack(fill="x")

    # ---------------- Потокобезопасное обновление UI ----------------
    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                self._handle_event(kind, payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_event(self, kind, payload):
        if kind == "status":
            self.status_var.set(payload)
        elif kind == "code":
            code = payload
            self.url_var.set(code.verification_url)
            self.code_var.set(code.user_code)
            self._set_qr_image(code.verification_url)
            self.login_panel.pack(fill="x", before=self.table_frame)
        elif kind == "code_clear":
            self.login_panel.pack_forget()
            self.url_var.set("")
            self.code_var.set("")
        elif kind == "login_ok":
            self.status_var.set("Авторизация выполнена. Загружаю медиатеку…")
            self.login_btn.configure(state="disabled")
            self.refresh_btn.configure(state="normal")
            self.logout_btn.configure(state="normal")
        elif kind == "login_error":
            self.status_var.set(f"Ошибка авторизации: {payload}")
            self.login_btn.configure(state="normal")
        elif kind == "tracks":
            self.tracks_data = payload
            self._fill_tree(payload)
            self.export_btn.configure(state="normal" if payload else "disabled")
            self.status_var.set("Готово")
            self.count_var.set(f"Треков в медиатеке («Мне нравится»): {len(payload)}")
        elif kind == "load_error":
            self.status_var.set(f"Ошибка загрузки медиатеки: {payload}")
        elif kind == "enable_refresh":
            self.refresh_btn.configure(state="normal")
        elif kind == "logged_out":
            self.status_var.set("Вы вышли из аккаунта")
            self.login_panel.pack_forget()
            self.url_var.set("")
            self.code_var.set("")
            self.login_btn.configure(state="normal")
            self.refresh_btn.configure(state="disabled")
            self.export_btn.configure(state="disabled")
            self.logout_btn.configure(state="disabled")
            self._fill_tree([])
            self.count_var.set("")

    def _fill_tree(self, tracks):
        self.tree.delete(*self.tree.get_children())
        for i, t in enumerate(tracks, start=1):
            self.tree.insert("", "end", values=(i, t["artist"], t["title"], t["album"], t["duration"]))

    def _set_qr_image(self, url: str, box_size: int = 220):
        """Генерирует QR-код для ссылки подтверждения и показывает его в окне."""
        qr_img = qrcode.make(url, box_size=6, border=2)
        qr_img = qr_img.convert("RGB").resize((box_size, box_size), Image.NEAREST)
        photo = ImageTk.PhotoImage(qr_img)
        self._qr_photo = photo  # без этой ссылки картинка исчезнет (сборщик мусора Python)
        self.qr_label.configure(image=photo)

    # ---------------- Авторизация ----------------
    def start_login(self):
        self.login_btn.configure(state="disabled")
        self.event_queue.put(("status", "Запрашиваю код подтверждения у Яндекса…"))
        threading.Thread(target=self._login_worker, daemon=True).start()

    def _login_worker(self):
        client = Client()

        def on_code(code):
            self.event_queue.put(("code", code))
            try:
                webbrowser.open(code.verification_url)
            except Exception:
                pass

        try:
            token = client.device_auth(on_code=on_code)
        except DeviceAuthError as e:
            self.event_queue.put(("code_clear", None))
            self.event_queue.put(("login_error", str(e)))
            return
        except Exception as e:
            self.event_queue.put(("code_clear", None))
            self.event_queue.put(("login_error", str(e)))
            return

        save_token(token.access_token)
        self.event_queue.put(("code_clear", None))
        self._start_client_with_token(token.access_token)

    def _start_client_with_token(self, token: str):
        threading.Thread(target=self._init_client_worker, args=(token,), daemon=True).start()

    def _init_client_worker(self, token: str):
        try:
            self.client = Client(token).init()
        except Exception as e:
            self.event_queue.put(("login_error", f"Не удалось подключиться: {e}"))
            clear_token()
            return
        self.event_queue.put(("login_ok", None))
        self._load_library_worker()

    def logout(self):
        clear_token()
        self.client = None
        self.tracks_data = []
        self.event_queue.put(("logged_out", None))

    # ---------------- Медиатека ----------------
    def load_library(self):
        if not self.client:
            return
        self.refresh_btn.configure(state="disabled")
        self.event_queue.put(("status", "Загружаю медиатеку…"))
        threading.Thread(target=self._load_library_worker, daemon=True).start()

    def _load_library_worker(self):
        try:
            likes = self.client.users_likes_tracks()
            short_list = likes.tracks if likes else []
            track_ids = [t.track_id for t in short_list]

            full_tracks = []
            batch_size = 100
            for i in range(0, len(track_ids), batch_size):
                batch_ids = track_ids[i:i + batch_size]
                if batch_ids:
                    full_tracks.extend(self.client.tracks(batch_ids))

            by_id = {str(t.id): t for t in full_tracks}
            ordered = []
            for short in short_list:
                t = by_id.get(str(short.id))
                if t is None:
                    continue
                artist_names = t.artists_name() or []
                ordered.append({
                    "artist": ", ".join(artist_names) if artist_names else "—",
                    "title": t.title or "—",
                    "album": t.albums[0].title if t.albums else "—",
                    "duration": ms_to_mmss(t.duration_ms),
                })
            self.event_queue.put(("tracks", ordered))
        except Exception as e:
            self.event_queue.put(("load_error", str(e)))
        finally:
            self.event_queue.put(("enable_refresh", None))

    # ---------------- Экспорт ----------------
    def export_tracks(self):
        if not self.tracks_data:
            messagebox.showinfo(APP_TITLE, "Список треков пуст.")
            return
        path = filedialog.asksaveasfilename(
            title="Сохранить список треков",
            defaultextension=".csv",
            filetypes=[("CSV файл", "*.csv"), ("Текстовый файл", "*.txt")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["№", "Исполнитель", "Название", "Альбом", "Длительность"])
                    for i, t in enumerate(self.tracks_data, start=1):
                        writer.writerow([i, t["artist"], t["title"], t["album"], t["duration"]])
            else:
                with open(path, "w", encoding="utf-8") as f:
                    for i, t in enumerate(self.tracks_data, start=1):
                        f.write(f"{i}. {t['artist']} — {t['title']} ({t['album']}) [{t['duration']}]\n")
            messagebox.showinfo(APP_TITLE, f"Сохранено: {path}")
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Не удалось сохранить файл: {e}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
