def __init__(self):
    self.ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'ignoreerrors': True,
    }