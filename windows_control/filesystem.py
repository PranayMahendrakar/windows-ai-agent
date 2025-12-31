"""
Windows AI Agent - File System Control
Cross-platform file operations with Windows-specific enhancements
"""
import os
import shutil
import glob
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class FileSystemController:
    """
    File System Controller
    Handles all file and directory operations with safety checks
    """
    
    def __init__(
        self,
        protected_paths: List[str] = None,
        allowed_paths: List[str] = None,
    ):
        self.protected_paths = protected_paths or [
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\Program Files (x86)",
        ]
        self.allowed_paths = allowed_paths or [
            os.path.expanduser("~"),
        ]
        self._snapshots: Dict[str, Dict] = {}  # For rollback
    
    def _is_path_safe(self, path: str) -> tuple[bool, str]:
        """Check if path is safe to access"""
        path = os.path.abspath(path)
        
        # Check protected paths
        for protected in self.protected_paths:
            if path.lower().startswith(protected.lower()):
                return False, f"Path is protected: {protected}"
        
        return True, ""
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for the current OS"""
        # Expand user directory
        path = os.path.expanduser(path)
        # Expand environment variables
        path = os.path.expandvars(path)
        # Normalize
        path = os.path.normpath(path)
        return path
    
    # === Read Operations ===
    
    def read_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """Read file contents"""
        path = self._normalize_path(path)
        
        safe, msg = self._is_path_safe(path)
        if not safe:
            return {"error": msg}
        
        try:
            if not os.path.exists(path):
                return {"error": f"File not found: {path}"}
            
            if not os.path.isfile(path):
                return {"error": f"Not a file: {path}"}
            
            # Check file size
            size = os.path.getsize(path)
            if size > 10 * 1024 * 1024:  # 10MB limit
                return {"error": f"File too large: {size} bytes"}
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "result": {
                    "content": content,
                    "path": path,
                    "size": size,
                    "encoding": encoding,
                }
            }
        except UnicodeDecodeError:
            return {"error": f"Cannot read file as {encoding}, try binary mode"}
        except Exception as e:
            return {"error": str(e)}
    
    def read_file_binary(self, path: str) -> Dict[str, Any]:
        """Read file as binary"""
        path = self._normalize_path(path)
        
        safe, msg = self._is_path_safe(path)
        if not safe:
            return {"error": msg}
        
        try:
            with open(path, 'rb') as f:
                content = f.read()
            
            return {
                "result": {
                    "content_base64": content.hex(),
                    "path": path,
                    "size": len(content),
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def list_directory(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
        include_hidden: bool = False,
    ) -> Dict[str, Any]:
        """List directory contents"""
        path = self._normalize_path(path)
        
        safe, msg = self._is_path_safe(path)
        if not safe:
            return {"error": msg}
        
        try:
            if not os.path.exists(path):
                return {"error": f"Directory not found: {path}"}
            
            if not os.path.isdir(path):
                return {"error": f"Not a directory: {path}"}
            
            items = []
            
            if recursive:
                search_pattern = os.path.join(path, "**", pattern)
                matches = glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = os.path.join(path, pattern)
                matches = glob.glob(search_pattern)
            
            for item_path in matches:
                name = os.path.basename(item_path)
                
                # Skip hidden files if not requested
                if not include_hidden and name.startswith('.'):
                    continue
                
                is_dir = os.path.isdir(item_path)
                stat = os.stat(item_path)
                
                items.append({
                    "name": name,
                    "path": item_path,
                    "is_directory": is_dir,
                    "size": stat.st_size if not is_dir else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                })
            
            return {
                "result": {
                    "path": path,
                    "items": items,
                    "count": len(items),
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed file/directory information"""
        path = self._normalize_path(path)
        
        try:
            if not os.path.exists(path):
                return {"error": f"Path not found: {path}"}
            
            stat = os.stat(path)
            is_dir = os.path.isdir(path)
            
            info = {
                "path": path,
                "name": os.path.basename(path),
                "is_directory": is_dir,
                "is_file": os.path.isfile(path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            }
            
            # Add extension for files
            if not is_dir:
                info["extension"] = os.path.splitext(path)[1]
            
            return {"result": info}
        except Exception as e:
            return {"error": str(e)}
    
    def search_files(
        self,
        path: str,
        pattern: str,
        content_search: str = None,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        """Search for files by name pattern and optionally content"""
        path = self._normalize_path(path)
        
        safe, msg = self._is_path_safe(path)
        if not safe:
            return {"error": msg}
        
        try:
            results = []
            search_pattern = os.path.join(path, "**", pattern)
            
            for file_path in glob.glob(search_pattern, recursive=True):
                if len(results) >= max_results:
                    break
                
                if os.path.isfile(file_path):
                    match_info = {
                        "path": file_path,
                        "name": os.path.basename(file_path),
                        "size": os.path.getsize(file_path),
                    }
                    
                    # Content search if specified
                    if content_search:
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if content_search.lower() in content.lower():
                                    match_info["content_match"] = True
                                    results.append(match_info)
                        except:
                            pass
                    else:
                        results.append(match_info)
            
            return {
                "result": {
                    "matches": results,
                    "count": len(results),
                    "search_path": path,
                    "pattern": pattern,
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    # === Write Operations ===
    
    def write_file(
        self,
        path: str,
        content: str,
        mode: str = "write",  # write, append
        encoding: str = "utf-8",
        create_dirs: bool = True,
    ) -> Dict[str, Any]:
        """Write content to file"""
        path = self._normalize_path(path)
        
        safe, msg = self._is_path_safe(path)
        if not safe:
            return {"error": msg}
        
        try:
            # Create snapshot for rollback
            existed = os.path.exists(path)
            old_content = None
            if existed and os.path.isfile(path):
                with open(path, 'r', encoding=encoding, errors='ignore') as f:
                    old_content = f.read()
            
            # Create directories if needed
            if create_dirs:
                os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Write file
            file_mode = 'a' if mode == "append" else 'w'
            with open(path, file_mode, encoding=encoding) as f:
                f.write(content)
            
            side_effects = [{
                "type": "file_modified" if existed else "file_created",
                "path": path,
                "reversible": True,
                "rollback_data": old_content,
            }]
            
            return {
                "result": {
                    "path": path,
                    "bytes_written": len(content.encode(encoding)),
                    "mode": mode,
                },
                "side_effects": side_effects,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def create_directory(self, path: str, parents: bool = True) -> Dict[str, Any]:
        """Create a directory"""
        path = self._normalize_path(path)
        
        safe, msg = self._is_path_safe(path)
        if not safe:
            return {"error": msg}
        
        try:
            if os.path.exists(path):
                return {"error": f"Path already exists: {path}"}
            
            if parents:
                os.makedirs(path)
            else:
                os.mkdir(path)
            
            return {
                "result": {
                    "path": path,
                    "created": True,
                },
                "side_effects": [{
                    "type": "directory_created",
                    "path": path,
                    "reversible": True,
                }]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def copy(
        self,
        source: str,
        destination: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Copy file or directory"""
        source = self._normalize_path(source)
        destination = self._normalize_path(destination)
        
        safe, msg = self._is_path_safe(destination)
        if not safe:
            return {"error": msg}
        
        try:
            if not os.path.exists(source):
                return {"error": f"Source not found: {source}"}
            
            if os.path.exists(destination) and not overwrite:
                return {"error": f"Destination exists: {destination}"}
            
            if os.path.isdir(source):
                if os.path.exists(destination):
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            
            return {
                "result": {
                    "source": source,
                    "destination": destination,
                    "is_directory": os.path.isdir(destination),
                },
                "side_effects": [{
                    "type": "file_created" if os.path.isfile(destination) else "directory_created",
                    "path": destination,
                    "reversible": True,
                }]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def move(
        self,
        source: str,
        destination: str,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Move/rename file or directory"""
        source = self._normalize_path(source)
        destination = self._normalize_path(destination)
        
        safe_src, msg_src = self._is_path_safe(source)
        safe_dst, msg_dst = self._is_path_safe(destination)
        
        if not safe_src:
            return {"error": msg_src}
        if not safe_dst:
            return {"error": msg_dst}
        
        try:
            if not os.path.exists(source):
                return {"error": f"Source not found: {source}"}
            
            if os.path.exists(destination) and not overwrite:
                return {"error": f"Destination exists: {destination}"}
            
            shutil.move(source, destination)
            
            return {
                "result": {
                    "source": source,
                    "destination": destination,
                },
                "side_effects": [
                    {
                        "type": "file_moved",
                        "path": destination,
                        "reversible": True,
                        "rollback_data": {"original_path": source},
                    }
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def delete(
        self,
        path: str,
        recursive: bool = False,
    ) -> Dict[str, Any]:
        """Delete file or directory"""
        path = self._normalize_path(path)
        
        safe, msg = self._is_path_safe(path)
        if not safe:
            return {"error": msg}
        
        try:
            if not os.path.exists(path):
                return {"error": f"Path not found: {path}"}
            
            is_dir = os.path.isdir(path)
            
            # Store for potential recovery
            if is_dir:
                if not recursive:
                    return {"error": "Use recursive=True to delete directories"}
                shutil.rmtree(path)
            else:
                os.remove(path)
            
            return {
                "result": {
                    "path": path,
                    "deleted": True,
                    "was_directory": is_dir,
                },
                "side_effects": [{
                    "type": "file_deleted" if not is_dir else "directory_deleted",
                    "path": path,
                    "reversible": False,  # Deletion is generally not reversible without backup
                }]
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
_controller: Optional[FileSystemController] = None

def get_filesystem_controller() -> FileSystemController:
    global _controller
    if _controller is None:
        _controller = FileSystemController()
    return _controller
