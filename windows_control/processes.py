"""
Windows AI Agent - Process and Application Controller
Handles process management and application launching
"""
import os
import sys
import subprocess
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

# Check if we're on Windows
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    try:
        import psutil
        HAS_PSUTIL = True
    except ImportError:
        HAS_PSUTIL = False
        logger.warning("psutil not installed, some features limited")
else:
    HAS_PSUTIL = False
    logger.info("Running on non-Windows platform, using mock implementations")


@dataclass
class ProcessInfo:
    """Information about a process"""
    pid: int
    name: str
    exe: str = ""
    cmdline: str = ""
    status: str = ""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    username: str = ""


@dataclass  
class WindowInfo:
    """Information about a window"""
    handle: int
    title: str
    class_name: str = ""
    process_id: int = 0
    is_visible: bool = True
    rect: Dict[str, int] = None


class ProcessController:
    """
    Process Controller
    Manages Windows processes - list, start, stop, etc.
    """
    
    def __init__(self):
        self._process_cache: Dict[int, ProcessInfo] = {}
    
    def list_processes(
        self,
        filter_name: str = None,
        include_system: bool = False,
    ) -> Dict[str, Any]:
        """List running processes"""
        if IS_WINDOWS and HAS_PSUTIL:
            return self._list_processes_windows(filter_name, include_system)
        else:
            return self._list_processes_mock(filter_name)
    
    def _list_processes_windows(
        self,
        filter_name: str = None,
        include_system: bool = False,
    ) -> Dict[str, Any]:
        """List processes on Windows using psutil"""
        import psutil
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'status', 'username']):
            try:
                info = proc.info
                
                # Filter by name if specified
                if filter_name and filter_name.lower() not in info['name'].lower():
                    continue
                
                # Skip system processes if not requested
                if not include_system and info['username'] in ['SYSTEM', 'NT AUTHORITY\\SYSTEM']:
                    continue
                
                try:
                    memory_info = proc.memory_info()
                    memory_mb = memory_info.rss / (1024 * 1024)
                except:
                    memory_mb = 0
                
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "exe": info['exe'] or "",
                    "status": info['status'],
                    "username": info['username'] or "",
                    "memory_mb": round(memory_mb, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            "result": {
                "processes": processes,
                "count": len(processes),
            }
        }
    
    def _list_processes_mock(self, filter_name: str = None) -> Dict[str, Any]:
        """Mock process list for non-Windows"""
        # Use subprocess to get basic process info
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            processes = []
            for line in lines:
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    name = parts[10].split()[0] if parts[10] else ""
                    if filter_name and filter_name.lower() not in name.lower():
                        continue
                    
                    processes.append({
                        "pid": int(parts[1]),
                        "name": os.path.basename(name),
                        "exe": name,
                        "status": "running",
                        "username": parts[0],
                        "memory_mb": 0,
                    })
            
            return {
                "result": {
                    "processes": processes[:50],  # Limit results
                    "count": len(processes),
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        """Get detailed info about a specific process"""
        if IS_WINDOWS and HAS_PSUTIL:
            import psutil
            try:
                proc = psutil.Process(pid)
                info = proc.as_dict(attrs=[
                    'pid', 'name', 'exe', 'cmdline', 'status',
                    'create_time', 'username', 'cpu_percent'
                ])
                memory = proc.memory_info()
                
                return {
                    "result": {
                        "pid": info['pid'],
                        "name": info['name'],
                        "exe": info['exe'],
                        "cmdline": ' '.join(info['cmdline'] or []),
                        "status": info['status'],
                        "username": info['username'],
                        "memory_mb": round(memory.rss / (1024 * 1024), 2),
                        "cpu_percent": info['cpu_percent'],
                    }
                }
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"error": "Process info not available on this platform"}
    
    def kill_process(
        self,
        pid: int = None,
        name: str = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Kill a process by PID or name"""
        if not pid and not name:
            return {"error": "Either pid or name must be specified"}
        
        if IS_WINDOWS and HAS_PSUTIL:
            import psutil
            
            try:
                if pid:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    
                    return {
                        "result": {
                            "killed": True,
                            "pid": pid,
                            "name": proc_name,
                        },
                        "side_effects": [{
                            "type": "process_killed",
                            "data": {"pid": pid, "name": proc_name},
                            "reversible": False,
                        }]
                    }
                else:
                    # Kill by name
                    killed = []
                    for proc in psutil.process_iter(['pid', 'name']):
                        if proc.info['name'].lower() == name.lower():
                            try:
                                if force:
                                    proc.kill()
                                else:
                                    proc.terminate()
                                killed.append(proc.info['pid'])
                            except:
                                pass
                    
                    return {
                        "result": {
                            "killed": len(killed) > 0,
                            "name": name,
                            "pids": killed,
                            "count": len(killed),
                        }
                    }
            except Exception as e:
                return {"error": str(e)}
        else:
            # Non-Windows implementation
            try:
                if pid:
                    os.kill(pid, 9 if force else 15)
                    return {"result": {"killed": True, "pid": pid}}
                else:
                    result = subprocess.run(['pkill', '-9' if force else '-15', name], capture_output=True)
                    return {"result": {"killed": result.returncode == 0, "name": name}}
            except Exception as e:
                return {"error": str(e)}


class ApplicationController:
    """
    Application Controller
    Launches and manages applications
    """
    
    def __init__(self):
        # Common application paths on Windows
        self.app_aliases = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "code": "code.exe",
            "vscode": "code.exe",
        }
    
    def open_application(
        self,
        identifier: str,
        arguments: List[str] = None,
        working_dir: str = None,
        wait: bool = False,
        run_as_admin: bool = False,
    ) -> Dict[str, Any]:
        """Open an application"""
        arguments = arguments or []
        
        # Resolve alias
        app_name = self.app_aliases.get(identifier.lower(), identifier)
        
        try:
            if IS_WINDOWS:
                return self._open_app_windows(app_name, arguments, working_dir, wait, run_as_admin)
            else:
                return self._open_app_unix(app_name, arguments, working_dir, wait)
        except Exception as e:
            return {"error": str(e)}
    
    def _open_app_windows(
        self,
        app_name: str,
        arguments: List[str],
        working_dir: str,
        wait: bool,
        run_as_admin: bool,
    ) -> Dict[str, Any]:
        """Open application on Windows"""
        import subprocess
        
        cmd = [app_name] + arguments
        
        if run_as_admin:
            # Use ShellExecute with runas
            import ctypes
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                app_name,
                ' '.join(arguments),
                working_dir,
                1  # SW_SHOWNORMAL
            )
            if result > 32:
                return {
                    "result": {
                        "launched": True,
                        "application": app_name,
                        "elevated": True,
                    }
                }
            else:
                return {"error": f"Failed to launch with admin rights, error code: {result}"}
        
        # Normal launch
        process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        if wait:
            process.wait()
        
        return {
            "result": {
                "launched": True,
                "application": app_name,
                "pid": process.pid,
                "arguments": arguments,
            },
            "side_effects": [{
                "type": "process_started",
                "data": {"pid": process.pid, "name": app_name},
                "reversible": True,
            }]
        }
    
    def _open_app_unix(
        self,
        app_name: str,
        arguments: List[str],
        working_dir: str,
        wait: bool,
    ) -> Dict[str, Any]:
        """Open application on Unix-like systems"""
        cmd = [app_name] + arguments
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            if wait:
                process.wait()
            
            return {
                "result": {
                    "launched": True,
                    "application": app_name,
                    "pid": process.pid,
                },
                "side_effects": [{
                    "type": "process_started",
                    "data": {"pid": process.pid, "name": app_name},
                    "reversible": True,
                }]
            }
        except FileNotFoundError:
            return {"error": f"Application not found: {app_name}"}
    
    def close_application(
        self,
        identifier: str = None,
        pid: int = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Close an application gracefully or forcefully"""
        process_ctrl = ProcessController()
        return process_ctrl.kill_process(pid=pid, name=identifier, force=force)
    
    def list_installed_applications(self) -> Dict[str, Any]:
        """List installed applications"""
        if IS_WINDOWS:
            return self._list_installed_windows()
        else:
            return self._list_installed_unix()
    
    def _list_installed_windows(self) -> Dict[str, Any]:
        """List installed Windows applications"""
        try:
            # Query registry for installed programs
            import winreg
            
            apps = []
            paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]
            
            for hive, path in paths:
                try:
                    key = winreg.OpenKey(hive, path)
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                version = ""
                                try:
                                    version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                except:
                                    pass
                                
                                apps.append({
                                    "name": name,
                                    "version": version,
                                })
                            except:
                                pass
                            
                            winreg.CloseKey(subkey)
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except:
                    continue
            
            # Remove duplicates
            seen = set()
            unique_apps = []
            for app in apps:
                if app['name'] not in seen:
                    seen.add(app['name'])
                    unique_apps.append(app)
            
            return {
                "result": {
                    "applications": sorted(unique_apps, key=lambda x: x['name']),
                    "count": len(unique_apps),
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _list_installed_unix(self) -> Dict[str, Any]:
        """List installed applications on Unix"""
        try:
            # Try dpkg (Debian/Ubuntu)
            result = subprocess.run(
                ['dpkg', '--list'],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                apps = []
                for line in result.stdout.split('\n')[5:]:
                    parts = line.split()
                    if len(parts) >= 3 and parts[0] == 'ii':
                        apps.append({
                            "name": parts[1],
                            "version": parts[2],
                        })
                
                return {
                    "result": {
                        "applications": apps[:100],
                        "count": len(apps),
                    }
                }
        except:
            pass
        
        return {"result": {"applications": [], "count": 0}}


class WindowController:
    """
    Window Controller
    Manages Windows windows - focus, minimize, maximize, etc.
    """
    
    def __init__(self):
        self._windows_cache: List[WindowInfo] = []
    
    def list_windows(self, filter_title: str = None) -> Dict[str, Any]:
        """List all visible windows"""
        if IS_WINDOWS:
            return self._list_windows_win32(filter_title)
        else:
            return self._list_windows_mock(filter_title)
    
    def _list_windows_win32(self, filter_title: str = None) -> Dict[str, Any]:
        """List windows using Win32 API"""
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        windows = []
        
        def enum_callback(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd) + 1
                buffer = ctypes.create_unicode_buffer(length)
                user32.GetWindowTextW(hwnd, buffer, length)
                title = buffer.value
                
                if title:
                    if filter_title and filter_title.lower() not in title.lower():
                        return True
                    
                    # Get process ID
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    
                    # Get window rect
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    
                    windows.append({
                        "handle": hwnd,
                        "title": title,
                        "process_id": pid.value,
                        "rect": {
                            "left": rect.left,
                            "top": rect.top,
                            "right": rect.right,
                            "bottom": rect.bottom,
                        }
                    })
            return True
        
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        
        return {
            "result": {
                "windows": windows,
                "count": len(windows),
            }
        }
    
    def _list_windows_mock(self, filter_title: str = None) -> Dict[str, Any]:
        """Mock window list for non-Windows"""
        return {
            "result": {
                "windows": [
                    {"handle": 1, "title": "Mock Window 1", "process_id": 1000},
                    {"handle": 2, "title": "Mock Window 2", "process_id": 1001},
                ],
                "count": 2,
                "note": "Mock data - not running on Windows",
            }
        }
    
    def focus_window(self, handle: int = None, title: str = None) -> Dict[str, Any]:
        """Bring a window to the foreground"""
        if IS_WINDOWS:
            import ctypes
            user32 = ctypes.windll.user32
            
            if handle is None and title:
                # Find window by title
                handle = user32.FindWindowW(None, title)
                if not handle:
                    return {"error": f"Window not found: {title}"}
            
            if handle:
                user32.SetForegroundWindow(handle)
                return {"result": {"focused": True, "handle": handle}}
        
        return {"error": "Window focus not available on this platform"}
    
    def minimize_window(self, handle: int) -> Dict[str, Any]:
        """Minimize a window"""
        if IS_WINDOWS:
            import ctypes
            user32 = ctypes.windll.user32
            user32.ShowWindow(handle, 6)  # SW_MINIMIZE
            return {"result": {"minimized": True, "handle": handle}}
        
        return {"error": "Not available on this platform"}
    
    def maximize_window(self, handle: int) -> Dict[str, Any]:
        """Maximize a window"""
        if IS_WINDOWS:
            import ctypes
            user32 = ctypes.windll.user32
            user32.ShowWindow(handle, 3)  # SW_MAXIMIZE
            return {"result": {"maximized": True, "handle": handle}}
        
        return {"error": "Not available on this platform"}
    
    def close_window(self, handle: int) -> Dict[str, Any]:
        """Close a window gracefully"""
        if IS_WINDOWS:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            
            WM_CLOSE = 0x0010
            user32.PostMessageW(handle, WM_CLOSE, 0, 0)
            return {
                "result": {"closed": True, "handle": handle},
                "side_effects": [{
                    "type": "window_closed",
                    "data": {"handle": handle},
                    "reversible": False,
                }]
            }
        
        return {"error": "Not available on this platform"}


# Module-level controller instances
_process_controller: Optional[ProcessController] = None
_app_controller: Optional[ApplicationController] = None
_window_controller: Optional[WindowController] = None


def get_process_controller() -> ProcessController:
    global _process_controller
    if _process_controller is None:
        _process_controller = ProcessController()
    return _process_controller


def get_app_controller() -> ApplicationController:
    global _app_controller
    if _app_controller is None:
        _app_controller = ApplicationController()
    return _app_controller


def get_window_controller() -> WindowController:
    global _window_controller
    if _window_controller is None:
        _window_controller = WindowController()
    return _window_controller
