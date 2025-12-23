import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import VIDEOS_DIR, LINKS_DB, DEFAULT_LINK_EXPIRE_MINUTES


class FileServer:
    def __init__(self):
        self.app = FastAPI(title="Video File Server")
        self._setup_routes()
        self.links: Dict[str, dict] = self._load_links()
    
    def _load_links(self) -> Dict[str, dict]:
        """Load links from JSON file"""
        if LINKS_DB.exists():
            with open(LINKS_DB, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_links(self):
        """Save links to JSON file"""
        with open(LINKS_DB, 'w') as f:
            json.dump(self.links, f, indent=2)
    
    def _cleanup_expired_links(self):
        """Remove expired links and delete files"""
        current_time = time.time()
        expired_links = []
        
        for link_id, link_data in list(self.links.items()):
            if link_data['expires_at'] < current_time:
                expired_links.append(link_id)
                # Delete file if exists
                file_path = VIDEOS_DIR / link_data['filename']
                if file_path.exists():
                    file_path.unlink()
        
        for link_id in expired_links:
            del self.links[link_id]
        
        if expired_links:
            self._save_links()
    
    def generate_link(self, filename: str, expire_minutes: int = DEFAULT_LINK_EXPIRE_MINUTES) -> str:
        """Generate download link for file"""
        self._cleanup_expired_links()
        
        # Create unique link ID
        link_id = hashlib.md5(f"{filename}{time.time()}".encode()).hexdigest()[:12]
        
        # Store link info
        self.links[link_id] = {
            'filename': filename,
            'created_at': time.time(),
            'expires_at': time.time() + (expire_minutes * 60),
            'downloads': 0
        }
        
        self._save_links()
        return f"/download/{link_id}"
    
    def get_file_info(self, link_id: str) -> Optional[dict]:
        """Get file info by link ID"""
        self._cleanup_expired_links()
        
        if link_id not in self.links:
            return None
        
        link_data = self.links[link_id]
        
        # Update download count
        link_data['downloads'] += 1
        self._save_links()
        
        return link_data
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            return {"status": "File server is running"}
        
        @self.app.get("/download/{link_id}")
        async def download_file(link_id: str):
            """Download file by link ID"""
            file_info = self.get_file_info(link_id)
            
            if not file_info:
                raise HTTPException(status_code=404, detail="Link expired or invalid")
            
            file_path = VIDEOS_DIR / file_info['filename']
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            # Return file for download
            return FileResponse(
                path=file_path,
                filename=file_info['filename'],
                media_type='application/octet-stream'
            )
        
        @self.app.get("/info/{link_id}")
        async def get_link_info(link_id: str):
            """Get link information"""
            file_info = self.get_file_info(link_id)
            
            if not file_info:
                raise HTTPException(status_code=404, detail="Link expired or invalid")
            
            return {
                "filename": file_info['filename'],
                "created_at": datetime.fromtimestamp(file_info['created_at']).isoformat(),
                "expires_at": datetime.fromtimestamp(file_info['expires_at']).isoformat(),
                "downloads": file_info['downloads'],
                "expires_in_minutes": int((file_info['expires_at'] - time.time()) / 60)
            }
        
        @self.app.delete("/cleanup")
        async def cleanup_files():
            """Cleanup expired files (admin endpoint)"""
            old_count = len(self.links)
            self._cleanup_expired_links()
            new_count = len(self.links)
            
            return {
                "removed": old_count - new_count,
                "remaining": new_count
            }
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run file server"""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)


# Singleton instance
file_server = FileServer()