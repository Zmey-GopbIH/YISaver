import os
from pathlib import Path
from typing import Dict
from config import ADMIN_IDS

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import DEFAULT_MAX_CHAT_SIZE, DEFAULT_MAX_SERVER_SIZE, FILE_SERVER_URL, VIDEOS_DIR, ALLOWED_DOMAINS
from bot.downloader import downloader
from bot.file_server import file_server
from bot.utils import format_size, is_valid_url

# User settings storage
USER_SETTINGS: Dict[int, dict] = {}  # user_id -> {'max_server_size': int, 'link_expire': int}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
    🎬 *Video Downloader Bot*
    
    📥 *Поддерживаемые платформы:*
    • Instagram (Reels, Posts)
    • YouTube (Shorts, Videos)
    • TikTok (все видео)
    
    📤 *Как использовать:*
    1. Отправьте ссылку на видео
    2. Бот скачает и отправит вам видео
    
    ⚙️ *Настройки:*
    /settings - настройки максимального размера и времени жизни ссылок
    
    ⚠️ *Ограничения:*
    • Видео до 50MB отправляются напрямую
    • Большие видео сохраняются на сервере с временной ссылкой
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
    📖 *Справка*
    
    *Поддерживаемые ссылки:*
    • Instagram: https://www.instagram.com/reel/.../
    • Instagram: https://www.instagram.com/p/.../
    • YouTube: https://youtube.com/shorts/...
    • YouTube: https://youtube.com/watch?v=...
    • TikTok: https://www.tiktok.com/@.../video/...
    • TikTok: https://vm.tiktok.com/...
    
    *Команды:*
    /start - начало работы
    /settings - настройки
    /help - эта справка
    
    *Особенности:*
    • Большие видео (>50MB) сохраняются на сервере
    • Ссылки на скачивание действительны ограниченное время
    • Файлы автоматически удаляются после истечения срока
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    user_id = update.effective_user.id
    user_settings = USER_SETTINGS.get(user_id, {})
    
    current_server_size = user_settings.get('max_server_size', DEFAULT_MAX_SERVER_SIZE)
    current_expire = user_settings.get('link_expire', 60)
    
    keyboard = [
        [
            InlineKeyboardButton("Лимит сервера", callback_data="menu_server_size"),
            InlineKeyboardButton("Время ссылок", callback_data="menu_expire"),
        ],
        [
            InlineKeyboardButton("Текущие настройки", callback_data="show_current"),
            InlineKeyboardButton("Сбросить", callback_data="reset_settings"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"⚙️ *Настройки*\n\n"
        f"*Текущие значения:*\n"
        f"• Макс. размер для сервера: {format_size(current_server_size)}\n"
        f"• Время жизни ссылок: {current_expire} мин.\n\n"
        f"*Примечания:*\n"
        f"• Видео ≤50MB отправляются в чат\n"
        f"• Видео >50MB сохраняются на сервер\n"
        f"• Если видео превышает лимит сервера, загрузка прерывается\n\n"
        f"Выберите категорию для настройки:"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_server_size":
        await show_server_size_menu(query)
    elif data == "menu_expire":
        await show_expire_menu(query)
    elif data == "show_current":
        await show_current_settings(query)
    elif data == "reset_settings":
        await reset_settings(query)
    elif data.startswith("server_size_"):
        await set_server_size(query, data)
    elif data.startswith("expire_"):
        await set_expire(query, data)
    elif data == "back_to_menu":
        await settings_edit(query)


async def show_server_size_menu(query):
    """Show server size selection menu"""
    keyboard = [
        [
            InlineKeyboardButton("100MB", callback_data="server_size_100"),
            InlineKeyboardButton("200MB", callback_data="server_size_200"),
            InlineKeyboardButton("500MB", callback_data="server_size_500"),
        ],
        [
            InlineKeyboardButton("1GB", callback_data="server_size_1024"),
            InlineKeyboardButton("2GB", callback_data="server_size_2048"),
            InlineKeyboardButton("5GB", callback_data="server_size_5120"),
        ],
        [
            InlineKeyboardButton("Назад", callback_data="back_to_menu"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📏 *Выберите максимальный размер видео для сервера:*\n\n"
        "Если видео превысит этот размер во время загрузки, загрузка будет прервана.\n"
        "Видео до 50MB отправляются в чат, видео больше 50MB сохраняются на сервере.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def show_expire_menu(query):
    """Show expiration time menu"""
    keyboard = [
        [
            InlineKeyboardButton("15 мин", callback_data="expire_15"),
            InlineKeyboardButton("30 мин", callback_data="expire_30"),
            InlineKeyboardButton("60 мин", callback_data="expire_60"),
        ],
        [
            InlineKeyboardButton("3 часа", callback_data="expire_180"),
            InlineKeyboardButton("6 часов", callback_data="expire_360"),
            InlineKeyboardButton("12 часов", callback_data="expire_720"),
        ],
        [
            InlineKeyboardButton("24 часа", callback_data="expire_1440"),
            InlineKeyboardButton("Назад", callback_data="back_to_menu"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⏰ *Выберите время жизни ссылок:*\n\n"
        "Ссылки на скачивание больших видео будут активны указанное время.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def show_current_settings(query):
    """Show current settings"""
    user_id = query.from_user.id
    user_settings = USER_SETTINGS.get(user_id, {})
    
    current_server_size = user_settings.get('max_server_size', DEFAULT_MAX_SERVER_SIZE)
    current_expire = user_settings.get('link_expire', 60)
    
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
    ⚙️ *Текущие настройки:*
    
    *Лимит сервера:*
    • Максимальный размер: {format_size(current_server_size)}
    • Видео больше этого размера не будут скачаны
    
    *Время жизни ссылок:*
    • Ссылки действительны: {current_expire} минут
    • После истечения времени файлы удаляются автоматически
    
    *Примечание:*
    • Видео до 50MB отправляются в чат Telegram
    • Видео от 50MB до лимита сервера сохраняются на сервере
    
    *Сервер:*
    • Файлы хранятся на: {FILE_SERVER_URL}
    """
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def reset_settings(query):
    """Reset user settings"""
    user_id = query.from_user.id
    if user_id in USER_SETTINGS:
        del USER_SETTINGS[user_id]
    
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✅ Настройки сброшены к значениям по умолчанию!",
        reply_markup=reply_markup
    )


async def set_server_size(query, data):
    """Set server size limit"""
    user_id = query.from_user.id
    size_mb = int(data.split("_")[2])
    
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {}
    
    USER_SETTINGS[user_id]['max_server_size'] = size_mb * 1024 * 1024
    
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Лимит сервера установлен: *{size_mb}MB*\n\n"
        f"Видео больше {size_mb}MB не будут скачаны.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def set_expire(query, data):
    """Set link expiration time"""
    user_id = query.from_user.id
    minutes = int(data.split("_")[1])
    
    if user_id not in USER_SETTINGS:
        USER_SETTINGS[user_id] = {}
    
    USER_SETTINGS[user_id]['link_expire'] = minutes
    
    keyboard = [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Время жизни ссылок установлено: *{minutes} минут*\n\n"
        f"Ссылки на скачивание будут активны {minutes} минут.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def settings_edit(query):
    """Edit settings message"""
    user_id = query.from_user.id
    user_settings = USER_SETTINGS.get(user_id, {})
    
    current_server_size = user_settings.get('max_server_size', DEFAULT_MAX_SERVER_SIZE)
    current_expire = user_settings.get('link_expire', 60)
    
    keyboard = [
        [
            InlineKeyboardButton("Лимит сервера", callback_data="menu_server_size"),
            InlineKeyboardButton("Время ссылок", callback_data="menu_expire"),
        ],
        [
            InlineKeyboardButton("Текущие настройки", callback_data="show_current"),
            InlineKeyboardButton("Сбросить", callback_data="reset_settings"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
    ⚙️ *Настройки*
    
    *Текущие значения:*
    • Макс. размер для сервера: {format_size(current_server_size)}
    • Время жизни ссылок: {current_expire} мин.
    
    Выберите категорию для настройки:
    """
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video URL message - НОВАЯ ЛОГИКА"""
    url = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Validate URL
    if not is_valid_url(url):
        await update.message.reply_text(
            "❌ *Неверная ссылка*\n\n"
            "Пожалуйста, отправьте корректную ссылку на видео из:\n"
            "• Instagram\n• YouTube\n• TikTok",
            parse_mode='Markdown'
        )
        return
    
    # Check if domain is allowed
    if not any(domain in url.lower() for domain in ALLOWED_DOMAINS):
        await update.message.reply_text(
            "❌ *Платформа не поддерживается*\n\n"
            "Поддерживаемые платформы:\n"
            "• Instagram (instagram.com)\n"
            "• YouTube (youtube.com, youtu.be)\n"
            "• TikTok (tiktok.com, vm.tiktok.com)",
            parse_mode='Markdown'
        )
        return
    
    # Get user settings
    user_settings = USER_SETTINGS.get(user_id, {})
    max_server_size = user_settings.get('max_server_size', DEFAULT_MAX_SERVER_SIZE)
    link_expire = user_settings.get('link_expire', 60)
    
    # Send status message
    status_msg = await update.message.reply_text(
        "🔍 *Анализирую ссылку...*\n"
        f"⚠️ Лимит сервера: {format_size(max_server_size)}",
        parse_mode='Markdown'
    )
    
    try:
        # Скачиваем с проверкой размера
        await status_msg.edit_text(
            "📥 *Скачиваю видео...*\n"
            f"⏳ Проверяю размер (макс. {max_server_size // (1024*1024)}MB)...",
            parse_mode='Markdown'
        )
        
        temp_filepath, info, platform, error = await downloader.download_with_size_check(
            url, max_server_size
        )
        
        if error:
            await status_msg.edit_text(
                f"❌ *Ошибка:* {error}\n\n"
                "Попробуйте уменьшить лимит в /settings или выберите другое видео.",
                parse_mode='Markdown'
            )
            return
        
        if not temp_filepath or not info:
            await status_msg.edit_text(
                "❌ Не удалось скачать видео.\n"
                "Возможно, видео приватное или платформа заблокировала запрос.",
                parse_mode='Markdown'
            )
            return
        
        # Получаем реальный размер файла
        file_size = Path(temp_filepath).stat().st_size
        
        # Определяем платформу для подписи
        platform_names = {
            'instagram': 'Instagram 📸',
            'youtube': 'YouTube ▶️',
            'tiktok': 'TikTok 🎵',
            'unknown': 'Видео 📹'
        }
        
        platform_display = platform_names.get(platform, 'Видео 📹')
        
        # РЕШАЕМ: отправлять в чат или на сервер
        if file_size <= DEFAULT_MAX_CHAT_SIZE:
            # Отправляем в чат Telegram
            await status_msg.edit_text(
                "✅ *Видео скачано!*\n"
                f"📏 Размер: {format_size(file_size)}\n"
                "📤 Отправляю в Telegram...",
                parse_mode='Markdown'
            )
            
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action='upload_video'
            )
            
            # Создаем подпись
            caption = f"{platform_display}\n"
            if info.get('title'):
                title = info['title'][:100] + "..." if len(info['title']) > 100 else info['title']
                caption += f"📝 {title}\n"
            caption += f"📊 Размер: {format_size(file_size)}"
            
            # Отправляем видео
            try:
                with open(temp_filepath, 'rb') as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption=caption,
                        supports_streaming=True,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60
                    )
                
                # Удаляем временный файл
                Path(temp_filepath).unlink()
                
                await status_msg.delete()
                
            except Exception as e:
                await status_msg.edit_text(
                    f"❌ *Ошибка отправки в Telegram:*\n`{str(e)[:200]}`\n\n"
                    "Попробуйте еще раз.",
                    parse_mode='Markdown'
                )
                if Path(temp_filepath).exists():
                    Path(temp_filepath).unlink()
                return
                
        else:
            # Сохраняем на сервере и отправляем ссылку
            await status_msg.edit_text(
                f"✅ *Видео скачано!*\n"
                f"📏 Размер: {format_size(file_size)}\n"
                f"💾 Сохраняю на сервер...",
                parse_mode='Markdown'
            )
            
            # Перемещаем файл в постоянное хранилище
            try:
                final_filename = downloader.move_to_server_storage(temp_filepath, platform)
                final_filepath = VIDEOS_DIR / final_filename
                
                # Проверяем, что файл существует
                if not final_filepath.exists():
                    await status_msg.edit_text("❌ Ошибка при сохранении файла на сервер")
                    return
                
                # Генерируем ссылку
                download_link = file_server.generate_link(final_filename, link_expire)
                full_url = f"{FILE_SERVER_URL}{download_link}"
                
                # Создаем клавиатуру с кнопкой
                keyboard = [
                    [InlineKeyboardButton("📥 Скачать видео", url=full_url)],
                    [InlineKeyboardButton("ℹ️ Информация о ссылке", 
                      callback_data=f"link_info_{download_link.split('/')[-1]}")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Формируем сообщение
                message_text = (
                    f"✅ *Видео сохранено на сервере!*\n\n"
                    f"📹 *Платформа:* {platform_display}\n"
                    f"📏 *Размер:* {format_size(file_size)}\n"
                    f"⏰ *Срок хранения:* {link_expire} минут\n"
                    f"📁 *Имя файла:* `{final_filename}`\n\n"
                    f"🔗 *Ссылка для скачивания:*\n`{full_url}`\n\n"
                    f"⚠️ *Ссылка действительна {link_expire} минут*"
                )
                
                if info.get('title'):
                    title = info['title'][:150] + "..." if len(info['title']) > 150 else info['title']
                    message_text = f"📝 *{title}*\n\n" + message_text
                
                await status_msg.edit_text(
                    message_text, 
                    parse_mode='Markdown', 
                    reply_markup=reply_markup
                )
                
            except Exception as e:
                await status_msg.edit_text(
                    f"❌ *Ошибка при сохранении на сервере:*\n`{str(e)[:200]}`",
                    parse_mode='Markdown'
                )
                # Удаляем временный файл, если он еще существует
                if Path(temp_filepath).exists():
                    Path(temp_filepath).unlink()
                return
    
    except Exception as e:
        print(f"Error processing video: {e}")
        await status_msg.edit_text(
            f"❌ *Критическая ошибка обработки видео*\n\n"
            f"Техническая информация:\n`{str(e)[:200]}`\n\n"
            f"Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
            parse_mode='Markdown'
        )
        # Удаляем временный файл, если он существует
        if 'temp_filepath' in locals() and temp_filepath and Path(temp_filepath).exists():
            Path(temp_filepath).unlink()


async def link_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle link info callback"""
    query = update.callback_query
    await query.answer()
    
    link_id = query.data.replace("link_info_", "")
    
    try:
        # Get link info from file server
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{FILE_SERVER_URL}/info/{link_id}") as response:
                if response.status == 200:
                    info = await response.json()
                    
                    text = (
                        f"ℹ️ *Информация о ссылке*\n\n"
                        f"📁 *Файл:* `{info['filename']}`\n"
                        f"🕐 *Создано:* {info['created_at']}\n"
                        f"⏰ *Истекает:* {info['expires_at']}\n"
                        f"📊 *Скачиваний:* {info['downloads']}\n"
                        f"⏳ *Осталось:* {info['expires_in_minutes']} минут"
                    )
                    
                    await query.edit_message_text(text, parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ Ссылка не найдена или истекла")
    
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка получения информации: {str(e)}")


async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cleanup expired files (admin command)"""
    
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Эта команда только для администраторов")
        return
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{FILE_SERVER_URL}/cleanup") as response:
                if response.status == 200:
                    result = await response.json()
                    await update.message.reply_text(
                        f"🧹 *Очистка завершена*\n\n"
                        f"Удалено ссылок: {result['removed']}\n"
                        f"Осталось ссылок: {result['remaining']}",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text("❌ Ошибка при очистке")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


def setup_handlers(application):
    """Setup all handlers"""
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("cleanup", cleanup_command))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^(menu_|show_|reset_|server_size_|expire_|back_to_menu)"))
    application.add_handler(CallbackQueryHandler(link_info_callback, pattern="^link_info_"))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_url))