import json
import os
from pathlib import Path
import sys


# Это дело ИИ
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(sys._MEIPASS)
else:
    APP_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = APP_DIR

DATA_DIR = Path(os.environ.get("LYCEUM_CHAT_DATA_DIR", APP_DIR))
SETTINGS_FILE = DATA_DIR / "settings.json"
DATABASE_FILE = DATA_DIR / "chats.sqlite3"

# Для запроса к RouterAI
MINI_MODEL = "openai/gpt-4o-mini"
NANO_MODEL = "openai/gpt-5-nano"
LUNA_MODEL = "openai/gpt-6-luna"
DEFAULT_MODEL = MINI_MODEL


# Возвращение пути к файлу (это делал ИИ)
def resource_path(name):
    return str(RESOURCE_DIR / name)


# Создаёт папку для настроек и базы данных, если её ещё нет (это делал ИИ)
def prepare_data_folder():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Прочитывает ключ и выбранную модель из файла настроек
# Есть недоработка: повреждённый JSON-файл не восстанавливается автоматически
# Это делал ИИ
def load_settings():
    prepare_data_folder()
    result = {"api_key": "", "model": DEFAULT_MODEL}
    if SETTINGS_FILE.exists():
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(saved, dict):
            raise ValueError("В settings.json должен быть объект JSON.")
        if isinstance(saved.get("api_key"), str):
            result["api_key"] = saved["api_key"].strip()
        if saved.get("model") in (MINI_MODEL, NANO_MODEL, LUNA_MODEL):
            result["model"] = saved["model"]
    return result


# Лоудит настройки в JSON-файл (то есть записывает их)
def save_settings(settings):
    prepare_data_folder()
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
