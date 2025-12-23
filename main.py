import asyncio
import threading
from multiprocessing import Process

from telegram.ext import Application

from config import TELEGRAM_TOKEN, FILE_SERVER_HOST, FILE_SERVER_PORT
from bot.handlers import setup_handlers
from bot.file_server import file_server


def run_file_server():
    """Run file server in separate process"""
    import uvicorn
    uvicorn.run(
        file_server.app,
        host=FILE_SERVER_HOST,
        port=FILE_SERVER_PORT,
        log_level="info"
    )


async def run_bot():
    """Run Telegram bot"""
    # Create Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Setup handlers
    setup_handlers(application)
    
    # Start bot
    print("🤖 Telegram bot is starting...")
    print(f"🌐 File server URL: http://{FILE_SERVER_HOST}:{FILE_SERVER_PORT}")
    print(f"📁 Videos directory: temp/videos/")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep running
    await asyncio.Event().wait()


def main():
    """Main function"""
    import sys
    import os
    from threading import Thread
    
    # Add current directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Запускаем файловый сервер в отдельном потоке
        from bot.file_server import file_server
        
        def run_server():
            import uvicorn
            from config import FILE_SERVER_HOST, FILE_SERVER_PORT
            
            print(f"🌐 Запуск файлового сервера на {FILE_SERVER_HOST}:{FILE_SERVER_PORT}")
            uvicorn.run(
                file_server.app,
                host=FILE_SERVER_HOST,
                port=FILE_SERVER_PORT,
                log_level="info"
            )
        
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Ждем немного для запуска сервера
        import time
        time.sleep(2)
        
        print(f"✅ Файловый сервер запущен: {FILE_SERVER_URL}")
        
    except Exception as e:
        print(f"⚠️ Не удалось запустить файловый сервер: {e}")
        print("⚠️ Ссылки для скачивания больших видео работать не будут!")
    
    # Запускаем бота
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")

if __name__ == '__main__':
    main()
