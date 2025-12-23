import os
from pathlib import Path

# ========== TELEGRAM BOT ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8533413936:AAF597F9RSqjnv4AU05YZILETXaUsRGhHks")

# ========== ADMIN SETTINGS ==========
ADMIN_IDS = [384368691]  # Замените на ваш Telegram ID

# ========== FILE SERVER ==========
FILE_SERVER_HOST = os.getenv("FILE_SERVER_HOST", "0.0.0.0")
FILE_SERVER_PORT = int(os.getenv("FILE_SERVER_PORT", "8000"))
FILE_SERVER_URL = os.getenv("FILE_SERVER_URL", f"http://localhost:{FILE_SERVER_PORT}")

# ========== PATHS ==========
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
VIDEOS_DIR = TEMP_DIR / "videos"
TEMP_DOWNLOADS_DIR = TEMP_DIR / "downloads"
LINKS_DB = TEMP_DIR / "links.json"

# ========== DEFAULT SETTINGS ==========
DEFAULT_MAX_SERVER_SIZE = 500 * 1024 * 1024  # 500MB - максимальный размер для сервера
DEFAULT_MAX_CHAT_SIZE = 50 * 1024 * 1024  # 50MB - максимальный размер для отправки в чат
DEFAULT_LINK_EXPIRE_MINUTES = 60  # 1 час

# ========== ALLOWED DOMAINS ==========
ALLOWED_DOMAINS = [
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com"
]

# ========== CREATE DIRECTORIES ==========
TEMP_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)
TEMP_DOWNLOADS_DIR.mkdir(exist_ok=True)

# ========== COOKIES SETTINGS ==========
USE_BROWSER_COOKIES = True  # Автоматически использовать cookies из браузера
COOKIES_FILE = None  # Или путь к файлу cookies.txt