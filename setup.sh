#!/bin/bash

# Скрипт установки Video Downloader Bot

echo "🎬 Установка Video Downloader Bot"
echo "================================"

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python3 и повторите попытку."
    exit 1
fi

# Создание виртуального окружения
echo "🔧 Создание виртуального окружения..."
python3 -m venv venv

# Активация окружения
echo "🔧 Активация окружения..."
source venv/bin/activate

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Установка FFmpeg (предупреждение)
echo "⚠️  Убедитесь, что FFmpeg установлен:"
echo "   Ubuntu/Debian: sudo apt install ffmpeg"
echo "   macOS: brew install ffmpeg"
echo "   Windows: https://ffmpeg.org/download.html"

# Создание конфигурационного файла
echo "⚙️  Настройка конфигурации..."
read -p "Введите токен Telegram бота: " token
read -p "Введите ваш Telegram ID (для админки): " admin_id

cat > config.py << EOF
import os
from pathlib import Path

# Telegram Bot Token
TELEGRAM_TOKEN = "$token"

# Admin Settings
ADMIN_IDS = [$admin_id]

# File Server Configuration
FILE_SERVER_HOST = "0.0.0.0"
FILE_SERVER_PORT = 8000
FILE_SERVER_URL = f"http://localhost:{FILE_SERVER_PORT}"

# Paths
BASE_DIR = Path(__file__).parent
TEMP_DIR = BASE_DIR / "temp"
VIDEOS_DIR = TEMP_DIR / "videos"
TEMP_DOWNLOADS_DIR = TEMP_DIR / "downloads"
LINKS_DB = TEMP_DIR / "links.json"

# Default settings
DEFAULT_MAX_SERVER_SIZE = 500 * 1024 * 1024  # 500MB
DEFAULT_MAX_CHAT_SIZE = 50 * 1024 * 1024  # 50MB
DEFAULT_LINK_EXPIRE_MINUTES = 60  # 1 hour

# Allowed domains
ALLOWED_DOMAINS = [
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com"
]

# Create directories
TEMP_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)
TEMP_DOWNLOADS_DIR.mkdir(exist_ok=True)
EOF

echo "✅ Установка завершена!"
echo ""
echo "📋 Инструкции по запуску:"
echo "1. Активируйте окружение: source venv/bin/activate"
echo "2. Запустите бота: python main.py"
echo "3. Откройте Telegram и найдите вашего бота"
echo ""
echo "🔧 Дополнительные настройки в файле config.py"