"""
moa/execution_engine.py
Execution Engine - REAL OS operations (NO LLM)
With Auto-Scan for installed applications
"""

import os
import subprocess
import psutil
import requests
import logging
import platform
import shutil
import webbrowser
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("jarvis.execution_engine")


class ExecutionEngine:
    """
    Executes system actions.
    
    RULE: NEVER use LLM for system actions.
    These are REAL OS operations.
    """
    
    def __init__(self, auto_scan: bool = True):
        # Comprehensive app aliases with proper executable names
        self.app_aliases = {
            # System apps
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "notepad": "notepad.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "cmd": "cmd.exe",
            "command prompt": "cmd.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "task manager": "taskmgr.exe",
            "taskmgr": "taskmgr.exe",
            "control panel": "control.exe",
            "settings": "ms-settings:",
            "store": "ms-windows-store:",
            "microsoft store": "ms-windows-store:",
            "regedit": "regedit.exe",
            "registry editor": "regedit.exe",
            "device manager": "devmgmt.msc",
            "disk management": "diskmgmt.msc",
            "services": "services.msc",
            "event viewer": "eventvwr.msc",
            
            # UWP Apps - Using correct protocol handlers
            "camera": "windows.camera:",
            "clock": "ms-clock:",
            "alarms": "ms-clock:",
            "photos": "ms-photos:",
            "gallery": "ms-photos:",
            "mail": "outlookmail:",
            "calendar": "outlookcal:",
            "maps": "bingmaps:",
            "weather": "ms-weather:",
            "music": "ms-music:",
            "movies": "ms-video:",
            "tv": "ms-video:",
            "clipchamp": "ms-clipchamp:",
            "calculator": "calc.exe",
            
            # Browsers
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "microsoft edge": "msedge.exe",
            "browser": "chrome.exe",
            "opera": "opera.exe",
            "brave": "brave.exe",
            "vivaldi": "vivaldi.exe",
            
            # Office
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
            "outlook": "OUTLOOK.EXE",
            "onenote": "ONENOTE.EXE",
            "access": "MSACCESS.EXE",
            "publisher": "MSPUB.EXE",
            
            # Development
            "vscode": "code.exe",
            "visual studio code": "code.exe",
            "code": "code.exe",
            "visual studio": "devenv.exe",
            "pycharm": "pycharm64.exe",
            "intellij": "idea64.exe",
            "sublime": "sublime_text.exe",
            "sublime text": "sublime_text.exe",
            "notepad++": "notepad++.exe",
            "notepad plus plus": "notepad++.exe",
            "git": "git.exe",
            "git bash": "git-bash.exe",
            "github desktop": "GitHubDesktop.exe",
            
            # Media
            "spotify": "Spotify.exe",
            "vlc": "vlc.exe",
            "media player": "wmplayer.exe",
            "windows media player": "wmplayer.exe",
            "winamp": "winamp.exe",
            "foobar2000": "foobar2000.exe",
            "itunes": "iTunes.exe",
            "audacity": "audacity.exe",
            
            # Communication
            "discord": "Discord.exe",
            "slack": "slack.exe",
            "teams": "Teams.exe",
            "microsoft teams": "Teams.exe",
            "zoom": "Zoom.exe",
            "zoom meeting": "Zoom.exe",
            "skype": "Skype.exe",
            "telegram": "Telegram.exe",
            "whatsapp": "WhatsApp.exe",
            "signal": "Signal.exe",
            
            # Games
            "steam": "steam.exe",
            "epic games": "EpicGamesLauncher.exe",
            "epic": "EpicGamesLauncher.exe",
            "ubisoft": "UbisoftConnect.exe",
            "minecraft": "Minecraft.exe",
            "roblox": "RobloxPlayerLauncher.exe",
            
            # Utility
            "7zip": "7zFM.exe",
            "winrar": "WinRAR.exe",
            "winzip": "WINZIP32.EXE",
            "ccleaner": "CCleaner64.exe",
            "malwarebytes": "MBAMService.exe",
            
            # Adobe
            "photoshop": "Photoshop.exe",
            "adobe photoshop": "Photoshop.exe",
            "illustrator": "Illustrator.exe",
            "adobe illustrator": "Illustrator.exe",
            "premiere": "Premiere.exe",
            "adobe premiere": "Premiere.exe",
            "after effects": "AfterFX.exe",
            "adobe after effects": "AfterFX.exe",
            "reader": "Acrobat.exe",
            "adobe reader": "Acrobat.exe",
            "acrobat": "Acrobat.exe",
            
            # Web apps (open in browser)
            "chat gpt": "https://chat.openai.com",
            "chatgpt": "https://chat.openai.com",
            "gpt": "https://chat.openai.com",
            "claude": "https://claude.ai",
            "copilot": "https://copilot.microsoft.com",
            "gemini": "https://gemini.google.com",
            "perplexity": "https://perplexity.ai",
            "deepseek": "https://chat.deepseek.com",
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "gmail": "https://gmail.com",
            "github": "https://github.com",
            "stackoverflow": "https://stackoverflow.com",
            "reddit": "https://reddit.com",
            "twitter": "https://twitter.com",
            "x": "https://x.com",
            "linkedin": "https://linkedin.com",
            "facebook": "https://facebook.com",
            "instagram": "https://instagram.com",
            "amazon": "https://amazon.com",
            "flipkart": "https://flipkart.com",
            "netflix": "https://netflix.com",
            "prime video": "https://primevideo.com",
            "hotstar": "https://hotstar.com",
            "spotify web": "https://spotify.com",
        }
        
        # Cache for resolved paths
        self._app_path_cache = {}
        self._installed_apps_cache = None
        self._cache_time = None
        self._cache_duration = 300  # 5 minutes
        
        # Location cache
        self._location_cache = None
        self._loc_cache_time = None
        self._loc_cache_duration = 300  # 5 minutes
        
        # =================================================
        # AUTO-SCAN: Scan for installed applications
        # =================================================
        self._app_discovery_cache = {}
        self._last_scan_time = 0
        self._scan_interval = 3600  # 1 hour
        
        # Known UWP app protocols
        self.uwp_protocols = {
            "camera": "windows.camera:",
            "clock": "ms-clock:",
            "alarms": "ms-clock:",
            "photos": "ms-photos:",
            "gallery": "ms-photos:",
            "mail": "outlookmail:",
            "calendar": "outlookcal:",
            "maps": "bingmaps:",
            "weather": "ms-weather:",
            "music": "ms-music:",
            "movies": "ms-video:",
            "tv": "ms-video:",
            "clipchamp": "ms-clipchamp:",
            "settings": "ms-settings:",
            "store": "ms-windows-store:",
            "calculator": "calc.exe",
        }
        
        if auto_scan:
            print("🔍 Scanning for installed applications...")
            self._scan_installed_apps()
            print(f"✅ Found {len(self._app_discovery_cache)} applications ready to launch!")
    
    # =================================================
    # AUTO-SCAN: Discover installed applications
    # =================================================
    
    def _scan_installed_apps(self, force: bool = False):
        """
        Scan for all installed applications on the system.
        This runs automatically on startup.
        """
        current_time = time.time()
        
        # Check if cache is fresh
        if not force and (current_time - self._last_scan_time) < self._scan_interval:
            logger.debug("Using cached app list (fresh)")
            return
        
        logger.info("🔍 Scanning for installed applications...")
        start_time = time.time()
        
        discovered_apps = {}
        
        # 1. Scan Start Menu
        self._scan_start_menu(discovered_apps)
        
        # 2. Scan Program Files
        self._scan_program_files(discovered_apps)
        
        # 3. Scan Windows Apps (UWP)
        self._scan_windows_apps(discovered_apps)
        
        # 4. Scan Desktop
        self._scan_desktop(discovered_apps)
        
        # 5. Scan Registry
        self._scan_registry(discovered_apps)
        
        # Update cache
        self._app_discovery_cache = discovered_apps
        self._last_scan_time = current_time
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Scan complete: Found {len(discovered_apps)} apps in {elapsed:.2f}s")
        
        # Add built-in aliases
        self._add_builtin_aliases(discovered_apps)
    
    def _scan_start_menu(self, apps: Dict):
        """Scan Start Menu shortcuts."""
        start_menu_paths = [
            os.environ.get("ProgramData", "C:\\ProgramData") + r"\Microsoft\Windows\Start Menu\Programs",
            os.environ.get("APPDATA", "") + r"\Microsoft\Windows\Start Menu\Programs",
        ]
        
        for path in start_menu_paths:
            if not path or not os.path.exists(path):
                continue
            self._scan_directory_for_shortcuts(path, apps)
    
    def _scan_directory_for_shortcuts(self, path: str, apps: Dict, depth: int = 0):
        """Recursively scan a directory for shortcuts."""
        if depth > 5:
            return
        
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                
                if os.path.isdir(item_path):
                    self._scan_directory_for_shortcuts(item_path, apps, depth + 1)
                else:
                    if item.endswith('.lnk'):
                        self._add_shortcut(item_path, apps)
                    elif item.endswith('.exe'):
                        self._add_executable(item_path, apps)
        except (PermissionError, OSError):
            pass
    
    def _add_shortcut(self, path: str, apps: Dict):
        """Add a shortcut to the app list."""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(path)
            target = shortcut.TargetPath
            
            if not target or not os.path.exists(target):
                return
            
            name = Path(path).stem
            display_name = self._get_friendly_name(name, target)
            
            if display_name not in apps:
                apps[display_name] = {
                    "name": display_name,
                    "path": target,
                    "type": "shortcut",
                    "shortcut_path": path
                }
        except Exception:
            # Fallback
            name = Path(path).stem
            if name not in apps:
                apps[name] = {
                    "name": name,
                    "path": path,
                    "type": "shortcut"
                }
    
    def _scan_program_files(self, apps: Dict):
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
                            self._add_executable(exe_path, apps)
                        else:
                            self._scan_directory_for_executables(item_path, apps, 2)
                    elif item.endswith('.exe'):
                        self._add_executable(item_path, apps)
            except (PermissionError, OSError):
                pass
    
    def _scan_directory_for_executables(self, path: str, apps: Dict, depth: int):
        """Scan a directory for executables (limited depth)."""
        if depth <= 0:
            return
        
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    self._scan_directory_for_executables(item_path, apps, depth - 1)
                elif item.endswith('.exe'):
                    self._add_executable(item_path, apps)
        except (PermissionError, OSError):
            pass
    
    def _add_executable(self, path: str, apps: Dict):
        """Add an executable to the app list."""
        try:
            name = Path(path).stem
            display_name = self._get_friendly_name(name, path)
            
            if display_name not in apps:
                apps[display_name] = {
                    "name": display_name,
                    "path": path,
                    "type": "executable"
                }
        except Exception:
            pass
    
    def _scan_windows_apps(self, apps: Dict):
        """Scan Windows Apps (UWP/Microsoft Store)."""
        try:
            # Get UWP apps using PowerShell
            ps_script = """
            Get-AppxPackage | ForEach-Object {
                $pkg = $_
                $display_name = $pkg.PackageFamilyName
                # Try to get the app name
                try {
                    $manifest = Get-AppxPackageManifest $pkg
                    $app_name = $manifest.Package.Properties.DisplayName
                    if ($app_name) {
                        $display_name = $app_name
                    }
                } catch {}
                
                [PSCustomObject]@{
                    Name = $display_name
                    PackageFullName = $pkg.PackageFullName
                    PackageFamilyName = $pkg.PackageFamilyName
                }
            } | ConvertTo-Json -Compress
            """
            
            result = subprocess.run(
                ['powershell', '-c', ps_script],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                try:
                    uwp_apps = json.loads(result.stdout)
                    if not isinstance(uwp_apps, list):
                        uwp_apps = [uwp_apps]
                    
                    # UWP app name mapping for common apps
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
                        "Microsoft.WindowsWeather": "Weather",
                        "Microsoft.WindowsXbox": "Xbox",
                        "Microsoft.Spotify": "Spotify",
                        "Microsoft.Netflix": "Netflix",
                        "Microsoft.PrimeVideo": "Prime Video",
                    }
                    
                    for app in uwp_apps:
                        if not app:
                            continue
                        
                        display_name = app.get('Name') or app.get('PackageFamilyName')
                        if not display_name:
                            continue
                        
                        # Clean up the name
                        display_name = display_name.replace('_', ' ').replace('-', ' ')
                        parts = display_name.split('.')
                        if len(parts) > 1:
                            display_name = parts[-1]
                        
                        # Check if it's a known UWP app
                        for key, value in uwp_mapping.items():
                            if key in display_name or key in app.get('PackageFullName', ''):
                                display_name = value
                                break
                        
                        # Check if we have a protocol for this app
                        protocol = None
                        if display_name.lower() in self.uwp_protocols:
                            protocol = self.uwp_protocols[display_name.lower()]
                        
                        if display_name not in apps:
                            apps[display_name] = {
                                "name": display_name,
                                "package": app.get('PackageFullName'),
                                "type": "uwp",
                                "protocol": protocol
                            }
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug(f"UWP scan error: {e}")
    
    def _scan_desktop(self, apps: Dict):
        """Scan Desktop shortcuts."""
        desktop_paths = [
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
            os.path.join(os.environ.get("PUBLIC", ""), "Desktop"),
            os.environ.get("DESKTOP", ""),
        ]
        
        for path in desktop_paths:
            if not path or not os.path.exists(path):
                continue
            self._scan_directory_for_shortcuts(path, apps)
    
    def _scan_registry(self, apps: Dict):
        """Scan registry for installed programs."""
        try:
            import winreg
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
                                            display_name = display_name.strip()
                                            if display_name and display_name not in apps:
                                                try:
                                                    install_path = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                                    if install_path and os.path.exists(install_path):
                                                        for file in os.listdir(install_path):
                                                            if file.endswith('.exe'):
                                                                self._add_executable(os.path.join(install_path, file), apps)
                                                                break
                                                except:
                                                    apps[display_name] = {
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
    
    def _get_friendly_name(self, name: str, path: str) -> str:
        """Get a friendly display name."""
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
        
        return name.replace('_', ' ').replace('-', ' ').strip()
    
    def _add_builtin_aliases(self, apps: Dict):
        """Add built-in aliases for common apps."""
        aliases = {
            "calc": "Calculator",
            "calculator": "Calculator",
            "notepad": "Notepad",
            "paint": "Paint",
            "cmd": "Command Prompt",
            "powershell": "PowerShell",
            "explorer": "File Explorer",
            "task manager": "Task Manager",
            "control panel": "Control Panel",
            "settings": "Settings",
            "store": "Microsoft Store",
            "regedit": "Registry Editor",
            "device manager": "Device Manager",
            "disk management": "Disk Management",
            "services": "Services",
            "event viewer": "Event Viewer",
            "snipping tool": "Snipping Tool",
            "chrome": "Google Chrome",
            "browser": "Google Chrome",
            "firefox": "Firefox",
            "edge": "Microsoft Edge",
            "word": "Microsoft Word",
            "excel": "Microsoft Excel",
            "powerpoint": "Microsoft PowerPoint",
            "outlook": "Microsoft Outlook",
            "vscode": "Visual Studio Code",
            "code": "Visual Studio Code",
            "spotify": "Spotify",
            "vlc": "VLC Media Player",
            "discord": "Discord",
            "slack": "Slack",
            "teams": "Microsoft Teams",
            "zoom": "Zoom",
            "skype": "Skype",
            "telegram": "Telegram",
            "whatsapp": "WhatsApp",
            "camera": "Camera",
            "clock": "Clock",
            "photos": "Photos",
            "mail": "Mail",
            "calendar": "Calendar",
            "maps": "Maps",
            "weather": "Weather",
            "music": "Music",
            "movies": "Movies & TV",
            "clipchamp": "Clipchamp",
            "chatgpt": "ChatGPT",
            "claude": "Claude",
            "copilot": "Microsoft Copilot",
            "gemini": "Gemini",
        }
        
        for alias, target in aliases.items():
            if target in apps:
                self.app_aliases[alias] = self.app_aliases.get(alias, target)
    
    # =================================================
    # RESOLVE APP PATH
    # =================================================
    
    def _resolve_app_path(self, app_name: str) -> Optional[str]:
        """
        Resolve the full path of an application.
        """
        # Check cache
        if app_name in self._app_path_cache:
            return self._app_path_cache[app_name]
        
        # Check discovery cache
        app_name_lower = app_name.lower()
        for name, info in self._app_discovery_cache.items():
            if name.lower() == app_name_lower:
                path = info.get("path")
                if path and os.path.exists(path):
                    self._app_path_cache[app_name] = path
                    return path
                # Check for protocol
                protocol = info.get("protocol")
                if protocol:
                    self._app_path_cache[app_name] = protocol
                    return protocol
        
        # Check alias
        if app_name in self.app_aliases:
            alias = self.app_aliases[app_name]
            if alias.startswith("http") or alias.startswith("ms-"):
                self._app_path_cache[app_name] = alias
                return alias
        
        # Check if it's a known UWP protocol
        if app_name_lower in self.uwp_protocols:
            protocol = self.uwp_protocols[app_name_lower]
            self._app_path_cache[app_name] = protocol
            return protocol
        
        # Method 1: Check if it's already a full path
        if os.path.exists(app_name):
            self._app_path_cache[app_name] = app_name
            return app_name
        
        # Method 2: Use shutil.which
        app_path = shutil.which(app_name)
        if app_path:
            self._app_path_cache[app_name] = app_path
            return app_path
        
        # Method 3: Check with .exe extension
        if not app_name.endswith('.exe') and not app_name.endswith('.msc'):
            app_path = shutil.which(app_name + '.exe')
            if app_path:
                self._app_path_cache[app_name] = app_path
                return app_path
        
        # Method 4: Check common Windows paths
        windows_paths = [
            r"C:\Windows\System32",
            r"C:\Windows\SysWOW64",
            r"C:\Program Files",
            r"C:\Program Files (x86)",
            os.environ.get("ProgramFiles", ""),
            os.environ.get("ProgramFiles(x86)", ""),
            os.environ.get("LOCALAPPDATA", "") + r"\Programs",
            os.environ.get("APPDATA", "") + r"\Programs",
        ]
        
        for base_path in windows_paths:
            if not base_path or not os.path.exists(base_path):
                continue
            
            test_path = os.path.join(base_path, app_name)
            if (app_name.endswith('.exe') or app_name.endswith('.msc')) and os.path.exists(test_path):
                self._app_path_cache[app_name] = test_path
                return test_path
            
            if not app_name.endswith('.exe') and not app_name.endswith('.msc'):
                test_path = os.path.join(base_path, app_name + '.exe')
                if os.path.exists(test_path):
                    self._app_path_cache[app_name] = test_path
                    return test_path
        
        # Not found
        self._app_path_cache[app_name] = None
        return None
    
    # =================================================
    # APP LAUNCH - FIXED: Uses os.startfile for reliability
    # =================================================
    
    def launch_app(self, app: str) -> Dict[str, Any]:
        """Launch an application - REAL OS call."""
        app = app.strip().lower()
        
        # Check alias first
        app = self.app_aliases.get(app, app)
        
        # If it's a URL (web app), open in browser
        if app.startswith("http"):
            try:
                webbrowser.open(app)
                return {
                    "success": True,
                    "message": f"Opening {app} in your browser...",
                    "app": app,
                    "mode": "launch"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Could not open {app}: {str(e)}",
                    "app": app,
                    "mode": "launch"
                }
        
        # 🔧 FIX: Use os.startfile for URI protocols (UWP)
        if app.startswith("ms-") or app.startswith("windows.") or app.startswith("outlook"):
            try:
                os.startfile(app)
                friendly_name = self._get_friendly_name_from_protocol(app)
                return {
                    "success": True,
                    "message": f"Opening {friendly_name}...",
                    "app": app,
                    "mode": "launch",
                    "type": "uwp"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Could not open {app}: {str(e)}",
                    "app": app,
                    "mode": "launch"
                }
        
        # Resolve the full path
        app_path = self._resolve_app_path(app)
        
        if app_path:
            try:
                # 🔧 FIX: Use os.startfile for Windows (more reliable)
                if platform.system() == "Windows":
                    os.startfile(app_path)
                else:
                    subprocess.Popen([app_path])
                
                friendly_name = self._get_friendly_name_from_path(app_path, app)
                
                return {
                    "success": True,
                    "message": f"Opening {friendly_name}...",
                    "app": friendly_name,
                    "path": app_path,
                    "mode": "launch"
                }
            except Exception as e:
                logger.error(f"Launch error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Could not open {app}: {str(e)}",
                    "app": app,
                    "mode": "launch"
                }
        else:
            # Last resort: try os.startfile with app name
            try:
                os.startfile(app)
                return {
                    "success": True,
                    "message": f"Opening {app}...",
                    "app": app,
                    "mode": "launch"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "message": f"Could not find or open {app}. Please check the app name.",
                    "app": app,
                    "mode": "launch"
                }
    
    def _get_friendly_name_from_protocol(self, protocol: str) -> str:
        """Get friendly name from protocol."""
        protocol_map = {
            "ms-music:": "Music",
            "ms-clock:": "Clock",
            "ms-photos:": "Photos",
            "ms-video:": "Movies & TV",
            "ms-weather:": "Weather",
            "ms-settings:": "Settings",
            "ms-windows-store:": "Microsoft Store",
            "ms-clipchamp:": "Clipchamp",
            "outlookmail:": "Mail",
            "outlookcal:": "Calendar",
            "bingmaps:": "Maps",
            "windows.camera:": "Camera",
        }
        
        for key, value in protocol_map.items():
            if key in protocol:
                return value
        return protocol.replace(":", "").replace("ms-", "").capitalize()
    
    def _get_friendly_name_from_path(self, path: str, default: str) -> str:
        """Get friendly name from path."""
        if not path:
            return default
        
        # Check discovery cache
        for name, info in self._app_discovery_cache.items():
            if info.get("path") == path:
                return info.get("name", default)
        
        # Check name mapping
        name = Path(path).stem
        name_mapping = {
            "code": "Visual Studio Code",
            "winword": "Microsoft Word",
            "excel": "Microsoft Excel",
            "powerpnt": "Microsoft PowerPoint",
            "outlook": "Microsoft Outlook",
            "chrome": "Google Chrome",
            "msedge": "Microsoft Edge",
            "firefox": "Firefox",
        }
        
        return name_mapping.get(name, default)
    
    # =================================================
    # APP CLOSE - FIXED: Returns proper error messages
    # =================================================
    
    def close_app(self, app: str, force: bool = False) -> Dict[str, Any]:
        """Close an application."""
        app = app.strip().lower()
        
        # Clean app name
        app = re.sub(r'^the\s+', '', app)
        app = re.sub(r'\s+$', '', app)
        
        # Get the actual executable name from alias
        app_alias = self.app_aliases.get(app, app)
        
        # If it's a URL/web app, we can't close it
        if app_alias.startswith("http"):
            return {
                "success": False,
                "error": "Web app",
                "message": f"Cannot close web app '{app}'. Please close it in your browser.",
                "app": app,
                "mode": "close"
            }
        
        # If it's a URI protocol (UWP), we can't close it via process
        if app_alias.startswith("ms-") or app_alias.startswith("windows.") or app_alias.startswith("outlook"):
            return {
                "success": False,
                "error": "UWP app",
                "message": f"Cannot close UWP app '{app}'. Please close it manually.",
                "app": app,
                "mode": "close"
            }
        
        # Build list of process names to match
        process_names = []
        process_names.append(app_alias)
        
        if not app_alias.endswith('.exe') and not app_alias.endswith('.msc'):
            process_names.append(app_alias + '.exe')
        
        if app != app_alias:
            process_names.append(app)
            if not app.endswith('.exe') and not app.endswith('.msc'):
                process_names.append(app + '.exe')
        
        process_names.append(app_alias.lower())
        process_names.append(app_alias.upper())
        process_names.append(app_alias.capitalize())
        
        process_names = list(set([p.lower() for p in process_names]))
        
        try:
            killed = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name']
                    if proc_name:
                        proc_name_lower = proc_name.lower()
                        for match_name in process_names:
                            if (match_name == proc_name_lower or 
                                match_name in proc_name_lower or 
                                proc_name_lower in match_name):
                                if force:
                                    proc.kill()
                                else:
                                    proc.terminate()
                                killed.append({
                                    'pid': proc.info['pid'],
                                    'name': proc_name
                                })
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed:
                return {
                    "success": True,
                    "message": f"Closed {app} ({len(killed)} instance(s))",
                    "app": app,
                    "pids": killed,
                    "mode": "close"
                }
            else:
                # 🔧 FIX: Return proper error with message
                return {
                    "success": False,
                    "error": f"Could not find '{app}' running.",
                    "message": f"Could not find '{app}' running. Check if the app is open.",
                    "app": app,
                    "pids": [],
                    "mode": "close"
                }
        except Exception as e:
            # 🔧 FIX: Catch all exceptions
            logger.error(f"Close error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error closing {app}: {str(e)}",
                "app": app,
                "mode": "close"
            }
    
    # =================================================
    # LIST INSTALLED APPS
    # =================================================
    
    def list_installed_apps(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        List all installed applications on the system.
        """
        if force_refresh:
            self._scan_installed_apps(force=True)
        
        all_apps = sorted(self._app_discovery_cache.keys())
        
        return {
            "success": True,
            "apps": all_apps,
            "count": len(all_apps),
            "mode": "list_apps",
            "message": f"Found {len(all_apps)} installed applications"
        }
    
    # =================================================
    # TIME, DATE, WEATHER, LOCATION
    # =================================================
    
    def get_time(self) -> Dict[str, Any]:
        """Get current time."""
        now = datetime.now()
        return {
            "success": True,
            "time": now.strftime("%I:%M %p").lstrip("0"),
            "time_24h": now.strftime("%H:%M"),
            "date": now.strftime("%A, %d %B %Y"),
            "timestamp": now.isoformat(),
            "mode": "time",
            "answer": f"{now.strftime('%I:%M %p').lstrip('0')} on {now.strftime('%A, %d %B %Y')}"
        }
    
    def get_date(self) -> Dict[str, Any]:
        """Get current date."""
        now = datetime.now()
        return {
            "success": True,
            "date": now.strftime("%A, %d %B %Y"),
            "day": now.strftime("%A"),
            "day_number": now.strftime("%d"),
            "month": now.strftime("%B"),
            "year": now.strftime("%Y"),
            "mode": "date",
            "answer": now.strftime("%A, %d %B %Y")
        }
    
    def get_weather(self, city: str = "London") -> Dict[str, Any]:
        """Get weather."""
        try:
            api_key = os.getenv("OPENWEATHER_API_KEY", "")
            if not api_key:
                return {
                    "success": False,
                    "error": "OpenWeather API key not configured",
                    "message": "Weather service not configured. Add OPENWEATHER_API_KEY to .env",
                    "mode": "weather"
                }
            
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "city": data.get("name", city),
                    "temperature": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "conditions": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"],
                    "wind_speed": data["wind"]["speed"],
                    "mode": "weather",
                    "answer": f"{city}: {data['main']['temp']}°C, {data['weather'][0]['description']}, humidity {data['main']['humidity']}%, wind {data['wind']['speed']} m/s"
                }
            else:
                return {
                    "success": False,
                    "error": f"Weather API error: {response.status_code}",
                    "mode": "weather",
                    "answer": f"Could not get weather for {city}"
                }
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "weather",
                "answer": f"Weather service error: {str(e)}"
            }
    
    def get_location(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get current location."""
        if not force_refresh and hasattr(self, '_location_cache') and self._location_cache and hasattr(self, '_loc_cache_time') and self._loc_cache_time:
            if (time.time() - self._loc_cache_time) < self._loc_cache_duration:
                logger.debug("Returning cached location")
                return self._location_cache
        
        logger.info("📍 Fetching location...")
        
        try:
            response = requests.get("https://ipapi.co/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                location = {
                    "success": True,
                    "city": data.get("city", "Unknown"),
                    "region": data.get("region", "Unknown"),
                    "country": data.get("country_name", "Unknown"),
                    "lat": data.get("latitude", 0.0),
                    "lon": data.get("longitude", 0.0),
                    "timezone": data.get("timezone", "Unknown"),
                    "mode": "location",
                    "answer": f"{data.get('city', 'Unknown')}, {data.get('region', 'Unknown')}, {data.get('country_name', 'Unknown')}"
                }
                self._location_cache = location
                self._loc_cache_time = time.time()
                return location
        except Exception as e:
            logger.debug(f"Location error: {e}")
        
        return {
            "success": True,
            "city": "Unknown",
            "region": "Unknown",
            "country": "Unknown",
            "lat": 0.0,
            "lon": 0.0,
            "mode": "location",
            "answer": "Location unknown",
            "warning": "Could not determine location"
        }
    
    def refresh_location(self) -> Dict[str, Any]:
        """Force refresh location."""
        return self.get_location(force_refresh=True)
    
    def get_user_location(self) -> Dict[str, Any]:
        """Get the user's physical location."""
        return self.get_location()
    
    def get_location_history(self) -> Dict[str, Any]:
        """Get location history."""
        if self._location_cache:
            return {
                "success": True,
                "location": self._location_cache,
                "timestamp": datetime.fromtimestamp(self._loc_cache_time).isoformat() if self._loc_cache_time else None,
                "mode": "location_history"
            }
        else:
            return {
                "success": False,
                "error": "No location history available",
                "mode": "location_history",
                "answer": "No location history available"
            }
    
    def set_location_manually(self, city: str, region: str, country: str, lat: float = 0.0, lon: float = 0.0) -> Dict[str, Any]:
        """Manually set the user's location."""
        location = {
            "success": True,
            "city": city,
            "region": region,
            "country": country,
            "lat": lat,
            "lon": lon,
            "mode": "location",
            "answer": f"{city}, {region}, {country}",
            "provider": "manual"
        }
        self._location_cache = location
        self._loc_cache_time = datetime.now().timestamp()
        return location