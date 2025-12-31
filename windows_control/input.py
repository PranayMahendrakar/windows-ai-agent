"""
Windows AI Agent - Input Simulation Controller
Handles keyboard and mouse input simulation
"""
import sys
import time
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    
    # Input type constants
    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1
    
    # Key event flags
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_SCANCODE = 0x0008
    
    # Mouse event flags
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000
    
    # Virtual key codes
    VK_CODES = {
        'backspace': 0x08, 'tab': 0x09, 'enter': 0x0D, 'return': 0x0D,
        'shift': 0x10, 'ctrl': 0x11, 'control': 0x11, 'alt': 0x12,
        'pause': 0x13, 'capslock': 0x14, 'escape': 0x1B, 'esc': 0x1B,
        'space': 0x20, 'pageup': 0x21, 'pagedown': 0x22,
        'end': 0x23, 'home': 0x24,
        'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
        'printscreen': 0x2C, 'insert': 0x2D, 'delete': 0x2E,
        'win': 0x5B, 'windows': 0x5B, 'apps': 0x5D,
        'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
        'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
        'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
        'numlock': 0x90, 'scrolllock': 0x91,
    }
    
    # Add letters and numbers
    for c in 'abcdefghijklmnopqrstuvwxyz':
        VK_CODES[c] = ord(c.upper())
    for c in '0123456789':
        VK_CODES[c] = ord(c)
    
    # Structures for SendInput
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
            ]
        _anonymous_ = ("_input",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("_input", _INPUT),
        ]


class KeyboardController:
    """
    Keyboard Controller
    Simulates keyboard input on Windows
    """
    
    def __init__(self):
        self._typing_delay = 0.02  # Delay between keystrokes
    
    def type_text(
        self,
        text: str,
        interval: float = 0.02,
    ) -> Dict[str, Any]:
        """Type text character by character"""
        if IS_WINDOWS:
            return self._type_text_windows(text, interval)
        else:
            return self._type_text_mock(text)
    
    def _type_text_windows(self, text: str, interval: float) -> Dict[str, Any]:
        """Type text using Windows SendInput"""
        user32 = ctypes.windll.user32
        
        for char in text:
            # Create key down event
            inputs = []
            
            # Use unicode input for most characters
            ki_down = KEYBDINPUT(
                wVk=0,
                wScan=ord(char),
                dwFlags=KEYEVENTF_UNICODE,
                time=0,
                dwExtraInfo=None,
            )
            input_down = INPUT(type=INPUT_KEYBOARD)
            input_down.ki = ki_down
            inputs.append(input_down)
            
            # Key up
            ki_up = KEYBDINPUT(
                wVk=0,
                wScan=ord(char),
                dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                time=0,
                dwExtraInfo=None,
            )
            input_up = INPUT(type=INPUT_KEYBOARD)
            input_up.ki = ki_up
            inputs.append(input_up)
            
            # Send inputs
            array = (INPUT * len(inputs))(*inputs)
            user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
            
            if interval > 0:
                time.sleep(interval)
        
        return {
            "result": {
                "typed": True,
                "text": text,
                "length": len(text),
            }
        }
    
    def _type_text_mock(self, text: str) -> Dict[str, Any]:
        """Mock typing for non-Windows"""
        logger.info(f"[MOCK] Would type: {text}")
        return {
            "result": {
                "typed": True,
                "text": text,
                "length": len(text),
                "note": "Mock - not actually typed",
            }
        }
    
    def press_key(self, key: str) -> Dict[str, Any]:
        """Press and release a single key"""
        if IS_WINDOWS:
            return self._press_key_windows(key)
        else:
            return {"result": {"pressed": True, "key": key, "note": "Mock"}}
    
    def _press_key_windows(self, key: str) -> Dict[str, Any]:
        """Press key on Windows"""
        user32 = ctypes.windll.user32
        
        vk = VK_CODES.get(key.lower())
        if vk is None:
            # Try as single character
            if len(key) == 1:
                vk = ord(key.upper())
            else:
                return {"error": f"Unknown key: {key}"}
        
        # Key down
        user32.keybd_event(vk, 0, 0, 0)
        # Key up
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        
        return {"result": {"pressed": True, "key": key}}
    
    def press_hotkey(self, keys: List[str]) -> Dict[str, Any]:
        """Press a hotkey combination (e.g., ['ctrl', 'c'])"""
        if IS_WINDOWS:
            return self._press_hotkey_windows(keys)
        else:
            return {"result": {"pressed": True, "keys": keys, "note": "Mock"}}
    
    def _press_hotkey_windows(self, keys: List[str]) -> Dict[str, Any]:
        """Press hotkey on Windows"""
        user32 = ctypes.windll.user32
        
        # Get virtual key codes
        vk_codes = []
        for key in keys:
            vk = VK_CODES.get(key.lower())
            if vk is None:
                if len(key) == 1:
                    vk = ord(key.upper())
                else:
                    return {"error": f"Unknown key: {key}"}
            vk_codes.append(vk)
        
        # Press all keys down
        for vk in vk_codes:
            user32.keybd_event(vk, 0, 0, 0)
        
        time.sleep(0.05)
        
        # Release all keys (in reverse order)
        for vk in reversed(vk_codes):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        
        return {"result": {"pressed": True, "keys": keys}}
    
    def hold_key(self, key: str, duration: float = 0.5) -> Dict[str, Any]:
        """Hold a key for a duration"""
        if IS_WINDOWS:
            user32 = ctypes.windll.user32
            vk = VK_CODES.get(key.lower(), ord(key.upper()) if len(key) == 1 else None)
            
            if vk is None:
                return {"error": f"Unknown key: {key}"}
            
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(duration)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            
            return {"result": {"held": True, "key": key, "duration": duration}}
        
        return {"result": {"held": True, "key": key, "note": "Mock"}}


class MouseController:
    """
    Mouse Controller
    Simulates mouse input on Windows
    """
    
    def __init__(self):
        self._screen_width = 1920
        self._screen_height = 1080
        
        if IS_WINDOWS:
            user32 = ctypes.windll.user32
            self._screen_width = user32.GetSystemMetrics(0)
            self._screen_height = user32.GetSystemMetrics(1)
    
    def get_position(self) -> Dict[str, Any]:
        """Get current mouse position"""
        if IS_WINDOWS:
            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
            
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return {"result": {"x": pt.x, "y": pt.y}}
        
        return {"result": {"x": 0, "y": 0, "note": "Mock"}}
    
    def move_to(
        self,
        x: int,
        y: int,
        duration: float = 0,
    ) -> Dict[str, Any]:
        """Move mouse to absolute position"""
        if IS_WINDOWS:
            return self._move_to_windows(x, y, duration)
        else:
            return {"result": {"moved": True, "x": x, "y": y, "note": "Mock"}}
    
    def _move_to_windows(self, x: int, y: int, duration: float) -> Dict[str, Any]:
        """Move mouse on Windows"""
        user32 = ctypes.windll.user32
        
        if duration > 0:
            # Smooth movement
            pos = self.get_position()["result"]
            start_x, start_y = pos["x"], pos["y"]
            steps = int(duration * 60)  # 60 steps per second
            
            for i in range(steps + 1):
                progress = i / steps
                curr_x = int(start_x + (x - start_x) * progress)
                curr_y = int(start_y + (y - start_y) * progress)
                user32.SetCursorPos(curr_x, curr_y)
                time.sleep(duration / steps)
        else:
            user32.SetCursorPos(x, y)
        
        return {"result": {"moved": True, "x": x, "y": y}}
    
    def click(
        self,
        x: int = None,
        y: int = None,
        button: str = "left",
        clicks: int = 1,
    ) -> Dict[str, Any]:
        """Click at position (or current position if x,y not specified)"""
        if IS_WINDOWS:
            return self._click_windows(x, y, button, clicks)
        else:
            return {"result": {"clicked": True, "button": button, "note": "Mock"}}
    
    def _click_windows(
        self,
        x: int,
        y: int,
        button: str,
        clicks: int,
    ) -> Dict[str, Any]:
        """Click on Windows"""
        user32 = ctypes.windll.user32
        
        # Move to position if specified
        if x is not None and y is not None:
            user32.SetCursorPos(x, y)
        
        # Determine button flags
        if button == "left":
            down_flag = MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_LEFTUP
        elif button == "right":
            down_flag = MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            down_flag = MOUSEEVENTF_MIDDLEDOWN
            up_flag = MOUSEEVENTF_MIDDLEUP
        else:
            return {"error": f"Unknown button: {button}"}
        
        # Perform clicks
        for _ in range(clicks):
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.01)
            user32.mouse_event(up_flag, 0, 0, 0, 0)
            if clicks > 1:
                time.sleep(0.1)
        
        pos = self.get_position()["result"]
        return {
            "result": {
                "clicked": True,
                "x": pos["x"],
                "y": pos["y"],
                "button": button,
                "clicks": clicks,
            }
        }
    
    def double_click(self, x: int = None, y: int = None) -> Dict[str, Any]:
        """Double-click at position"""
        return self.click(x, y, "left", clicks=2)
    
    def right_click(self, x: int = None, y: int = None) -> Dict[str, Any]:
        """Right-click at position"""
        return self.click(x, y, "right", clicks=1)
    
    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> Dict[str, Any]:
        """Drag from one position to another"""
        if IS_WINDOWS:
            return self._drag_windows(start_x, start_y, end_x, end_y, duration, button)
        else:
            return {"result": {"dragged": True, "note": "Mock"}}
    
    def _drag_windows(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float,
        button: str,
    ) -> Dict[str, Any]:
        """Drag on Windows"""
        user32 = ctypes.windll.user32
        
        # Determine button flags
        if button == "left":
            down_flag = MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_LEFTUP
        elif button == "right":
            down_flag = MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_RIGHTUP
        else:
            return {"error": f"Unknown button: {button}"}
        
        # Move to start
        user32.SetCursorPos(start_x, start_y)
        time.sleep(0.05)
        
        # Press button
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        
        # Smooth movement to end
        steps = int(duration * 60)
        for i in range(steps + 1):
            progress = i / steps
            curr_x = int(start_x + (end_x - start_x) * progress)
            curr_y = int(start_y + (end_y - start_y) * progress)
            user32.SetCursorPos(curr_x, curr_y)
            time.sleep(duration / steps)
        
        # Release button
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        
        return {
            "result": {
                "dragged": True,
                "start": {"x": start_x, "y": start_y},
                "end": {"x": end_x, "y": end_y},
                "button": button,
            }
        }
    
    def scroll(
        self,
        clicks: int,
        x: int = None,
        y: int = None,
    ) -> Dict[str, Any]:
        """Scroll wheel (positive = up, negative = down)"""
        if IS_WINDOWS:
            user32 = ctypes.windll.user32
            
            if x is not None and y is not None:
                user32.SetCursorPos(x, y)
            
            # WHEEL_DELTA = 120
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, clicks * 120, 0)
            
            return {"result": {"scrolled": True, "clicks": clicks}}
        
        return {"result": {"scrolled": True, "clicks": clicks, "note": "Mock"}}


class ClipboardController:
    """
    Clipboard Controller
    Manages clipboard operations
    """
    
    def get_text(self) -> Dict[str, Any]:
        """Get text from clipboard"""
        if IS_WINDOWS:
            import ctypes
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            user32.OpenClipboard(0)
            try:
                if user32.IsClipboardFormatAvailable(1):  # CF_TEXT
                    data = user32.GetClipboardData(13)  # CF_UNICODETEXT
                    if data:
                        text = ctypes.c_wchar_p(data).value
                        return {"result": {"text": text}}
                return {"result": {"text": ""}}
            finally:
                user32.CloseClipboard()
        
        # Try pyperclip or xclip on Linux
        try:
            import subprocess
            result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'],
                                  capture_output=True, text=True)
            return {"result": {"text": result.stdout}}
        except:
            return {"result": {"text": "", "note": "Clipboard not available"}}
    
    def set_text(self, text: str) -> Dict[str, Any]:
        """Set text to clipboard"""
        if IS_WINDOWS:
            import ctypes
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            user32.OpenClipboard(0)
            try:
                user32.EmptyClipboard()
                
                # Allocate global memory
                hMem = kernel32.GlobalAlloc(0x0042, (len(text) + 1) * 2)  # GMEM_MOVEABLE | GMEM_ZEROINIT
                pMem = kernel32.GlobalLock(hMem)
                ctypes.memmove(pMem, text.encode('utf-16-le'), len(text) * 2)
                kernel32.GlobalUnlock(hMem)
                
                user32.SetClipboardData(13, hMem)  # CF_UNICODETEXT
                
                return {"result": {"set": True, "length": len(text)}}
            finally:
                user32.CloseClipboard()
        
        # Try xclip on Linux
        try:
            import subprocess
            subprocess.run(['xclip', '-selection', 'clipboard'],
                         input=text.encode(), check=True)
            return {"result": {"set": True, "length": len(text)}}
        except:
            return {"error": "Clipboard not available"}
    
    def clear(self) -> Dict[str, Any]:
        """Clear clipboard"""
        if IS_WINDOWS:
            import ctypes
            user32 = ctypes.windll.user32
            user32.OpenClipboard(0)
            user32.EmptyClipboard()
            user32.CloseClipboard()
            return {"result": {"cleared": True}}
        
        return self.set_text("")


# Singleton instances
_keyboard: Optional[KeyboardController] = None
_mouse: Optional[MouseController] = None
_clipboard: Optional[ClipboardController] = None


def get_keyboard_controller() -> KeyboardController:
    global _keyboard
    if _keyboard is None:
        _keyboard = KeyboardController()
    return _keyboard


def get_mouse_controller() -> MouseController:
    global _mouse
    if _mouse is None:
        _mouse = MouseController()
    return _mouse


def get_clipboard_controller() -> ClipboardController:
    global _clipboard
    if _clipboard is None:
        _clipboard = ClipboardController()
    return _clipboard
