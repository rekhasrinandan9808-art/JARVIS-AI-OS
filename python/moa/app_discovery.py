"""
Application Discovery Service - Discovers all installed applications
Scans: Start Menu, Program Files, Windows Apps, Desktop, Registry
Supports: EXE, LNK, UWP (Microsoft Store) apps
"""

import os
import json
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from rapidfuzz import process, fuzz
import winreg
import ctypes
from ctypes import wintypes

logger = logging.getLogger("jarvis.app_discovery")

class AppDiscovery:
    """
    Discovers all installed applications on Windows.
    Scans:
    - Start Menu (All Users + Current User)
    - Program Files (x86 and x64)
    - Windows Apps (UWP/Microsoft Store)
    - Desktop shortcuts
    - Registry (for installed programs)
    """
    
    def __init__(self, cache_file: str = None):
        self.cache_file = cache_file or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "app_index.json"
        )
        
        # Ensure directory exists
        Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
        
        # App database
        self.apps: Dict[str, Dict] = {}
        self.aliases: Dict[str, str] = {}
        self.uwp_apps: Dict[str, str] = {}  # AppID -> Friendly Name
        self.app_paths: Dict[str, str] = {}  # Friendly Name -> Path/AppID
        
        # Load cache
        self.load_cache()
        
        # Track last scan time
        self.last_scan = 0
        self.scan_interval = 3600  # 1 hour
        
    def load_cache(self):
        """Load app cache from file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.apps = data.get("apps", {})
                    self.aliases = data.get("aliases", {})
                    self.uwp_apps = data.get("uwp_apps", {})
                    self.app_paths = data.get("app_paths", {})
                    self.last_scan = data.get("last_scan", 0)
                logger.info(f"📂 Loaded {len(self.apps)} apps from cache")
                return True
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
        return False
    
    def save_cache(self):
        """Save app cache to file."""
        try:
            data = {
                "apps": self.apps,
                "aliases": self.aliases,
                "uwp_apps": self.uwp_apps,
                "app_paths": self.app_paths,
                "last_scan": self.last_scan,
                "scan_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Saved {len(self.apps)} apps to cache")
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")
    
    def scan_all_apps(self, force: bool = False):
        """
        Scan all installed applications.
        This is the main discovery method called at startup.
        """
        # Check if cache is fresh
        if not force and (time.time() - self.last_scan) < self.scan_interval:
            logger.info("Using cached app list (fresh)")
            return
        
        logger.info("🔍 Scanning for all installed applications...")
        start_time = time.time()
        
        # Clear existing data
        self.apps = {}
        self.aliases = {}
        self.uwp_apps = {}
        self.app_paths = {}
        
        # Scan all sources
        self._scan_start_menu()
        self._scan_program_files()
        self._scan_windows_apps()
        self._scan_desktop()
        self._scan_registry()
        self._add_builtin_aliases()
        
        self.last_scan = time.time()
        elapsed = time.time() - start_time
        
        logger.info(f"✅ Scan complete: Found {len(self.apps)} apps in {elapsed:.2f}s")
        self.save_cache()
    
    # ==========================================
    # SCAN START MENU
    # ==========================================
    
    def _scan_start_menu(self):
        """Scan Start Menu shortcuts."""
        start_menu_paths = [
            os.environ.get("ProgramData", "C:\\ProgramData") + r"\Microsoft\Windows\Start Menu\Programs",
            os.environ.get("APPDATA", "") + r"\Microsoft\Windows\Start Menu\Programs",
        ]
        
        for path in start_menu_paths:
            if not path or not os.path.exists(path):
                continue
            
            self._scan_directory_for_shortcuts(path)
    
    def _scan_directory_for_shortcuts(self, path: str, depth: int = 0):
        """Recursively scan a directory for shortcuts."""
        if depth > 5:  # Limit depth
            return
        
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                
                if os.path.isdir(item_path):
                    self._scan_directory_for_shortcuts(item_path, depth + 1)
                else:
                    # Check if it's a shortcut or executable
                    if item.endswith('.lnk'):
                        self._add_shortcut(item_path)
                    elif item.endswith('.exe'):
                        self._add_executable(item_path)
        except (PermissionError, OSError):
            pass
    
    def _add_shortcut(self, path: str):
        """Add a shortcut to the app database."""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(path)
            target = shortcut.TargetPath
            
            if not target or not os.path.exists(target):
                return
            
            name = Path(path).stem
            display_name = self._get_friendly_name(name, target)
            
            self.apps[display_name] = {
                "name": display_name,
                "path": target,
                "type": "shortcut",
                "shortcut_path": path
            }
            self.app_paths[display_name] = target
            
        except Exception as e:
            # Fallback: use the file name
            name = Path(path).stem
            self.apps[name] = {
                "name": name,
                "path": path,
                "type": "shortcut"
            }
            self.app_paths[name] = path
    
    # ==========================================
    # SCAN PROGRAM FILES
    # ==========================================
    
    def _scan_program_files(self):
        """Scan Program Files directories."""
        program_paths = [
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", "") + r"\Programs",
            os.environ.get("APPDATA", "") + r"\Programs",
        ]
        
        for path in program_paths:
            if not path or not os.path.exists(path):
                continue
            
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    
                    if os.path.isdir(item_path):
                        # Check for executable with same name
                        exe_path = os.path.join(item_path, item + '.exe')
                        if os.path.exists(exe_path):
                            self._add_executable(exe_path)
                        else:
                            # Search for any exe in this directory (limited depth)
                            self._scan_directory_for_executables(item_path, 2)
                    elif item.endswith('.exe'):
                        self._add_executable(item_path)
            except (PermissionError, OSError):
                pass
    
    def _scan_directory_for_executables(self, path: str, depth: int):
        """Scan a directory for executables (limited depth)."""
        if depth <= 0:
            return
        
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    self._scan_directory_for_executables(item_path, depth - 1)
                elif item.endswith('.exe'):
                    self._add_executable(item_path)
        except (PermissionError, OSError):
            pass
    
    def _add_executable(self, path: str):
        """Add an executable to the app database."""
        try:
            name = Path(path).stem
            display_name = self._get_friendly_name(name, path)
            
            # Skip if already added
            if display_name in self.apps:
                return
            
            self.apps[display_name] = {
                "name": display_name,
                "path": path,
                "type": "executable"
            }
            self.app_paths[display_name] = path
            
        except Exception as e:
            pass
    
    # ==========================================
    # SCAN WINDOWS APPS (UWP/Microsoft Store)
    # ==========================================
    
    def _scan_windows_apps(self):
        """Scan Windows Apps (UWP/Microsoft Store)."""
        try:
            # Use PowerShell to get UWP apps
            ps_script = """
            Get-StartApps | ForEach-Object {
                $app = $_
                try {
                    $manifest = Get-AppxPackage -Name $app.Name
                    if ($manifest) {
                        [PSCustomObject]@{
                            Name = $app.Name
                            DisplayName = $manifest.PackageFamilyName
                            AppId = $app.AppId
                            PackageName = $manifest.PackageFullName
                        }
                    }
                } catch {}
            } | ConvertTo-Json -Compress
            """
            
            result = subprocess.run(
                ['powershell', '-c', ps_script],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    apps = json.loads(result.stdout)
                    if not isinstance(apps, list):
                        apps = [apps]
                    
                    for app in apps:
                        if not app:
                            continue
                        
                        display_name = app.get('DisplayName') or app.get('Name')
                        app_id = app.get('AppId')
                        
                        if display_name and app_id:
                            # Clean display name
                            display_name = display_name.replace('_', ' ')
                            display_name = display_name.replace('-', ' ')
                            
                            # Extract meaningful name
                            parts = display_name.split('.')
                            if len(parts) > 1:
                                display_name = parts[-1]
                            
                            # Map common UWP apps
                            uwp_mapping = {
                                "Microsoft.WindowsCamera": "Camera",
                                "Microsoft.WindowsCalculator": "Calculator",
                                "Microsoft.WindowsAlarms": "Alarms",
                                "Microsoft.WindowsClock": "Clock",
                                "Microsoft.WindowsPhotos": "Photos",
                                "Microsoft.WindowsMail": "Mail",
                                "Microsoft.WindowsCalendar": "Calendar",
                                "Microsoft.WindowsMaps": "Maps",
                                "Microsoft.WindowsStore": "Store",
                                "Microsoft.WindowsSettings": "Settings",
                                "Microsoft.WindowsNotepad": "Notepad",
                                "Microsoft.WindowsPaint": "Paint",
                                "Microsoft.WindowsClipchamp": "Clipchamp",
                                "Microsoft.WindowsMediaPlayer": "Media Player",
                                "Microsoft.WindowsMovies": "Movies & TV",
                                "Microsoft.WindowsSoundRecorder": "Sound Recorder",
                                "Microsoft.WindowsVoiceRecorder": "Voice Recorder",
                                "Microsoft.WindowsAlarmClock": "Alarm Clock",
                                "Microsoft.WindowsWeather": "Weather",
                                "Microsoft.WindowsTips": "Tips",
                                "Microsoft.WindowsXbox": "Xbox",
                                "Microsoft.WindowsSpotify": "Spotify",
                                "Microsoft.WindowsNetflix": "Netflix",
                                "Microsoft.WindowsPrimeVideo": "Prime Video",
                                "Microsoft.WindowsHotstar": "Hotstar",
                            }
                            
                            # Check if it's a known UWP app
                            for key, value in uwp_mapping.items():
                                if key in display_name or key in app_id:
                                    display_name = value
                                    break
                            
                            self.uwp_apps[display_name] = app_id
                            self.apps[display_name] = {
                                "name": display_name,
                                "appid": app_id,
                                "type": "uwp"
                            }
                            self.app_paths[display_name] = f"shell:AppsFolder\\{app_id}"
                            
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            logger.debug(f"UWP scan error: {e}")
    
    # ==========================================
    # SCAN DESKTOP
    # ==========================================
    
    def _scan_desktop(self):
        """Scan Desktop shortcuts."""
        desktop_paths = [
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
            os.path.join(os.environ.get("PUBLIC", ""), "Desktop"),
            os.environ.get("DESKTOP", ""),
        ]
        
        for path in desktop_paths:
            if not path or not os.path.exists(path):
                continue
            
            self._scan_directory_for_shortcuts(path)
    
    # ==========================================
    # SCAN REGISTRY
    # ==========================================
    
    def _scan_registry(self):
        """Scan registry for installed programs."""
        try:
            registry_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ]
            
            for reg_path in registry_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        for i in range(0, winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        if display_name:
                                            # Get install location
                                            try:
                                                install_path = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                            except:
                                                install_path = None
                                            
                                            # Get display icon path
                                            try:
                                                icon_path = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                            except:
                                                icon_path = None
                                            
                                            # Clean up the name
                                            display_name = display_name.strip()
                                            if display_name and display_name not in self.apps:
                                                # Try to find the executable
                                                if install_path and os.path.exists(install_path):
                                                    # Check for exe in install path
                                                    for file in os.listdir(install_path):
                                                        if file.endswith('.exe'):
                                                            self._add_executable(os.path.join(install_path, file))
                                                            break
                                                elif icon_path and os.path.exists(icon_path):
                                                    self.apps[display_name] = {
                                                        "name": display_name,
                                                        "path": icon_path,
                                                        "type": "registry"
                                                    }
                                                    self.app_paths[display_name] = icon_path
                                                else:
                                                    # Add with just name
                                                    self.apps[display_name] = {
                                                        "name": display_name,
                                                        "type": "registry"
                                                    }
                                    except:
                                        pass
                            except:
                                pass
                except:
                    pass
        except Exception as e:
            logger.debug(f"Registry scan error: {e}")
    
    # ==========================================
    # BUILT-IN ALIASES
    # ==========================================
    
    def _add_builtin_aliases(self):
        """Add built-in aliases for common apps."""
        aliases = {
            # System
            "calc": "Calculator",
            "calculator": "Calculator",
            "notepad": "Notepad",
            "paint": "Paint",
            "cmd": "Command Prompt",
            "command prompt": "Command Prompt",
            "powershell": "PowerShell",
            "explorer": "File Explorer",
            "file explorer": "File Explorer",
            "task manager": "Task Manager",
            "taskmgr": "Task Manager",
            "control panel": "Control Panel",
            "settings": "Settings",
            "store": "Microsoft Store",
            "microsoft store": "Microsoft Store",
            "regedit": "Registry Editor",
            "registry editor": "Registry Editor",
            "device manager": "Device Manager",
            "disk management": "Disk Management",
            "services": "Services",
            "event viewer": "Event Viewer",
            "snipping tool": "Snipping Tool",
            "screenshot": "Snipping Tool",
            
            # Browsers
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "browser": "Google Chrome",
            "firefox": "Firefox",
            "edge": "Microsoft Edge",
            "microsoft edge": "Microsoft Edge",
            "opera": "Opera",
            "brave": "Brave",
            
            # Office
            "word": "Microsoft Word",
            "excel": "Microsoft Excel",
            "powerpoint": "Microsoft PowerPoint",
            "outlook": "Microsoft Outlook",
            "onenote": "Microsoft OneNote",
            
            # Development
            "vscode": "Visual Studio Code",
            "visual studio code": "Visual Studio Code",
            "code": "Visual Studio Code",
            "visual studio": "Visual Studio",
            "pycharm": "PyCharm",
            "intellij": "IntelliJ IDEA",
            "sublime": "Sublime Text",
            "sublime text": "Sublime Text",
            "notepad++": "Notepad++",
            "notepad plus plus": "Notepad++",
            "git": "Git Bash",
            "git bash": "Git Bash",
            "github": "GitHub Desktop",
            "github desktop": "GitHub Desktop",
            
            # Media
            "spotify": "Spotify",
            "vlc": "VLC Media Player",
            "media player": "Windows Media Player",
            "windows media player": "Windows Media Player",
            
            # Communication
            "discord": "Discord",
            "slack": "Slack",
            "teams": "Microsoft Teams",
            "microsoft teams": "Microsoft Teams",
            "zoom": "Zoom",
            "skype": "Skype",
            "telegram": "Telegram",
            "whatsapp": "WhatsApp",
            
            # UWP Apps
            "camera": "Camera",
            "clock": "Clock",
            "alarm": "Alarms",
            "photos": "Photos",
            "gallery": "Photos",
            "mail": "Mail",
            "calendar": "Calendar",
            "maps": "Maps",
            "weather": "Weather",
            "calculator": "Calculator",
            "music": "Spotify",
            "movies": "Movies & TV",
            "clipchamp": "Clipchamp",
            
            # AI Apps
            "chatgpt": "ChatGPT",
            "chat gpt": "ChatGPT",
            "gpt": "ChatGPT",
            "claude": "Claude",
            "copilot": "Microsoft Copilot",
            "gemini": "Gemini",
            
            # Games
            "steam": "Steam",
            "epic": "Epic Games Launcher",
            "epic games": "Epic Games Launcher",
            "minecraft": "Minecraft",
            "roblox": "Roblox",
            
            # Utilities
            "7zip": "7-Zip",
            "winrar": "WinRAR",
            "ccleaner": "CCleaner",
            "malwarebytes": "Malwarebytes",
            
            # Adobe
            "photoshop": "Adobe Photoshop",
            "adobe photoshop": "Adobe Photoshop",
            "illustrator": "Adobe Illustrator",
            "adobe illustrator": "Adobe Illustrator",
            "premiere": "Adobe Premiere",
            "adobe premiere": "Adobe Premiere",
            "after effects": "Adobe After Effects",
            "adobe after effects": "Adobe After Effects",
            "acrobat": "Adobe Acrobat",
            "adobe acrobat": "Adobe Acrobat",
            "reader": "Adobe Reader",
            "adobe reader": "Adobe Reader",
        }
        
        # Add aliases that point to actual app names
        for alias, target in aliases.items():
            if target in self.apps:
                self.aliases[alias] = target
            # Also check if target might be in UWP apps
            elif target in self.uwp_apps:
                self.aliases[alias] = target
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    def _get_friendly_name(self, name: str, path: str) -> str:
        """Get a friendly display name from a file name or path."""
        # Common name mappings
        name_mapping = {
            "code": "Visual Studio Code",
            "winword": "Microsoft Word",
            "excel": "Microsoft Excel",
            "powerpnt": "Microsoft PowerPoint",
            "outlook": "Microsoft Outlook",
            "chrome": "Google Chrome",
            "msedge": "Microsoft Edge",
            "firefox": "Firefox",
            "notepad": "Notepad",
            "calc": "Calculator",
            "mspaint": "Paint",
            "explorer": "File Explorer",
            "taskmgr": "Task Manager",
            "control": "Control Panel",
            "regedit": "Registry Editor",
            "devmgmt": "Device Manager",
            "diskmgmt": "Disk Management",
            "eventvwr": "Event Viewer",
            "services": "Services",
        }
        
        name_lower = name.lower()
        if name_lower in name_mapping:
            return name_mapping[name_lower]
        
        # Check if it's a common pattern
        if "visual studio" in name_lower:
            return "Visual Studio"
        if "git" in name_lower and "bash" in name_lower:
            return "Git Bash"
        if "python" in name_lower:
            return "Python"
        
        # Return cleaned name
        return name.replace('_', ' ').replace('-', ' ').strip()
    
    def find_app(self, query: str, threshold: int = 80) -> Optional[Dict]:
        """
        Find an application by name using fuzzy matching.
        Returns app info or None if not found.
        """
        if not query:
            return None
        
        query_lower = query.lower().strip()
        
        # 1. Check direct alias match
        if query_lower in self.aliases:
            target = self.aliases[query_lower]
            if target in self.apps:
                return self.apps[target]
            elif target in self.uwp_apps:
                return {
                    "name": target,
                    "appid": self.uwp_apps[target],
                    "type": "uwp"
                }
        
        # 2. Check direct app name match
        for app_name, app_info in self.apps.items():
            if app_name.lower() == query_lower:
                return app_info
        
        # 3. Check UWP apps
        for app_name, app_id in self.uwp_apps.items():
            if app_name.lower() == query_lower:
                return {
                    "name": app_name,
                    "appid": app_id,
                    "type": "uwp"
                }
        
        # 4. Fuzzy match
        all_names = list(self.apps.keys()) + list(self.uwp_apps.keys())
        if not all_names:
            return None
        
        # Use rapidfuzz for better matching
        matches = process.extract(
            query,
            all_names,
            scorer=fuzz.WRatio,
            limit=5
        )
        
        for match in matches:
            if match[1] >= threshold:
                app_name = match[0]
                if app_name in self.apps:
                    return self.apps[app_name]
                elif app_name in self.uwp_apps:
                    return {
                        "name": app_name,
                        "appid": self.uwp_apps[app_name],
                        "type": "uwp"
                    }
        
        return None
    
    def get_app_path(self, app_name: str) -> Optional[str]:
        """Get the path or AppID for an application."""
        app = self.find_app(app_name)
        if not app:
            return None
        
        if app.get("type") == "uwp":
            return f"shell:AppsFolder\\{app.get('appid')}"
        else:
            return app.get("path")
    
    def get_display_name(self, app_name: str) -> Optional[str]:
        """Get the display name for an application."""
        app = self.find_app(app_name)
        if not app:
            return None
        return app.get("name")
    
    def list_all_apps(self) -> List[str]:
        """Get a list of all discovered applications."""
        return sorted(list(self.apps.keys()) + list(self.uwp_apps.keys()))
    
    def get_app_info(self, app_name: str) -> Dict:
        """Get full application info."""
        app = self.find_app(app_name)
        if not app:
            return {}
        
        # Get alias info
        aliases = []
        for alias, target in self.aliases.items():
            if target == app.get("name"):
                aliases.append(alias)
        
        return {
            **app,
            "aliases": aliases,
            "has_alias": len(aliases) > 0
        }