"""
OMNI File Manager - Handle file uploads, storage, and processing
"""

import os
import uuid
import shutil
import mimetypes
from datetime import datetime
from pathlib import Path


class FileManager:
    """Manages file uploads and storage"""
    
    def __init__(self, upload_folder='/tmp/omni_uploads'):
        self.upload_folder = Path(upload_folder)
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        
        # Allowed extensions
        self.allowed_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
            'video': ['.mp4', '.webm', '.mov', '.avi'],
            'audio': ['.mp3', '.wav', '.ogg', '.m4a'],
            'document': ['.pdf', '.doc', '.docx', '.txt', '.md', '.csv', '.xlsx', '.json'],
            'code': ['.py', '.js', '.ts', '.html', '.css', '.json', '.yaml', '.yml'],
        }
    
    def save(self, file, subfolder=None):
        """Save an uploaded file"""
        if hasattr(file, 'filename'):
            # Flask FileStorage object
            filename = file.filename
            save_func = file.save
        else:
            # File path string
            filename = os.path.basename(file)
            save_func = lambda p: shutil.copy(file, p)
        
        # Generate unique filename
        ext = os.path.splitext(filename)[1].lower()
        unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
        
        # Determine save path
        if subfolder:
            save_dir = self.upload_folder / subfolder
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.upload_folder
        
        save_path = save_dir / unique_name
        
        # Save file
        save_func(str(save_path))
        
        return str(save_path)
    
    def get(self, filepath):
        """Get file info"""
        path = Path(filepath)
        
        if not path.exists():
            return None
        
        return {
            'path': str(path),
            'name': path.name,
            'extension': path.suffix,
            'size': path.stat().st_size,
            'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            'type': self._get_file_type(path.suffix)
        }
    
    def delete(self, filepath):
        """Delete a file"""
        path = Path(filepath)
        
        if path.exists():
            path.unlink()
            return True
        return False
    
    def list_files(self, subfolder=None, file_type=None):
        """List files in storage"""
        search_dir = self.upload_folder
        if subfolder:
            search_dir = search_dir / subfolder
        
        if not search_dir.exists():
            return []
        
        files = []
        for path in search_dir.iterdir():
            if path.is_file():
                info = self.get(str(path))
                if info:
                    if file_type is None or info['type'] == file_type:
                        files.append(info)
        
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    def _get_file_type(self, extension):
        """Determine file type from extension"""
        ext = extension.lower()
        for file_type, extensions in self.allowed_extensions.items():
            if ext in extensions:
                return file_type
        return 'other'
    
    def is_allowed(self, filename):
        """Check if file extension is allowed"""
        ext = os.path.splitext(filename)[1].lower()
        all_allowed = []
        for exts in self.allowed_extensions.values():
            all_allowed.extend(exts)
        return ext in all_allowed
    
    def get_size_human(self, size_bytes):
        """Convert bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def read_text(self, filepath):
        """Read text content from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return None
    
    def write_text(self, filepath, content):
        """Write text content to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except:
            return False
    
    def copy(self, src, dst):
        """Copy a file"""
        try:
            shutil.copy(src, dst)
            return True
        except:
            return False
    
    def move(self, src, dst):
        """Move a file"""
        try:
            shutil.move(src, dst)
            return True
        except:
            return False
    
    def get_mime_type(self, filepath):
        """Get MIME type of file"""
        mime_type, _ = mimetypes.guess_type(filepath)
        return mime_type or 'application/octet-stream'
    
    def cleanup_old_files(self, days=7):
        """Remove files older than specified days"""
        import time
        
        cutoff = time.time() - (days * 86400)
        removed = 0
        
        for path in self.upload_folder.rglob('*'):
            if path.is_file():
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
        
        return removed
