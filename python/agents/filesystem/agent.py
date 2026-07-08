# agents/filesystem/agent.py

import os
import shutil
import asyncio
import logging
import subprocess
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

logger = logging.getLogger("jarvis.filesystem_agent")

class FileSystemAgent:
    """
    FileSystem Agent - Handles file operations with full drive access
    Supports: C:, D:, E:, USB drives, external drives, network drives
    """
    
    def __init__(self):
        self.agent_name = "filesystem_agent"
        self.description = "Handles file system operations with full drive access"
        self.working_directory = os.getcwd()
        self._allowed_extensions = [
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml',
            '.md', '.csv', '.log', '.ini', '.cfg', '.conf', '.sh', '.bat', '.ps1',
            '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wav',
            '.zip', '.rar', '.7z', '.tar', '.gz'
        ]
        self._drives = self._get_available_drives()
        logger.info(f"✅ FileSystemAgent initialized with {len(self._drives)} drives")
        logger.info(f"   Drives: {', '.join(self._drives)}")
    
    def _get_available_drives(self) -> List[str]:
        """Get all available drives on the system"""
        drives = []
        
        if os.name == 'nt':  # Windows
            try:
                import string
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append(drive)
            except:
                pass
        else:  # Linux/Mac
            try:
                partitions = psutil.disk_partitions()
                for partition in partitions:
                    if partition.device.startswith('/dev/'):
                        drives.append(partition.mountpoint)
            except:
                pass
        
        return drives
    
    def _get_drive_info(self, path: str) -> Dict[str, Any]:
        """Get information about a drive"""
        try:
            # Normalize path to drive root
            if len(path) >= 2 and path[1] == ':':
                if len(path) >= 3 and path[2] in ['/', '\\']:
                    drive = path[:3]
                else:
                    drive = f"{path[:2]}\\"
            else:
                drive = path
            
            try:
                # Get disk space using shutil
                usage = shutil.disk_usage(drive)
                
                # Determine drive type
                drive_type = "Unknown"
                if os.name == 'nt':
                    drive_letter = drive[:2]
                    try:
                        # Try to determine if it's a system drive
                        if drive_letter.lower() == 'c:':
                            drive_type = "System"
                        elif os.path.exists(drive_letter):
                            drive_type = "Fixed"
                    except:
                        pass
                else:
                    drive_type = "Mounted"
                
                return {
                    "drive": drive,
                    "type": drive_type,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "total_human": self._format_size(usage.total),
                    "used_human": self._format_size(usage.used),
                    "free_human": self._format_size(usage.free),
                    "percent_used": (usage.used / usage.total * 100) if usage.total > 0 else 0
                }
            except Exception as e:
                logger.debug(f"Could not get drive info for {drive}: {e}")
                
        except Exception as e:
            logger.debug(f"Could not get drive info for {path}: {e}")
        
        return {}
    
    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path with full drive support
        Supports:
        - Absolute paths with drive letter: C:/Users/file.txt
        - UNC paths: \\\\server\\share\\file.txt
        - Relative paths: ./file.txt
        - Home directory: ~/file.txt
        - Environment variables: %USERPROFILE%/file.txt
        - Any drive: D:/file.txt, E:/file.txt, etc.
        - Drive-specific patterns: "filename in D drive"
        """
        # Clean the path
        path = path.strip()
        
        # Expand environment variables
        if os.name == 'nt':
            for key, value in os.environ.items():
                path = path.replace(f'%{key}%', value)
        
        # Expand user home directory
        path = os.path.expanduser(path)
        
        # Check if it's a UNC path (starts with \\)
        if path.startswith('\\\\'):
            return Path(path)
        
        # Check if it's an absolute path with drive letter
        if len(path) >= 2 and path[1] == ':':
            # If it's just a drive letter (e.g., "C:"), add backslash
            if len(path) == 2:
                path = path + "\\"
            return Path(path)
        
        # Handle "in d drive" or "in c drive" patterns
        if " in " in path.lower():
            parts = re.split(r'\s+in\s+', path, maxsplit=1)
            if len(parts) == 2:
                filename = parts[0].strip()
                drive_part = parts[1].strip().lower()
                # Extract drive letter
                drive_match = re.search(r'([a-z])\s*(?:drive|:)?', drive_part)
                if drive_match:
                    drive = drive_match.group(1).upper()
                    # If drive_part contains a path after the drive
                    path_parts = drive_part.split('\\')
                    if len(path_parts) > 1 and path_parts[1].strip():
                        # It has a subpath
                        path = f"{drive}:\\{path_parts[1].strip()}\\{filename}"
                    else:
                        path = f"{drive}:\\{filename}"
                    return Path(path)
        
        # If not absolute, resolve relative to working directory
        if not os.path.isabs(path):
            path = os.path.join(self.working_directory, path)
        
        return Path(path).resolve()
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def _is_path_on_drive(self, path: str) -> bool:
        """Check if a path exists and is accessible"""
        try:
            return os.path.exists(path) or os.path.exists(os.path.dirname(path))
        except:
            return False
    
    # ============================================
    # CORE FILE OPERATIONS
    # ============================================
    
    async def _run(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for the agent"""
        logger.info(f"FileSystemAgent: {action} -> {params}")
        
        action_map = {
            "create_file": self.create_file,
            "open_file": self.open_file,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "delete_file": self.delete_file,
            "delete_folder": self.delete_folder,
            "list_directory": self.list_directory,
            "copy_file": self.copy_file,
            "move_file": self.move_file,
            "search_files": self.search_files,
            "get_file_info": self.get_file_info,
            "create_folder": self.create_folder,
            "create_and_open": self.create_and_open,
            "list_drives": self.list_drives,
            "get_drive_info": self.get_drive_info_route,
        }
        
        if action not in action_map:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": list(action_map.keys())
            }
        
        try:
            result = await action_map[action](params)
            return result
        except Exception as e:
            logger.error(f"FileSystemAgent error: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    # ============================================
    # DRIVE MANAGEMENT
    # ============================================
    
    async def list_drives(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        List all available drives
        """
        drives = self._get_available_drives()
        drive_info = []
        
        for drive in drives:
            info = self._get_drive_info(drive)
            if info:
                drive_info.append(info)
        
        return {
            "success": True,
            "drives": drive_info,
            "count": len(drive_info),
            "message": f"Found {len(drive_info)} drives"
        }
    
    async def get_drive_info_route(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get information about a specific drive
        params: {
            "path": "C:/" or "D:/" or "E:/"
        }
        """
        path = params.get("path", "")
        if not path:
            return {"success": False, "error": "No path provided"}
        
        # Normalize path to drive root
        if len(path) >= 2 and path[1] == ':':
            if len(path) >= 3 and path[2] in ['/', '\\']:
                drive = path[:3]
            else:
                drive = f"{path[:2]}\\"
        else:
            drive = path
        
        info = self._get_drive_info(drive)
        if not info:
            return {"success": False, "error": f"Could not get info for drive: {drive}"}
        
        return {
            "success": True,
            "drive_info": info,
            "message": f"Drive {info.get('drive', '')}: {info.get('free_human', '')} free of {info.get('total_human', '')}"
        }
    
    # ============================================
    # FILE OPERATIONS (Updated with drive support)
    # ============================================
    
    async def create_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new file at specified path (supports any drive)"""
        file_path = params.get("path", "")
        content = params.get("content", "")
        overwrite = params.get("overwrite", False)
        
        if not file_path:
            return {"success": False, "error": "No path provided"}
        
        # Resolve path
        path = self._resolve_path(file_path)
        
        # Check if parent directory exists
        if not path.parent.exists():
            # Try to create parent directory
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                return {
                    "success": False,
                    "error": f"Permission denied. Cannot create directory: {path.parent}",
                    "suggestion": "Check if you have write access to this location"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Cannot create directory: {e}",
                    "path": str(path.parent)
                }
        
        # Check if file exists
        if path.exists() and not overwrite:
            return {
                "success": False,
                "error": f"File already exists: {path}",
                "suggestion": "Use overwrite=True or choose a different name or location"
            }
        
        try:
            # Write the file
            path.write_text(content, encoding='utf-8')
            
            return {
                "success": True,
                "message": f"✅ Created: {path}",
                "path": str(path),
                "size": path.stat().st_size,
                "drive": str(path.drive) if hasattr(path, 'drive') else "unknown",
                "created": datetime.fromtimestamp(path.stat().st_ctime).isoformat()
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot write to: {path}",
                "suggestion": "Check if the drive is writable or if you have admin rights"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create file: {e}"}
    
    async def write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write content to a file (creates if doesn't exist, overwrites if exists)
        params: {
            "path": "path/to/file",
            "content": "content to write",
            "overwrite": True/False
        }
        """
        file_path = params.get("path", "")
        content = params.get("content", "")
        overwrite = params.get("overwrite", True)
        
        if not file_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(file_path)
        
        # Check if parent directory exists
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Cannot create directory: {e}",
                    "path": str(path.parent)
                }
        
        # Check if file exists and overwrite is False
        if path.exists() and not overwrite:
            return {
                "success": False,
                "error": f"File already exists: {path}",
                "suggestion": "Set overwrite=True or use append_file to add content"
            }
        
        try:
            path.write_text(content, encoding='utf-8')
            return {
                "success": True,
                "message": f"✅ Written to: {path}",
                "path": str(path),
                "size": path.stat().st_size,
                "drive": str(path.drive) if hasattr(path, 'drive') else "unknown"
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot write to: {path}",
                "suggestion": "Check if the drive is writable"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to write file: {e}"}
    
    async def append_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append content to a file
        params: {
            "path": "path/to/file",
            "content": "content to append"
        }
        """
        file_path = params.get("path", "")
        content = params.get("content", "")
        
        if not file_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(file_path)
        
        # Check if parent directory exists
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Cannot create directory: {e}",
                    "path": str(path.parent)
                }
        
        try:
            # Read existing content if file exists
            existing = ""
            if path.exists():
                try:
                    existing = path.read_text(encoding='utf-8')
                except:
                    existing = ""
            
            # Write combined content
            new_content = existing + content
            path.write_text(new_content, encoding='utf-8')
            
            return {
                "success": True,
                "message": f"✅ Appended to: {path}",
                "path": str(path),
                "size": path.stat().st_size,
                "drive": str(path.drive) if hasattr(path, 'drive') else "unknown",
                "appended": len(content),
                "total_size": path.stat().st_size
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot append to: {path}",
                "suggestion": "Check if the drive is writable"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to append to file: {e}"}
    
    async def open_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open a file with default application (supports any drive)"""
        file_path = params.get("path", "")
        application = params.get("application", None)
        
        if not file_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {path}",
                "suggestion": "Check if the file exists and the path is correct"
            }
        
        try:
            if application:
                if os.name == 'nt':
                    subprocess.Popen([application, str(path)], shell=True)
                else:
                    subprocess.Popen([application, str(path)])
            else:
                if os.name == 'nt':
                    os.startfile(str(path))
                else:
                    subprocess.Popen(['xdg-open', str(path)])
            
            return {
                "success": True,
                "message": f"✅ Opened: {path}",
                "path": str(path),
                "drive": str(path.drive) if hasattr(path, 'drive') else "unknown",
                "application": application or "default"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to open file: {e}"}
    
    async def read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents (supports any drive)"""
        file_path = params.get("path", "")
        max_lines = params.get("max_lines", None)
        
        if not file_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {path}",
                "suggestion": "Check if the file exists on the drive"
            }
        
        try:
            content = path.read_text(encoding='utf-8')
            
            if max_lines:
                lines = content.split('\n')[:max_lines]
                content = '\n'.join(lines)
                if len(lines) < len(content.split('\n')):
                    content += f"\n... (truncated, showing {max_lines} lines)"
            
            return {
                "success": True,
                "content": content,
                "path": str(path),
                "size": path.stat().st_size,
                "lines": len(content.split('\n'))
            }
        except UnicodeDecodeError:
            # Try reading as binary if text fails
            try:
                with open(path, 'rb') as f:
                    content = f.read(1024)  # Read first 1KB for preview
                    return {
                        "success": True,
                        "content": f"[Binary file - showing first 1024 bytes]\n{content.hex()[:200]}...",
                        "path": str(path),
                        "size": path.stat().st_size,
                        "is_binary": True
                    }
            except:
                return {"success": False, "error": "Could not read file (binary or protected)"}
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {e}"}
    
    async def list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List contents of a directory (supports any drive)"""
        file_path = params.get("path", ".")
        show_hidden = params.get("show_hidden", False)
        
        path = self._resolve_path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"Path not found: {path}",
                "suggestion": "Check if the drive is connected and path is correct"
            }
        
        if not path.is_dir():
            return {"success": False, "error": "Path is not a directory"}
        
        try:
            items = []
            for item in path.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                try:
                    is_dir = item.is_dir()
                    stat = item.stat() if item.exists() else None
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if is_dir else "file",
                        "size": stat.st_size if stat and not is_dir else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat() if stat else None
                    })
                except (PermissionError, OSError):
                    # Skip items we can't access
                    continue
            
            items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
            
            # Get drive info
            drive_info = self._get_drive_info(str(path))
            
            return {
                "success": True,
                "path": str(path),
                "drive_info": drive_info,
                "items": items,
                "count": len(items),
                "directories": sum(1 for i in items if i["type"] == "directory"),
                "files": sum(1 for i in items if i["type"] == "file")
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied accessing: {path}",
                "suggestion": "Check if you have read access to this location"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to list directory: {e}"}
    
    async def create_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new folder (supports any drive)"""
        folder_path = params.get("path", "")
        parents = params.get("parents", True)
        
        if not folder_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(folder_path)
        
        if path.exists():
            return {
                "success": False,
                "error": f"Folder already exists: {path}",
                "suggestion": "Choose a different name or location"
            }
        
        try:
            if parents:
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.mkdir()
            
            return {
                "success": True,
                "message": f"✅ Created folder: {path}",
                "path": str(path),
                "drive": str(path.drive) if hasattr(path, 'drive') else "unknown"
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot create folder: {path}",
                "suggestion": "Check if you have write access to this drive/location"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to create folder: {e}"}
    
    async def delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file (supports any drive)"""
        file_path = params.get("path", "")
        force = params.get("force", False)
        
        if not file_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {path}",
                "suggestion": "Check if the file exists"
            }
        
        if path.is_dir() and not force:
            return {
                "success": False,
                "error": "Path is a directory. Use delete_folder or force=True"
            }
        
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            
            return {
                "success": True,
                "message": f"✅ Deleted: {path}",
                "path": str(path)
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot delete: {path}",
                "suggestion": "Check if the file is in use or you have delete permissions"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to delete: {e}"}
    
    async def delete_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a folder and all its contents (supports any drive)"""
        folder_path = params.get("path", "")
        force = params.get("force", False)
        
        if not folder_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(folder_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"Folder not found: {path}",
                "suggestion": "Check if the folder exists"
            }
        
        if not path.is_dir():
            return {"success": False, "error": "Path is not a directory"}
        
        try:
            shutil.rmtree(path)
            return {
                "success": True,
                "message": f"✅ Deleted folder: {path}",
                "path": str(path)
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot delete folder: {path}",
                "suggestion": "Check if the folder is in use or you have delete permissions"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to delete folder: {e}"}
    
    async def search_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for files matching a pattern (supports any drive)"""
        search_path = params.get("path", ".")
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", True)
        max_results = params.get("max_results", 50)
        
        path = self._resolve_path(search_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"Path not found: {path}",
                "suggestion": "Check if the drive is connected"
            }
        
        try:
            results = []
            glob_pattern = f"**/{pattern}" if recursive else pattern
            
            for item in path.glob(glob_pattern):
                if len(results) >= max_results:
                    break
                
                try:
                    is_dir = item.is_dir()
                    stat = item.stat() if item.exists() else None
                    results.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if is_dir else "file",
                        "size": stat.st_size if stat and not is_dir else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat() if stat else None
                    })
                except (PermissionError, OSError):
                    continue
            
            return {
                "success": True,
                "path": str(path),
                "pattern": pattern,
                "results": results,
                "count": len(results),
                "truncated": len(results) >= max_results
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to search: {e}"}
    
    async def copy_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Copy a file or directory (supports any drive to any drive)"""
        source = params.get("source", "")
        destination = params.get("destination", "")
        
        if not source or not destination:
            return {"success": False, "error": "Source and destination required"}
        
        src_path = self._resolve_path(source)
        dst_path = self._resolve_path(destination)
        
        if not src_path.exists():
            return {
                "success": False,
                "error": f"Source not found: {src_path}",
                "suggestion": "Check if the source file/drive is accessible"
            }
        
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            
            return {
                "success": True,
                "message": f"✅ Copied: {src_path} -> {dst_path}",
                "source": str(src_path),
                "destination": str(dst_path)
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot copy to: {dst_path}",
                "suggestion": "Check if destination drive is writable"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to copy: {e}"}
    
    async def move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Move a file or directory (supports any drive to any drive)"""
        source = params.get("source", "")
        destination = params.get("destination", "")
        
        if not source or not destination:
            return {"success": False, "error": "Source and destination required"}
        
        src_path = self._resolve_path(source)
        dst_path = self._resolve_path(destination)
        
        if not src_path.exists():
            return {
                "success": False,
                "error": f"Source not found: {src_path}",
                "suggestion": "Check if the source file/drive is accessible"
            }
        
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            
            return {
                "success": True,
                "message": f"✅ Moved: {src_path} -> {dst_path}",
                "source": str(src_path),
                "destination": str(dst_path)
            }
        except PermissionError:
            return {
                "success": False,
                "error": f"Permission denied. Cannot move to: {dst_path}",
                "suggestion": "Check if destination drive is writable"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to move: {e}"}
    
    async def create_and_open(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a file and open it immediately (supports any drive)"""
        create_result = await self.create_file(params)
        if not create_result.get("success"):
            return create_result
        
        open_result = await self.open_file(params)
        
        return {
            "success": True,
            "message": f"✅ Created and opened: {params.get('path')}",
            "create_result": create_result,
            "open_result": open_result
        }
    
    # ============================================
    # ADDITIONAL HELPER METHODS
    # ============================================
    
    async def get_file_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed file information (supports any drive)"""
        file_path = params.get("path", "")
        
        if not file_path:
            return {"success": False, "error": "No path provided"}
        
        path = self._resolve_path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"Path not found: {path}",
                "suggestion": "Check if the drive is connected and path is correct"
            }
        
        try:
            stat = path.stat()
            
            return {
                "success": True,
                "path": str(path),
                "name": path.name,
                "drive": str(path.drive) if hasattr(path, 'drive') else "unknown",
                "is_directory": path.is_dir(),
                "is_file": path.is_file(),
                "size": stat.st_size,
                "size_human": self._format_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "extension": path.suffix if path.is_file() else None,
                "parent": str(path.parent)
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get file info: {e}"}
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for the agent"""
        return {
            "agent": self.agent_name,
            "description": self.description,
            "supported_drives": self._drives,
            "actions": {
                "create_file": "Create a new file on any drive",
                "open_file": "Open a file on any drive",
                "read_file": "Read file contents",
                "write_file": "Write content to a file (overwrites existing)",
                "append_file": "Append content to a file",
                "delete_file": "Delete a file",
                "delete_folder": "Delete a folder and its contents",
                "list_directory": "List directory contents",
                "copy_file": "Copy files between drives",
                "move_file": "Move files between drives",
                "search_files": "Search for files by pattern",
                "get_file_info": "Get detailed file information",
                "create_folder": "Create a new folder",
                "create_and_open": "Create a file and open it",
                "list_drives": "List all available drives",
                "get_drive_info": "Get information about a drive"
            },
            "examples": [
                "create file D:/test.txt with content Hello",
                "open E:/Documents/report.pdf",
                "list directory F:/",
                "copy file C:/data.txt to D:/backup/",
                "search files *.mp3 in E:/Music",
                "list drives"
            ]
        }