import asyncio
import os
import random
import string
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import yt_dlp

from config import TEMP_DOWNLOADS_DIR, VIDEOS_DIR


class VideoDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'ignoreerrors': False,
        }
    
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
            If error_message is not None, download failed
        """
        loop = asyncio.get_event_loop()
        
        # Get platform
        platform = self._get_platform_from_url(url)
        temp_filename = self._generate_temp_filename(platform)
        temp_filepath = TEMP_DOWNLOADS_DIR / temp_filename
        
        # Флаг для отслеживания превышения размера
        size_exceeded = False
        
        def progress_hook(d):
            """Progress hook для отслеживания размера"""
            nonlocal size_exceeded
            if d['status'] == 'downloading':
                # Проверяем размер скачанного файла
                if temp_filepath.exists():
                    current_size = temp_filepath.stat().st_size
                    if current_size > max_server_size:
                        size_exceeded = True
                        raise Exception(f"Размер превысил лимит сервера: {current_size} > {max_server_size}")
        
        # Настраиваем yt-dlp с хуком прогресса
        ydl_opts = {
            **self.ydl_opts,
            'format': 'best[ext=mp4]/best',
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
            
            return None, None, None, "Не удалось скачать видео"
            
        except Exception as e:
            # Удаляем временный файл при ошибке
            if temp_filepath.exists():
                temp_filepath.unlink()
            
            error_msg = str(e)
            if "размер превысил" in error_msg.lower() or "too large" in error_msg.lower():
                return None, None, None, f"Видео слишком большое! Максимальный размер: {max_server_size // (1024*1024)}MB"
            else:
                return None, None, None, f"Ошибка загрузки: {error_msg}"
    
    def move_to_server_storage(self, temp_filepath: str, platform: str) -> str:
        """Move file from temp to server storage"""
        final_filename = self._generate_final_filename(platform)
        final_filepath = VIDEOS_DIR / final_filename
        
        # Перемещаем файл
        Path(temp_filepath).rename(final_filepath)
        
        return final_filename


# Singleton instance
downloader = VideoDownloader()