FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p temp/downloads temp/videos

# Установка переменных окружения
ENV TELEGRAM_TOKEN=your_bot_token_here
ENV FILE_SERVER_HOST=0.0.0.0
ENV FILE_SERVER_PORT=8000
ENV PYTHONUNBUFFERED=1

# Открытие порта
EXPOSE 8000

# Запуск приложения
CMD ["python", "main.py"]