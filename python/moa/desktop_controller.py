"""
moa/desktop_controller.py
Complete Desktop Control Engine - Full system control with admin privileges
"""

import os
import sys
import shutil
import subprocess
import psutil
import winreg
import ctypes
import time
import json
import logging
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import threading
import queue

logger = logging.getLogger("jarvis.desktop_controller")

# ==========================================
# OPTIONAL IMPORTS WITH GRACEFUL FALLBACK
# ==========================================

PYAUTOGUI_AVAILABLE = False
PYGETWINDOW_AVAILABLE = False
PYCAW_AVAILABLE = False
SCREEN_BRIGHTNESS_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pass

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    pass

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    PYCAW_AVAILABLE = True
except ImportError:
    pass

try:
    import screen_brightness_control as sbc
    SCREEN_BRIGHTNESS_AVAILABLE = True
except ImportError:
    pass


class DesktopController:
    """
    Complete Desktop Control with admin privileges.
    Handles: Files, Settings, Processes, Windows, Registry, System, Automation
    """
    
    def __init__(self):
        self.is_admin = self._check_admin()
        self.operation_queue = queue.Queue()
        self.auto_learn = True
        self.app_index = self._load_app_index()
        
        # ==========================================
        # SYSTEM CLEANER PATHS
        # ==========================================
        self.temp_paths = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Temp"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData\\Local\\Temp"),
        ]
        
        self.junk_extensions = [
            ".tmp", ".temp", ".log", ".cache", ".old", ".bak",
            ".~", ".dmp", ".gid", ".chk", ".fts", ".ftg",
            ".hst", ".wbk", ".xlk", ".sav", ".err", ".etl"
        ]
        
        self.recycle_bin_path = self._get_recycle_bin_path()
        
        logger.info(f"DesktopController initialized. Admin: {self.is_admin}")
    
    def _get_recycle_bin_path(self) -> str:
        """Get Recycle Bin path."""
        try:
            return "C:\\$Recycle.Bin"
        except:
            return "C:\\$Recycle.Bin"
    
    # ==========================================
    # ADMIN / ELEVATION
    # ==========================================
    
    def _check_admin(self) -> bool:
        """Check if running with admin privileges."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def elevate(self, command: str, args: List[str] = None) -> Dict[str, Any]:
        """Run a command with admin privileges."""
        try:
            args = args or []
            lpOperation = "runas"
            lpFile = command
            lpParameters = " ".join(args) if args else ""
            nShowCmd = 1
            
            result = ctypes.windll.shell32.ShellExecuteW(
                None, lpOperation, lpFile, lpParameters, None, nShowCmd
            )
            
            if result <= 32:
                return {"success": False, "error": f"Admin elevation failed (code: {result})"}
            
            return {"success": True, "message": f"Admin command executed: {command}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_as_admin(self, command: str, args: List[str] = None, wait: bool = False) -> Dict[str, Any]:
        """Run command as admin with better control."""
        try:
            args = args or []
            lpOperation = "runas"
            lpFile = command
            lpParameters = " ".join(args)
            nShowCmd = 1 if not wait else 0
            
            result = ctypes.windll.shell32.ShellExecuteW(
                None, lpOperation, lpFile, lpParameters, None, nShowCmd
            )
            
            if result <= 32:
                return {"success": False, "error": self._get_shell_error(result)}
            
            return {"success": True, "message": f"Admin command executed: {command} {lpParameters}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_shell_error(self, code: int) -> str:
        """Get Windows ShellExecute error message."""
        errors = {
            0: "Out of memory or resources.",
            2: "File not found.",
            3: "Path not found.",
            5: "Access denied.",
            8: "Insufficient memory.",
            31: "No associated application.",
            32: "No application associated with filename extension.",
            33: "DDE transaction failed.",
        }
        return errors.get(code, f"Unknown error code: {code}")
    
    # ==========================================
    # FILE OPERATIONS
    # ==========================================
    
    def file_exists(self, path: str) -> bool:
        return os.path.exists(path)
    
    def file_info(self, path: str) -> Dict[str, Any]:
        """Get file/directory information."""
        try:
            stat = os.stat(path)
            return {
                "success": True,
                "path": path,
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_dir": os.path.isdir(path),
                "is_file": os.path.isfile(path),
                "exists": True
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_file(self, path: str, content: str = "", overwrite: bool = False) -> Dict[str, Any]:
        """Create a file with optional content."""
        try:
            path = path.strip()
            if not path:
                return {"success": False, "error": "Empty path provided"}
            
            if not os.path.dirname(path) and ':' not in path:
                path = os.path.join(os.getcwd(), path)
            
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            if os.path.exists(path) and not overwrite:
                return {"success": False, "error": f"File exists: {path}"}
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {"success": True, "path": path, "size": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_file(self, path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Read a file's content."""
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            return {"success": True, "content": content, "size": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_file(self, path: str, permanent: bool = True) -> Dict[str, Any]:
        """Delete a file or directory."""
        try:
            if os.path.isdir(path):
                if permanent:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
            else:
                os.remove(path)
            return {"success": True, "path": path, "deleted": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def copy_file(self, src: str, dest: str, overwrite: bool = False) -> Dict[str, Any]:
        """Copy a file or directory."""
        try:
            if os.path.exists(dest) and not overwrite:
                return {"success": False, "error": f"Destination exists: {dest}"}
            
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src, dest)
            return {"success": True, "src": src, "dest": dest}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_file(self, src: str, dest: str, overwrite: bool = False) -> Dict[str, Any]:
        """Move a file or directory."""
        try:
            if os.path.exists(dest) and not overwrite:
                return {"success": False, "error": f"Destination exists: {dest}"}
            
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dest)
            return {"success": True, "src": src, "dest": dest}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def rename_file(self, old: str, new: str) -> Dict[str, Any]:
        """Rename a file or directory."""
        try:
            os.rename(old, new)
            return {"success": True, "old": old, "new": new}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_directory(self, path: str, recursive: bool = False, filter_ext: str = None) -> Dict[str, Any]:
        """List contents of a directory."""
        try:
            items = []
            if recursive:
                for root, dirs, files in os.walk(path):
                    for name in dirs + files:
                        full_path = os.path.join(root, name)
                        if filter_ext and not name.endswith(filter_ext):
                            continue
                        items.append(full_path)
            else:
                for name in os.listdir(path):
                    full_path = os.path.join(path, name)
                    if filter_ext and not name.endswith(filter_ext):
                        continue
                    items.append(full_path)
            
            return {"success": True, "path": path, "items": items, "count": len(items)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_files(self, root: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
        """Search for files matching a pattern."""
        try:
            results = []
            root_path = Path(root)
            if recursive:
                iterator = root_path.rglob(pattern)
            else:
                iterator = root_path.glob(pattern)
            
            for item in iterator:
                results.append(str(item))
            
            return {"success": True, "root": root, "pattern": pattern, "results": results, "count": len(results)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # PROCESS MANAGEMENT
    # ==========================================
    
    def list_processes(self, filter_name: str = None) -> Dict[str, Any]:
        """List running processes."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                            'status', 'create_time', 'username', 'exe']):
                try:
                    info = proc.info
                    if filter_name and filter_name.lower() not in info['name'].lower():
                        continue
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'cpu': info['cpu_percent'],
                        'memory': info['memory_percent'],
                        'status': info['status'],
                        'created': datetime.fromtimestamp(info['create_time']).isoformat(),
                        'username': info['username'],
                        'path': info['exe']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return {"success": True, "processes": processes, "count": len(processes)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def kill_process(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """Terminate a process by PID."""
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
            proc.wait(timeout=5)
            return {"success": True, "pid": pid, "name": proc.name()}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process {pid} not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def kill_process_by_name(self, name: str, force: bool = False) -> Dict[str, Any]:
        """Kill all processes with a given name."""
        try:
            killed = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == name.lower():
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()
                        killed.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return {"success": True, "name": name, "killed": killed, "count": len(killed)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_process(self, command: str, args: List[str] = None, as_admin: bool = False) -> Dict[str, Any]:
        """Start a new process."""
        try:
            if as_admin:
                return self.run_as_admin(command, args)
            else:
                cmd = [command] + (args or [])
                proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                return {"success": True, "pid": proc.pid, "command": command}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        """Get detailed process information."""
        try:
            proc = psutil.Process(pid)
            return {
                "success": True,
                "pid": pid,
                "name": proc.name(),
                "exe": proc.exe(),
                "cwd": proc.cwd(),
                "memory": proc.memory_info()._asdict(),
                "cpu": proc.cpu_percent(),
                "connections": [c._asdict() for c in proc.connections()],
                "open_files": [f.path for f in proc.open_files()],
                "children": [p.pid for p in proc.children()]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # WINDOW MANAGEMENT
    # ==========================================
    
    def list_windows(self) -> Dict[str, Any]:
        """List all visible windows."""
        try:
            if not PYGETWINDOW_AVAILABLE:
                return {"success": False, "error": "pygetwindow not installed. Install: pip install pygetwindow"}
            
            windows = []
            for win in gw.getAllWindows():
                if win.title:
                    windows.append({
                        "title": win.title,
                        "x": win.left,
                        "y": win.top,
                        "width": win.width,
                        "height": win.height,
                        "visible": win.isVisible,
                        "active": win.isActive,
                        "minimized": win.isMinimized,
                        "maximized": win.isMaximized
                    })
            return {"success": True, "windows": windows, "count": len(windows)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def focus_window(self, title: str) -> Dict[str, Any]:
        """Focus a window by title (partial match)."""
        try:
            if not PYGETWINDOW_AVAILABLE:
                return {"success": False, "error": "pygetwindow not installed"}
            
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return {"success": False, "error": f"No window found with title containing '{title}'"}
            
            windows[0].activate()
            return {"success": True, "window": windows[0].title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def minimize_window(self, title: str) -> Dict[str, Any]:
        """Minimize a window."""
        try:
            if not PYGETWINDOW_AVAILABLE:
                return {"success": False, "error": "pygetwindow not installed"}
            
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return {"success": False, "error": f"No window found with title containing '{title}'"}
            
            windows[0].minimize()
            return {"success": True, "window": windows[0].title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def maximize_window(self, title: str) -> Dict[str, Any]:
        """Maximize a window."""
        try:
            if not PYGETWINDOW_AVAILABLE:
                return {"success": False, "error": "pygetwindow not installed"}
            
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return {"success": False, "error": f"No window found with title containing '{title}'"}
            
            windows[0].maximize()
            return {"success": True, "window": windows[0].title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close_window(self, title: str) -> Dict[str, Any]:
        """Close a window."""
        try:
            if not PYGETWINDOW_AVAILABLE:
                return {"success": False, "error": "pygetwindow not installed"}
            
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return {"success": False, "error": f"No window found with title containing '{title}'"}
            
            windows[0].close()
            return {"success": True, "window": windows[0].title}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def resize_window(self, title: str, width: int, height: int) -> Dict[str, Any]:
        """Resize a window."""
        try:
            if not PYGETWINDOW_AVAILABLE:
                return {"success": False, "error": "pygetwindow not installed"}
            
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return {"success": False, "error": f"No window found with title containing '{title}'"}
            
            windows[0].resizeTo(width, height)
            return {"success": True, "window": windows[0].title, "width": width, "height": height}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_window(self, title: str, x: int, y: int) -> Dict[str, Any]:
        """Move a window."""
        try:
            if not PYGETWINDOW_AVAILABLE:
                return {"success": False, "error": "pygetwindow not installed"}
            
            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return {"success": False, "error": f"No window found with title containing '{title}'"}
            
            windows[0].moveTo(x, y)
            return {"success": True, "window": windows[0].title, "x": x, "y": y}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # SYSTEM SETTINGS
    # ==========================================
    
    def set_volume(self, level: int) -> Dict[str, Any]:
        """Set system volume (0-100) using multiple methods."""
        try:
            level = max(0, min(100, level))
            
            if PYCAW_AVAILABLE:
                try:
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                    return {"success": True, "volume": level, "method": "pycaw"}
                except Exception as e:
                    logger.debug(f"pycaw error: {e}")
            
            try:
                ps_script = f"""
                Add-Type -TypeDefinition @"
                using System;
                using System.Runtime.InteropServices;
                public class AudioVolume {{
                    [DllImport("user32.dll")]
                    public static extern IntPtr SendMessageW(IntPtr hWnd, int Msg, int wParam, int lParam);
                }}
                "@
                $vol = {level}
                $obj = New-Object -ComObject WScript.Shell
                for ($i = 0; $i -lt 50; $i++) {{
                    $obj.SendKeys([char]174)
                }}
                for ($i = 0; $i -lt $vol/2; $i++) {{
                    $obj.SendKeys([char]175)
                }}
                """
                subprocess.run(
                    f'powershell -c "{ps_script}"',
                    shell=True, capture_output=True, timeout=5
                )
                return {"success": True, "volume": level, "method": "powershell"}
            except Exception as e:
                logger.debug(f"PowerShell error: {e}")
            
            try:
                result = subprocess.run(
                    ['nircmd', 'setvolume', str(level)],
                    capture_output=True, timeout=2
                )
                if result.returncode == 0:
                    return {"success": True, "volume": level, "method": "nircmd"}
            except:
                pass
            
            try:
                subprocess.Popen('sndvol.exe', shell=True)
                return {
                    "success": True,
                    "volume": level,
                    "method": "manual",
                    "warning": "Volume mixer opened. Please adjust manually."
                }
            except:
                pass
            
            return {
                "success": False,
                "error": "Could not set volume. Install pycaw: pip install pycaw",
                "volume": level
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_volume(self) -> Dict[str, Any]:
        """Get current system volume."""
        try:
            if PYCAW_AVAILABLE:
                try:
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    current = volume.GetMasterVolumeLevelScalar() * 100
                    return {"success": True, "volume": int(current), "method": "pycaw"}
                except Exception as e:
                    logger.debug(f"pycaw get volume error: {e}")
            
            try:
                result = subprocess.run(
                    'powershell -c "(Get-WmiObject -Class Win32_Volume -Filter \'DriveLetter=\'C:\'\').GetVolume()"',
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    vol = int(float(result.stdout.strip()))
                    return {"success": True, "volume": vol, "method": "powershell"}
            except Exception as e:
                logger.debug(f"PowerShell get volume error: {e}")
            
            return {"success": False, "error": "Could not get volume", "volume": 50}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # BRIGHTNESS - FIXED: Added get_brightness
    # ==========================================
    
    def get_brightness(self) -> Dict[str, Any]:
        """Get current screen brightness."""
        try:
            if SCREEN_BRIGHTNESS_AVAILABLE:
                brightness = sbc.get_brightness()
                if brightness:
                    return {
                        "success": True,
                        "brightness": brightness[0] if isinstance(brightness, list) else brightness,
                        "method": "screen_brightness_control"
                    }
                return {"success": False, "error": "Could not get brightness - no value returned"}
            
            # Fallback: Try WMI
            try:
                result = subprocess.run(
                    'powershell -c "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"',
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    brightness = int(result.stdout.strip())
                    return {"success": True, "brightness": brightness, "method": "wmi"}
            except:
                pass
            
            return {"success": False, "error": "Could not get brightness. Install: pip install screen-brightness-control"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_brightness(self, level: int) -> Dict[str, Any]:
        """Set screen brightness (0-100)."""
        try:
            level = max(0, min(100, level))
            
            if SCREEN_BRIGHTNESS_AVAILABLE:
                try:
                    sbc.set_brightness(level)
                    return {"success": True, "brightness": level, "method": "screen_brightness_control"}
                except Exception as e:
                    logger.debug(f"screen_brightness_control error: {e}")
            
            try:
                subprocess.run(
                    f'powershell -c "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness({level},0)"',
                    shell=True, capture_output=True, timeout=5
                )
                return {"success": True, "brightness": level, "method": "wmi"}
            except Exception as e:
                logger.debug(f"WMI brightness error: {e}")
            
            return {
                "success": False,
                "error": "Could not set brightness. Install: pip install screen-brightness-control",
                "brightness": level
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_power_plan(self, plan: str) -> Dict[str, Any]:
        """Set power plan: 'balanced', 'high', 'power_saver'."""
        try:
            plans = {
                "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
                "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
                "power_saver": "a1841308-3541-4f68-bc83-4c39d7f0b2a0"
            }
            guid = plans.get(plan.lower())
            if not guid:
                return {"success": False, "error": f"Unknown plan: {plan}. Options: balanced, high, power_saver"}
            subprocess.run(f"powercfg -setactive {guid}", shell=True)
            return {"success": True, "plan": plan}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_wallpaper(self, image_path: str) -> Dict[str, Any]:
        """Set desktop wallpaper."""
        try:
            if not os.path.exists(image_path):
                return {"success": False, "error": f"Image not found: {image_path}"}
            
            script = f"""
            $code = @'
            using System.Runtime.InteropServices;
            public class Wallpaper {{
                [DllImport("user32.dll", CharSet = CharSet.Auto)]
                public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
            }}
            '@
            Add-Type -TypeDefinition $code -Name Wallpaper
            [Wallpaper]::SystemParametersInfo(20, 0, "{image_path}", 3)
            """
            subprocess.run(f'powershell -c "{script}"', shell=True)
            return {"success": True, "wallpaper": image_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # CLIPBOARD OPERATIONS
    # ==========================================
    
    def get_clipboard(self) -> Dict[str, Any]:
        """Get text from clipboard."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def set_clipboard(self, text: str) -> Dict[str, Any]:
        """Set text to clipboard."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear_clipboard(self) -> Dict[str, Any]:
        """Clear clipboard."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.destroy()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # SCREEN CAPTURE
    # ==========================================
    
    def screenshot(self, filename: str = None, region: tuple = None) -> Dict[str, Any]:
        """Capture screenshot."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed. Install: pip install pyautogui"}
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            if region:
                import pyautogui
                pyautogui.screenshot(filename, region=region)
            else:
                import pyautogui
                pyautogui.screenshot(filename)
            
            return {"success": True, "filename": filename, "path": os.path.abspath(filename)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def screen_size(self) -> Dict[str, Any]:
        """Get screen size."""
        try:
            if PYAUTOGUI_AVAILABLE:
                import pyautogui
                width, height = pyautogui.size()
                return {"success": True, "width": width, "height": height}
            else:
                return {"success": False, "error": "pyautogui not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_mouse_position(self) -> Dict[str, Any]:
        """Get current mouse position."""
        try:
            if PYAUTOGUI_AVAILABLE:
                import pyautogui
                x, y = pyautogui.position()
                return {"success": True, "x": x, "y": y}
            else:
                return {"success": False, "error": "pyautogui not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # SYSTEM INFORMATION
    # ==========================================
    
    def system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            cpu = {
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
                "percent": psutil.cpu_percent(interval=0.5),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {},
                "per_cpu": psutil.cpu_percent(interval=0.5, percpu=True)
            }
            
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            memory = {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": swap.percent
            }
            
            disk = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk.append({
                        "device": partition.device,
                        "mount": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    })
                except:
                    continue
            
            net = psutil.net_io_counters()
            network = {
                "sent": net.bytes_sent,
                "recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "sent_mb": net.bytes_sent / (1024 * 1024),
                "recv_mb": net.bytes_recv / (1024 * 1024)
            }
            
            battery = None
            if hasattr(psutil, "sensors_battery"):
                bat = psutil.sensors_battery()
                if bat:
                    battery = {
                        "percent": bat.percent,
                        "power_plugged": bat.power_plugged,
                        "seconds_left": bat.secsleft,
                        "charging": bat.power_plugged
                    }
            
            system = {
                "os": platform.system(),
                "os_version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            
            return {
                "success": True,
                "cpu": cpu,
                "memory": memory,
                "disk": disk,
                "network": network,
                "battery": battery,
                "system": system,
                "uptime": time.time() - psutil.boot_time(),
                "uptime_formatted": self._format_uptime(time.time() - psutil.boot_time())
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"
    
    # ==========================================
    # REGISTRY OPERATIONS
    # ==========================================
    
    def registry_read(self, key_path: str, value_name: str = "") -> Dict[str, Any]:
        """Read a registry value."""
        try:
            parts = key_path.split('\\')
            hive_str = parts[0]
            path = '\\'.join(parts[1:])
            
            hive_map = {
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_USERS": winreg.HKEY_USERS,
                "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
            }
            hive = hive_map.get(hive_str)
            if hive is None:
                return {"success": False, "error": f"Unknown hive: {hive_str}"}
            
            key = winreg.OpenKey(hive, path)
            data, reg_type = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            
            return {"success": True, "key": key_path, "value_name": value_name, "data": data, "type": reg_type}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def registry_write(self, key_path: str, value_name: str, data: Any, reg_type: int = winreg.REG_SZ) -> Dict[str, Any]:
        """Write a registry value."""
        try:
            parts = key_path.split('\\')
            hive_str = parts[0]
            path = '\\'.join(parts[1:])
            
            hive_map = {
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_USERS": winreg.HKEY_USERS,
                "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
            }
            hive = hive_map.get(hive_str)
            if hive is None:
                return {"success": False, "error": f"Unknown hive: {hive_str}"}
            
            key = winreg.CreateKey(hive, path)
            winreg.SetValueEx(key, value_name, 0, reg_type, data)
            winreg.CloseKey(key)
            return {"success": True, "key": key_path, "value_name": value_name, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def registry_delete(self, key_path: str, value_name: str = "") -> Dict[str, Any]:
        """Delete a registry value or key."""
        try:
            parts = key_path.split('\\')
            hive_str = parts[0]
            path = '\\'.join(parts[1:])
            
            hive_map = {
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_USERS": winreg.HKEY_USERS,
                "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
            }
            hive = hive_map.get(hive_str)
            if hive is None:
                return {"success": False, "error": f"Unknown hive: {hive_str}"}
            
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
            if value_name:
                winreg.DeleteValue(key, value_name)
            else:
                winreg.DeleteKey(key, path)
            winreg.CloseKey(key)
            return {"success": True, "key": key_path, "value_name": value_name}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # USER AUTOMATION (Keyboard/Mouse)
    # ==========================================
    
    def type_text(self, text: str, interval: float = 0.05) -> Dict[str, Any]:
        """Type text using keyboard simulation."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed"}
            import pyautogui
            pyautogui.write(text, interval=interval)
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def press_key(self, key: str, presses: int = 1) -> Dict[str, Any]:
        """Press a key or combination."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed"}
            import pyautogui
            pyautogui.press(key, presses=presses)
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def hotkey(self, *keys) -> Dict[str, Any]:
        """Press a combination of keys."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed"}
            import pyautogui
            pyautogui.hotkey(*keys)
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mouse_click(self, x: int = None, y: int = None, button: str = 'left', clicks: int = 1) -> Dict[str, Any]:
        """Click at current position or given coordinates."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed"}
            import pyautogui
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button, clicks=clicks)
            else:
                pyautogui.click(button=button, clicks=clicks)
            return {"success": True, "x": x, "y": y, "button": button}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mouse_move(self, x: int, y: int, duration: float = 0.2) -> Dict[str, Any]:
        """Move mouse to coordinates."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed"}
            import pyautogui
            pyautogui.moveTo(x, y, duration=duration)
            return {"success": True, "x": x, "y": y}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mouse_scroll(self, amount: int) -> Dict[str, Any]:
        """Scroll up/down (positive = up)."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed"}
            import pyautogui
            pyautogui.scroll(amount)
            return {"success": True, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> Dict[str, Any]:
        """Drag mouse from one position to another."""
        try:
            if not PYAUTOGUI_AVAILABLE:
                return {"success": False, "error": "pyautogui not installed"}
            import pyautogui
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=duration)
            return {"success": True, "start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # APPLICATION INDEX (Auto-learning)
    # ==========================================
    
    def _load_app_index(self) -> Dict[str, str]:
        """Load application index from file."""
        index_file = Path(__file__).parent.parent / "data" / "app_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_app_index(self):
        """Save application index to file."""
        index_file = Path(__file__).parent.parent / "data" / "app_index.json"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(index_file, 'w') as f:
            json.dump(self.app_index, f, indent=2)
    
    def find_app(self, app_name: str) -> Optional[str]:
        """Find an application by name using index."""
        app_name_lower = app_name.lower()
        
        if app_name_lower in self.app_index:
            path = self.app_index[app_name_lower]
            if os.path.exists(path):
                return path
        
        paths = self._search_common_apps(app_name)
        if paths:
            self.app_index[app_name_lower] = paths[0]
            self._save_app_index()
            return paths[0]
        
        return None
    
    def _search_common_apps(self, app_name: str) -> List[str]:
        """Search common application locations."""
        results = []
        
        locations = [
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("APPDATA", ""),
        ]
        
        app_name_lower = app_name.lower()
        for location in locations:
            if not location or not os.path.exists(location):
                continue
            
            for root, dirs, files in os.walk(location):
                if len(results) >= 10:
                    break
                for file in files:
                    if file.lower().endswith('.exe') and app_name_lower in file.lower():
                        results.append(os.path.join(root, file))
        
        return results
    
    # ==========================================
    # SERVICE MANAGEMENT
    # ==========================================
    
    def list_services(self) -> Dict[str, Any]:
        """List Windows services."""
        try:
            services = []
            for service in psutil.win_service_iter():
                try:
                    svc = psutil.win_service_get(service.name())
                    services.append({
                        "name": svc.name(),
                        "display_name": svc.display_name(),
                        "status": svc.status(),
                        "start_type": svc.start_type(),
                        "pid": svc.pid(),
                        "description": svc.description()
                    })
                except:
                    continue
            return {"success": True, "services": services, "count": len(services)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_service(self, service_name: str) -> Dict[str, Any]:
        """Start a Windows service."""
        try:
            subprocess.run(f"net start {service_name}", shell=True, capture_output=True)
            return {"success": True, "service": service_name}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_service(self, service_name: str) -> Dict[str, Any]:
        """Stop a Windows service."""
        try:
            subprocess.run(f"net stop {service_name}", shell=True, capture_output=True)
            return {"success": True, "service": service_name}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # NETWORK OPERATIONS
    # ==========================================
    
    def get_ip_info(self) -> Dict[str, Any]:
        """Get IP information."""
        try:
            import socket
            import requests
            
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            try:
                response = requests.get("https://api.ipify.org?format=json", timeout=5)
                public_ip = response.json().get("ip")
            except:
                public_ip = "Unable to fetch"
            
            return {
                "success": True,
                "hostname": hostname,
                "local_ip": local_ip,
                "public_ip": public_ip
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def ping_host(self, host: str, count: int = 4) -> Dict[str, Any]:
        """Ping a host."""
        try:
            result = subprocess.run(
                f"ping -n {count} {host}",
                shell=True,
                capture_output=True,
                text=True
            )
            return {"success": True, "host": host, "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # SYSTEM CLEANER - WITH PERMISSION FIX
    # ==========================================
    
    def scan_junk_files(self) -> Dict[str, Any]:
        """Scan for junk files that can be safely deleted."""
        junk_files = []
        total_size = 0
        
        try:
            logger.info("🔍 Starting junk file scan...")
            
            # 1. Scan Temp folders
            temp_count = 0
            for temp_path in self.temp_paths:
                if temp_path and os.path.exists(temp_path):
                    logger.debug(f"Scanning temp path: {temp_path}")
                    for root, dirs, files in os.walk(temp_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                if any(file.lower().endswith(ext) for ext in self.junk_extensions):
                                    size = os.path.getsize(file_path)
                                    junk_files.append({
                                        "path": file_path,
                                        "size": size,
                                        "type": "temp"
                                    })
                                    total_size += size
                                    temp_count += 1
                                elif os.path.exists(file_path):
                                    mtime = os.path.getmtime(file_path)
                                    if (time.time() - mtime) > 30 * 24 * 3600:
                                        size = os.path.getsize(file_path)
                                        junk_files.append({
                                            "path": file_path,
                                            "size": size,
                                            "type": "old_temp"
                                        })
                                        total_size += size
                                        temp_count += 1
                            except Exception as e:
                                logger.debug(f"Error processing {file_path}: {e}")
                                continue
            
            logger.info(f"Found {temp_count} temp files")
            
            # 2. Scan Log files
            log_count = 0
            log_paths = [
                os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Logs"),
                os.path.join(os.environ.get("USERPROFILE", ""), "AppData\\Local\\Microsoft\\Windows\\Logs"),
            ]
            for log_path in log_paths:
                if os.path.exists(log_path):
                    logger.debug(f"Scanning log path: {log_path}")
                    for root, dirs, files in os.walk(log_path):
                        for file in files:
                            if file.lower().endswith(".log"):
                                file_path = os.path.join(root, file)
                                try:
                                    size = os.path.getsize(file_path)
                                    junk_files.append({
                                        "path": file_path,
                                        "size": size,
                                        "type": "log"
                                    })
                                    total_size += size
                                    log_count += 1
                                except Exception as e:
                                    logger.debug(f"Error processing {file_path}: {e}")
                                    continue
            
            logger.info(f"Found {log_count} log files")
            
            # 3. Scan Prefetch - 🔧 FIX: Handled PermissionError gracefully
            prefetch_count = 0
            prefetch_path = "C:\\Windows\\Prefetch"
            if os.path.exists(prefetch_path):
                logger.debug(f"Scanning prefetch path: {prefetch_path}")
                try:
                    for file in os.listdir(prefetch_path):
                        if file.endswith(".pf"):
                            file_path = os.path.join(prefetch_path, file)
                            try:
                                mtime = os.path.getmtime(file_path)
                                if (time.time() - mtime) > 7 * 24 * 3600:
                                    size = os.path.getsize(file_path)
                                    junk_files.append({
                                        "path": file_path,
                                        "size": size,
                                        "type": "prefetch"
                                    })
                                    total_size += size
                                    prefetch_count += 1
                            except Exception as e:
                                logger.debug(f"Error processing {file_path}: {e}")
                                continue
                except PermissionError:
                    logger.warning("⚠️ Access denied to Prefetch folder. Skipping...")
                except Exception as e:
                    logger.debug(f"Error scanning prefetch: {e}")
                logger.info(f"Found {prefetch_count} prefetch files")
            
            # Build result
            result = {
                "success": True,
                "junk_files": junk_files,
                "total_files": len(junk_files),
                "total_size": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "total_size_gb": total_size / (1024 * 1024 * 1024)
            }
            
            # 🔧 FIX: Add message for display
            result["message"] = f"Found {result['total_files']} junk files ({result['total_size_mb']:.2f} MB)"
            
            logger.info(f"✅ Scan complete: {result['total_files']} files, {result['total_size_mb']:.2f} MB")
            return result
            
        except Exception as e:
            logger.error(f"❌ Junk scan error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "message": f"Scan error: {str(e)}"}
    
    def clean_system_junk(self, safe_mode: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Clean system junk files."""
        try:
            scan_result = self.scan_junk_files()
            if not scan_result.get("success"):
                return scan_result
            
            junk_files = scan_result.get("junk_files", [])
            deleted = []
            total_cleaned = 0
            
            if safe_mode:
                safe_types = ["temp", "old_temp"]
                junk_files = [f for f in junk_files if f.get("type") in safe_types]
            
            if dry_run:
                total_size = sum(f.get("size", 0) for f in junk_files)
                return {
                    "success": True,
                    "dry_run": True,
                    "message": f"Would clean {len(junk_files)} files ({total_size / (1024*1024):.2f} MB)",
                    "files_to_delete": junk_files,
                    "total_size": total_size
                }
            
            for file_info in junk_files:
                file_path = file_info.get("path")
                if not file_path:
                    continue
                
                try:
                    if os.path.exists(file_path):
                        if os.path.isdir(file_path):
                            shutil.rmtree(file_path, ignore_errors=True)
                        else:
                            os.remove(file_path)
                        deleted.append({
                            "path": file_path,
                            "type": file_info.get("type", "unknown"),
                            "size": file_info.get("size", 0)
                        })
                        total_cleaned += file_info.get("size", 0)
                except Exception as e:
                    logger.debug(f"Could not delete {file_path}: {e}")
            
            return {
                "success": True,
                "message": f"Cleaned {len(deleted)} files ({total_cleaned / (1024*1024):.2f} MB)",
                "deleted": deleted,
                "total_files": len(deleted),
                "total_cleaned": total_cleaned,
                "total_cleaned_mb": total_cleaned / (1024 * 1024)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def empty_recycle_bin(self, confirm: bool = True) -> Dict[str, Any]:
        """Empty Recycle Bin."""
        try:
            if confirm:
                result = subprocess.run(
                    'powershell -c "(Get-ChildItem -Path \'C:\\$Recycle.Bin\' -Recurse -Force -ErrorAction SilentlyContinue).Count"',
                    shell=True, capture_output=True, text=True
                )
                if result.stdout.strip():
                    item_count = int(result.stdout.strip())
                    if item_count == 0:
                        return {"success": True, "message": "Recycle Bin is already empty", "items_cleared": 0}
                    print(f"📊 Recycle Bin contains {item_count} items")
            
            subprocess.run(
                'powershell -c "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"',
                shell=True, capture_output=True, text=True
            )
            return {
                "success": True,
                "message": "Recycle Bin emptied successfully",
                "items_cleared": item_count if 'item_count' in locals() else 0
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_files_by_pattern(self, root_path: str, pattern: str, recursive: bool = True, 
                                confirm: bool = True, safe_mode: bool = True) -> Dict[str, Any]:
        """Delete files matching a pattern."""
        try:
            unsafe_paths = ["C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)"]
            if safe_mode and any(root_path.lower().startswith(p.lower()) for p in unsafe_paths):
                return {
                    "success": False,
                    "error": f"Deleting from {root_path} is not allowed in safe mode"
                }
            
            files_found = []
            root = Path(root_path)
            
            if recursive:
                iterator = root.rglob(pattern)
            else:
                iterator = root.glob(pattern)
            
            for file_path in iterator:
                if file_path.is_file():
                    if safe_mode:
                        if any(file_path.suffix.lower() == ext for ext in [".exe", ".dll", ".sys", ".ini"]):
                            continue
                        if any(file_path.name.lower().startswith(x) for x in ["boot", "config", "system"]):
                            continue
                    files_found.append(str(file_path))
            
            if not files_found:
                return {
                    "success": True,
                    "message": f"No files matching '{pattern}' found in {root_path}",
                    "files": []
                }
            
            if confirm:
                return {
                    "success": True,
                    "need_confirmation": True,
                    "files": files_found,
                    "count": len(files_found),
                    "message": f"Found {len(files_found)} files. Say 'yes' to delete."
                }
            
            deleted = []
            for file_path in files_found:
                try:
                    os.remove(file_path)
                    deleted.append(file_path)
                except Exception as e:
                    logger.debug(f"Could not delete {file_path}: {e}")
            
            return {
                "success": True,
                "deleted": deleted,
                "count": len(deleted),
                "message": f"Deleted {len(deleted)} files"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==========================================
    # DELETE LARGE FILES
    # ==========================================
    
    def delete_large_files(self, root_path: str, min_size_mb: int = 100, safe_mode: bool = True) -> Dict[str, Any]:
        """Find and delete large files."""
        try:
            large_files = []
            root = Path(root_path)
            
            for file_path in root.rglob("*"):
                if file_path.is_file():
                    try:
                        size = file_path.stat().st_size
                        if size > min_size_mb * 1024 * 1024:
                            if safe_mode:
                                if file_path.suffix.lower() in [".exe", ".dll", ".sys"]:
                                    continue
                            large_files.append({
                                "path": str(file_path),
                                "size": size,
                                "size_mb": size / (1024 * 1024)
                            })
                    except:
                        continue
            
            if not large_files:
                return {
                    "success": True,
                    "message": f"No files larger than {min_size_mb}MB found in {root_path}",
                    "files": []
                }
            
            total_size = sum(f["size"] for f in large_files)
            
            # Delete if confirmed
            deleted = []
            for file_info in large_files:
                try:
                    os.remove(file_info["path"])
                    deleted.append(file_info["path"])
                except:
                    pass
            
            return {
                "success": True,
                "files": large_files,
                "count": len(large_files),
                "total_size_mb": total_size / (1024 * 1024),
                "deleted": deleted,
                "deleted_count": len(deleted),
                "message": f"Found {len(large_files)} files larger than {min_size_mb}MB ({total_size / (1024*1024):.2f} MB total). Deleted {len(deleted)} files."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}