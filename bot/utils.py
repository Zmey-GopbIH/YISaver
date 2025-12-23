import re
from urllib.parse import urlparse


def format_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except:
        return ""


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    return filename


def get_platform_icon(platform: str) -> str:
    """Get platform icon"""
    icons = {
        'instagram': '📸',
        'youtube': '▶️',
        'tiktok': '🎵',
        'unknown': '📹'
    }
    return icons.get(platform, '📹')