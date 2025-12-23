import asyncio
import os
import random
import string
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import yt_dlp
from config import USE_BROWSER_COOKIES, COOKIES_FILE, VIDEOS_DIR, TEMP_DOWNLOADS_DIR

class VideoDownloader:
    def __init__(self):
        # Пытаемся получить cookies из браузера
        cookies = None
        
        if USE_BROWSER_COOKIES:
            try:
                import browser_cookie3
                # Пробуем получить cookies из разных браузеров
                for browser in [browser_cookie3.chrome, browser_cookie3.firefox, 
                               browser_cookie3.edge, browser_cookie3.opera]:
                    try:
                        cookies = browser(domain_name='youtube.com')
                        if cookies:
                            print(f"✅ Cookies loaded from {browser.__name__}")
                            break
                    except:
                        continue
            except ImportError:
                print("⚠️ browser-cookie3 not installed, skipping browser cookies")
        
        # Параметры для yt-dlp
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
        }
        
        # Добавляем cookies если есть
        if cookies:
            try:
                # Сохраняем cookies во временный файл
                import tempfile
                import pickle
                
                temp_cookie_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
                for cookie in cookies:
                    if cookie.name and cookie.value:
                        temp_cookie_file.write(f"{cookie.domain}\tTRUE\t{cookie.path}\t{cookie.secure}\t{cookie.expires}\t{cookie.name}\t{cookie.value}\n".encode())
                temp_cookie_file.close()
                
                self.ydl_opts['cookiefile'] = temp_cookie_file.name
                self.temp_cookie_file = temp_cookie_file.name
            except Exception as e:
                print(f"⚠️ Error loading cookies: {e}")
                self.temp_cookie_file = None
        elif COOKIES_FILE and os.path.exists(COOKIES_FILE):
            self.ydl_opts['cookiefile'] = COOKIES_FILE
    
    def __del__(self):
        """Очистка временных файлов cookies"""
        if hasattr(self, 'temp_cookie_file') and self.temp_cookie_file and os.path.exists(self.temp_cookie_file):
            try:
                os.unlink(self.temp_cookie_file)
            except:
                pass
    
    def _generate_temp_filename(self, platform: str) -> str:
        """Generate unique temporary filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"temp_{platform}_{timestamp}_{random_str}.mp4"
    
    def _generate_final_filename(self, platform: str) -> str:
        """Generate final filename for server storage"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{platform}_{timestamp}_{random_str}.mp4"
    
    def _get_platform_from_url(self, url: str) -> str:
        """Detect platform from URL"""
        url_lower = url.lower()
        if 'instagram.com' in url_lower:
            return 'instagram'
        elif 'tiktok.com' in url_lower or 'vt.tiktok.com' in url_lower:
            return 'tiktok'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        return 'unknown'
    
    async def download_with_size_check(
        self, 
        url: str, 
        max_server_size: int
    ) -> Tuple[Optional[str], Optional[Dict], Optional[str], Optional[str]]:
        """
        Download video with real-time size checking
        
        Returns:
            (temp_filepath, video_info, platform, error_message)
        """
        loop = asyncio.get_event_loop()
        platform = self._get_platform_from_url(url)
        temp_filename = self._generate_temp_filename(platform)
        temp_filepath = TEMP_DOWNLOADS_DIR / temp_filename
        
        # Флаг для отслеживания превышения размера
        size_exceeded = False
        
        def progress_hook(d):
            """Progress hook для отслеживания размера"""
            nonlocal size_exceeded
            if d['status'] == 'downloading':
                if temp_filepath.exists():
                    current_size = temp_filepath.stat().st_size
                    if current_size > max_server_size:
                        size_exceeded = True
                        raise Exception(f"Размер превысил лимит сервера: {current_size} > {max_server_size}")
        
        # Пробуем разные форматы
        formats_to_try = [
            'best[ext=mp4]',
            'best',
            'worst',  # Иногда маленькие файлы работают лучше
        ]
        
        for format_spec in formats_to_try:
            ydl_opts = {
                **self.ydl_opts,
                'format': format_spec,
                'outtmpl': str(temp_filepath),
                'progress_hooks': [progress_hook],
                'noprogress': True,
            }
            
            try:
                def download():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(url, download=True)
                
                info = await loop.run_in_executor(None, download)
                
                # Проверяем, не был ли превышен размер
                if size_exceeded:
                    if temp_filepath.exists():
                        temp_filepath.unlink()
                    return None, None, None, f"Видео слишком большое! Максимальный размер: {max_server_size // (1024*1024)}MB"
                
                # Проверяем итоговый размер
                if temp_filepath.exists():
                    final_size = temp_filepath.stat().st_size
                    if final_size > max_server_size:
                        temp_filepath.unlink()
                        return None, None, None, f"Видео слишком большое! Размер: {final_size // (1024*1024)}MB, лимит: {max_server_size // (1024*1024)}MB"
                    
                    return str(temp_filepath), info, platform, None
                    
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ Download attempt failed with format {format_spec}: {error_msg}")
                
                # Удаляем временный файл если есть
                if temp_filepath.exists():
                    temp_filepath.unlink()
                
                # Пробуем следующий формат
                continue
        
        # Если все форматы не сработали
        return None, None, None, "Не удалось скачать видео. YouTube может блокировать запросы."

# Singleton instance
downloader = VideoDownloader()
