"""
moa/app_controller.py
Application Controller - Launches applications with smart indexing
Fixed: Direct executable launch, proper shortcut handling, resilient scanning
"""

import os
import json
import subprocess
import platform
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set

logger = logging.getLogger("jarvis.app_controller")


class AppController:
    """
    Smart Application Launcher with indexing.
    
    Features:
    - Builds index of installed applications on startup
    - Direct executable launch (no shell)
    - Proper shortcut (.lnk) handling
    - Windows system app aliases
    - Resilient to missing directories
    """
    
    def __init__(self):
        self.index_file = Path(__file__).parent.parent / "data" / "app_index.json"
        self.index_file.parent.mkdir(exist_ok=True)
        self.app_index: Dict[str, str] = {}
        self.aliases: Dict[str, str] = {}
        self._load_index()
        
        # =================================================
        # SYSTEM APPS - Direct launch, no search needed
        # =================================================
        self.system_apps = {
            # Windows built-in apps (direct executables)
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "task manager": "taskmgr.exe",
            "regedit": "regedit.exe",
            "registry": "regedit.exe",
            "control panel": "control.exe",
            "device manager": "devmgmt.msc",
            "disk management": "diskmgmt.msc",
            "services": "services.msc",
            "event viewer": "eventvwr.msc",
            "performance monitor": "perfmon.msc",
            "resource monitor": "resmon.exe",
            "system information": "msinfo32.exe",
            "dxdiag": "dxdiag.exe",
            "character map": "charmap.exe",
            "snipping tool": "SnippingTool.exe",
            "screenshot": "SnippingTool.exe",
            "steps recorder": "psr.exe",
            "wordpad": "write.exe",
            "calculator": "calc.exe",
        }
        
        # =================================================
        # UWP / Special Apps - Launch via explorer or shell:
        # =================================================
        self.uwp_apps = {
            "settings": "ms-settings:",
            "store": "ms-windows-store:",
            "microsoft store": "ms-windows-store:",
            "photos": "ms-photos:",
            "alarms": "ms-clock:",
            "clock": "ms-clock:",
            "calendar": "outlookcal:",
            "mail": "outlookmail:",
            "people": "ms-people:",
            "maps": "bingmaps:",
            "weather": "weather:",
            "news": "bingnews:",
            "sports": "bingnews:sports",
            "finance": "bingfinance:",
            "health": "microsoft-health:",
            "tips": "ms-get-tips:",
            "feedback": "ms-feedback-hub:",
            "spotify": "spotify:",
        }
        
        # =================================================
        # Common App Aliases
        # =================================================
        self.default_aliases = {
            "calc": "calculator",
            "calc.exe": "calculator",
            "code": "visual studio code",
            "vscode": "visual studio code",
            "vs code": "visual studio code",
            "chrome": "google chrome",
            "browser": "google chrome",
            "ff": "firefox",
            "edge": "microsoft edge",
            "word": "microsoft word",
            "excel": "microsoft excel",
            "ppt": "microsoft powerpoint",
            "powerpoint": "microsoft powerpoint",
            "outlook": "microsoft outlook",
            "spot": "spotify",
            "vlc": "vlc media player",
            "mpc": "media player classic",
            "store": "microsoft store",
            "microsoft store": "microsoft store",
            "chatgpt": "chatgpt",
            "chat gpt": "chatgpt",
            "notepad++": "notepadplusplus",
            "notepad plus plus": "notepadplusplus",
            "npp": "notepadplusplus",
        }
        
        # Build initial index if empty
        if not self.app_index:
            self._build_initial_index()
        
        logger.info(f"AppController initialized with {len(self.app_index)} apps")
    
    def _load_index(self):
        """Load application index from file."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    self.app_index = data.get("apps", {})
                    self.aliases = data.get("aliases", {})
                logger.info(f"Loaded {len(self.app_index)} apps from index")
            except Exception as e:
                logger.error(f"Error loading app index: {e}")
                self.app_index = {}
                self.aliases = {}
    
    def _save_index(self):
        """Save application index to file."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump({
                    "apps": self.app_index,
                    "aliases": self.aliases
                }, f, indent=2)
            logger.info(f"Saved {len(self.app_index)} apps to index")
        except Exception as e:
            logger.error(f"Error saving app index: {e}")
    
    def _safe_scan_directory(self, directory: Path, pattern: str = "*.lnk") -> List[Path]:
        """Safely scan a directory for files, handling permissions and missing paths."""
        try:
            if not directory or not directory.exists():
                return []
            return list(directory.glob(pattern))
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.debug(f"Skipping directory {directory}: {e}")
            return []
    
    def _safe_rglob(self, directory: Path, pattern: str = "*.exe", max_depth: int = 3) -> List[Path]:
        """Safely scan a directory recursively with depth limit."""
        results = []
        try:
            if not directory or not directory.exists():
                return results
            
            # Limit depth to avoid scanning too deep
            def scan_dir(path: Path, depth: int = 0):
                if depth > max_depth:
                    return
                try:
                    for item in path.iterdir():
                        if item.is_file() and item.match(pattern):
                            results.append(item)
                        elif item.is_dir():
                            scan_dir(item, depth + 1)
                except (PermissionError, FileNotFoundError, OSError):
                    pass
            
            scan_dir(directory)
        except Exception as e:
            logger.debug(f"Error scanning {directory}: {e}")
        
        return results
    
    def _build_initial_index(self):
        """Build initial application index with error resilience."""
        apps_found: Set[str] = set()
        
        # 1. Add system apps (no search needed)
        for name, path in self.system_apps.items():
            if name not in self.app_index:
                self.app_index[name] = path
                apps_found.add(name)
        
        # 2. Add UWP apps (no search needed)
        for name, uri in self.uwp_apps.items():
            if name not in self.app_index:
                self.app_index[name] = uri
                apps_found.add(name)
        
        # 3. Scan Start Menu shortcuts (safe)
        start_menu_paths = [
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("ALLUSERSPROFILE", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]
        
        for start_path in start_menu_paths:
            if start_path and start_path.exists():
                for exe_file in self._safe_scan_directory(start_path, "*.lnk"):
                    name = exe_file.stem.lower()
                    if name not in self.app_index:
                        self.app_index[name] = str(exe_file)
                        apps_found.add(name)
        
        # 4. Add desktop shortcuts (safe)
        desktop_paths = [
            Path(os.environ.get("USERPROFILE", "")) / "Desktop",
            Path(os.environ.get("PUBLIC", "")) / "Desktop",
            Path(os.environ.get("USERPROFILE", "")) / "OneDrive" / "Desktop",
        ]
        
        for desktop_path in desktop_paths:
            if desktop_path and desktop_path.exists():
                for shortcut in self._safe_scan_directory(desktop_path, "*.lnk"):
                    name = shortcut.stem.lower()
                    if name not in self.app_index:
                        self.app_index[name] = str(shortcut)
                        apps_found.add(name)
        
        # 5. Scan common install directories (limited depth)
        common_base_paths = [
            os.environ.get("ProgramFiles", ""),
            os.environ.get("ProgramFiles(x86)", ""),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        
        # Known app names to search for (limited list)
        known_apps = [
            "Google", "Mozilla", "Microsoft", "Spotify", "Slack", "Discord",
            "Visual Studio Code", "Git", "Python", "Docker",
            "Adobe", "Blender", "Unity", "Steam",
            "ChatGPT", "Notion", "Obsidian", "VLC", "GIMP",
            "Firefox", "Chrome", "Edge", "Brave", "Opera",
        ]
        
        for base_path in common_base_paths:
            if not base_path or not os.path.exists(base_path):
                continue
            
            base = Path(base_path)
            for known in known_apps:
                app_dir = base / known
                if app_dir.exists():
                    # Safe limited search for .exe
                    for exe in self._safe_rglob(app_dir, "*.exe", max_depth=2):
                        exe_name = exe.stem.lower()
                        # Match exe name to app name
                        known_lower = known.lower().replace(" ", "")
                        if any(x in exe_name for x in [known_lower, known_lower[:5]]):
                            app_name = known.lower()
                            if app_name not in self.app_index:
                                self.app_index[app_name] = str(exe)
                                apps_found.add(app_name)
                                break
        
        # 6. Add aliases
        for alias, target in self.default_aliases.items():
            if alias not in self.aliases:
                self.aliases[alias] = target
        
        self._save_index()
        logger.info(f"Built initial index with {len(apps_found)} apps")
    
    def resolve_app_name(self, name: str) -> str:
        """Resolve alias to actual app name."""
        name_lower = name.lower().strip()
        
        # Check exact alias match
        if name_lower in self.aliases:
            return self.aliases[name_lower]
        
        # Check partial alias match
        for alias, target in self.aliases.items():
            if alias in name_lower or name_lower in alias:
                return target
        
        return name_lower
    
    def find_app(self, name: str) -> Optional[Tuple[str, str]]:
        """
        Find an application by name.
        
        Returns:
            Tuple of (app_name, executable_path) or None if not found
        """
        name_lower = name.lower().strip()
        resolved_name = self.resolve_app_name(name_lower)
        
        # 1. Check system apps (direct launch, no search)
        if resolved_name in self.system_apps:
            exe_path = self.system_apps[resolved_name]
            logger.info(f"System app '{resolved_name}' -> {exe_path}")
            return (resolved_name, exe_path)
        
        # 2. Check UWP apps
        if resolved_name in self.uwp_apps:
            uri = self.uwp_apps[resolved_name]
            logger.info(f"UWP app '{resolved_name}' -> {uri}")
            return (resolved_name, uri)
        
        # 3. Check index
        if resolved_name in self.app_index:
            exe_path = self.app_index[resolved_name]
            if self._verify_path(exe_path):
                logger.info(f"Found app '{resolved_name}' in index: {exe_path}")
                return (resolved_name, exe_path)
        
        # 4. Try direct executable
        exe_path = self._find_executable(name_lower)
        if exe_path:
            logger.info(f"Found app '{resolved_name}' directly: {exe_path}")
            self.app_index[resolved_name] = exe_path
            self._save_index()
            return (resolved_name, exe_path)
        
        # 5. Search common locations (limited)
        exe_path = self._search_common_locations(resolved_name)
        if exe_path:
            logger.info(f"Found app '{resolved_name}' in common locations: {exe_path}")
            self.app_index[resolved_name] = exe_path
            self._save_index()
            return (resolved_name, exe_path)
        
        logger.warning(f"App '{name}' not found")
        return None
    
    def _verify_path(self, path: str) -> bool:
        """Verify that a path exists and is accessible."""
        if not path:
            return False
        # Check if it's a direct executable
        if os.path.exists(path):
            return True
        # Check with .exe extension
        if not path.endswith('.exe'):
            path_exe = path + '.exe'
            if os.path.exists(path_exe):
                return True
        return False
    
    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable by name."""
        name_lower = name.lower()
        
        # Check if it's a direct path
        if os.path.exists(name):
            return name
        
        # Check with .exe extension
        if not name_lower.endswith('.exe'):
            exe_path = name + '.exe'
            if os.path.exists(exe_path):
                return exe_path
        
        # Check in PATH using where command
        try:
            result = subprocess.run(
                ['where', name],
                capture_output=True,
                text=True,
                shell=False
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        if not name_lower.endswith('.exe'):
            try:
                result = subprocess.run(
                    ['where', name + '.exe'],
                    capture_output=True,
                    text=True,
                    shell=False
                )
                if result.returncode == 0:
                    return result.stdout.strip().split('\n')[0]
            except:
                pass
        
        return None
    
    def _search_common_locations(self, name: str) -> Optional[str]:
        """Search common install locations for an app with error resilience."""
        name_lower = name.lower()
        
        # Common locations to search (limited)
        search_locations = [
            os.environ.get("ProgramFiles", ""),
            os.environ.get("ProgramFiles(x86)", ""),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        
        # Common executable names to look for
        search_names = [
            name_lower,
            name_lower.replace(" ", ""),
            name_lower.replace("-", ""),
            name_lower.replace("_", ""),
        ]
        
        for location in search_locations:
            if not location or not os.path.exists(location):
                continue
            
            location_path = Path(location)
            
            try:
                for pattern in search_names:
                    # Look for matching directories
                    for app_dir in location_path.iterdir():
                        if not app_dir.is_dir():
                            continue
                        # Check if app directory name matches
                        dir_name = app_dir.name.lower()
                        if pattern in dir_name or dir_name in pattern:
                            # Look for exe in bin or app subdirectories
                            for subdir_name in ["bin", "app", "application", "program", "files", ""]:
                                search_dir = app_dir / subdir_name if subdir_name else app_dir
                                if search_dir.exists():
                                    for exe in self._safe_scan_directory(search_dir, "*.exe"):
                                        exe_name = exe.stem.lower()
                                        if any(x in exe_name for x in search_names):
                                            return str(exe)
                    
                    # Direct search in location (limited depth)
                    for exe in self._safe_scan_directory(location_path, "*.exe"):
                        if exe.stem.lower() in search_names:
                            return str(exe)
            except Exception as e:
                logger.debug(f"Error searching {location}: {e}")
                continue
        
        return None
    
    def launch(self, name: str, args: List[str] = None) -> Dict:
        """
        Launch an application.
        
        CRITICAL: Uses shell=False for direct execution.
        No CMD windows should appear.
        
        Args:
            name: Application name
            args: Command line arguments
            
        Returns:
            Dict with success status and details
        """
        result = self.find_app(name)
        
        if not result:
            return {
                "success": False,
                "error": f"Application '{name}' not found",
                "message": f"❌ Could not find '{name}'. Please check the name and try again."
            }
        
        app_name, path = result
        args = args or []
        
        try:
            # =================================================
            # UWP App (URI protocol)
            # =================================================
            if path.startswith("ms-") or path.startswith("outlook") or path.startswith("bing") or path.startswith("spotify:"):
                logger.info(f"Launching UWP app: {path}")
                subprocess.Popen(['start', path], shell=True)
                return {
                    "success": True,
                    "message": f"✅ Opening {app_name}...",
                    "app": app_name,
                    "path": path,
                    "args": args
                }
            
            # =================================================
            # Shortcut (.lnk) - Use os.startfile
            # =================================================
            if path.lower().endswith('.lnk'):
                logger.info(f"Launching shortcut: {path}")
                os.startfile(path)
                return {
                    "success": True,
                    "message": f"✅ Opening {app_name}...",
                    "app": app_name,
                    "path": path,
                    "args": args
                }
            
            # =================================================
            # Direct Executable (.exe or other)
            # =================================================
            # Check if it's a system command (no path)
            if os.path.sep not in path and path.endswith('.exe'):
                # System command - use shell=False with just the name
                logger.info(f"Launching system command: {path}")
                if args:
                    subprocess.Popen([path] + args, shell=False)
                else:
                    subprocess.Popen([path], shell=False)
                return {
                    "success": True,
                    "message": f"✅ Opening {app_name}...",
                    "app": app_name,
                    "path": path,
                    "args": args
                }
            
            # Check if the path exists
            if not os.path.exists(path):
                # Try adding .exe
                if not path.endswith('.exe'):
                    path_exe = path + '.exe'
                    if os.path.exists(path_exe):
                        path = path_exe
                    else:
                        return {
                            "success": False,
                            "error": f"Path does not exist: {path}",
                            "message": f"❌ Could not find '{app_name}' at {path}",
                            "app": app_name,
                            "path": path
                        }
            
            # Direct executable launch - shell=False
            logger.info(f"Launching executable: {path}")
            if args:
                process = subprocess.Popen([path] + args, shell=False)
            else:
                process = subprocess.Popen([path], shell=False)
            
            return {
                "success": True,
                "message": f"✅ Opening {app_name}...",
                "app": app_name,
                "path": path,
                "args": args,
                "pid": process.pid if process else None
            }
            
        except FileNotFoundError as e:
            logger.error(f"File not found when launching {app_name}: {e}")
            return {
                "success": False,
                "error": f"File not found: {str(e)}",
                "message": f"❌ Could not find '{app_name}'. The file may be missing or moved.",
                "app": app_name,
                "path": path
            }
        except Exception as e:
            logger.error(f"Error launching {app_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Could not open {app_name}. Error: {str(e)}",
                "app": app_name,
                "path": path
            }
    
    def get_all_apps(self) -> List[str]:
        """Get list of all indexed applications."""
        return sorted(self.app_index.keys())
    
    def search_apps(self, query: str) -> List[str]:
        """Search for applications matching query."""
        query_lower = query.lower()
        matches = []
        
        for app_name in self.app_index.keys():
            if query_lower in app_name.lower():
                matches.append(app_name)
        
        return matches
    
    def add_alias(self, alias: str, target: str) -> None:
        """Add an alias for an application."""
        self.aliases[alias.lower()] = target.lower()
        self._save_index()
    
    def refresh_index(self) -> int:
        """Refresh the application index."""
        self.app_index = {}
        self._build_initial_index()
        return len(self.app_index)