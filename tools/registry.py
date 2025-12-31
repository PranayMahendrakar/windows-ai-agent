"""
Windows AI Agent - Tool Registry
Registers all available tools with their schemas and handlers
"""
from typing import Dict, List, Tuple, Any
import logging

from tools.server import ToolServer, ToolSchema, create_tool_schema
from core.types import ToolCategory, RiskLevel, PermissionTier

# Import controllers
from windows_control.filesystem import get_filesystem_controller
from windows_control.processes import (
    get_process_controller,
    get_app_controller,
    get_window_controller,
)
from windows_control.input import (
    get_keyboard_controller,
    get_mouse_controller,
    get_clipboard_controller,
)

logger = logging.getLogger(__name__)


def create_all_tools() -> List[Tuple[ToolSchema, callable]]:
    """Create all tool schemas and their handlers"""
    tools = []
    
    # Get controller instances
    fs = get_filesystem_controller()
    proc = get_process_controller()
    app = get_app_controller()
    win = get_window_controller()
    kbd = get_keyboard_controller()
    mouse = get_mouse_controller()
    clip = get_clipboard_controller()
    
    # ========== FILE SYSTEM TOOLS ==========
    
    # file_read
    tools.append((
        create_tool_schema(
            name="file_read",
            description="Read the contents of a file",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "path", "type": "string", "description": "Path to the file to read"},
                {"name": "encoding", "type": "string", "description": "File encoding", "default": "utf-8", "required": False},
            ],
        ),
        lambda args: fs.read_file(args["path"], args.get("encoding", "utf-8"))
    ))
    
    # file_write
    tools.append((
        create_tool_schema(
            name="file_write",
            description="Write content to a file (creates if doesn't exist)",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            parameters=[
                {"name": "path", "type": "string", "description": "Path to the file"},
                {"name": "content", "type": "string", "description": "Content to write"},
                {"name": "mode", "type": "string", "description": "Write mode: 'write' or 'append'", "default": "write", "required": False},
            ],
        ),
        lambda args: fs.write_file(args["path"], args["content"], args.get("mode", "write"))
    ))
    
    # file_delete
    tools.append((
        create_tool_schema(
            name="file_delete",
            description="Delete a file or directory",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            parameters=[
                {"name": "path", "type": "string", "description": "Path to delete"},
                {"name": "recursive", "type": "boolean", "description": "Delete directories recursively", "default": False, "required": False},
            ],
        ),
        lambda args: fs.delete(args["path"], args.get("recursive", False))
    ))
    
    # file_copy
    tools.append((
        create_tool_schema(
            name="file_copy",
            description="Copy a file or directory to a new location",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "source", "type": "string", "description": "Source path"},
                {"name": "destination", "type": "string", "description": "Destination path"},
                {"name": "overwrite", "type": "boolean", "description": "Overwrite if exists", "default": False, "required": False},
            ],
        ),
        lambda args: fs.copy(args["source"], args["destination"], args.get("overwrite", False))
    ))
    
    # file_move
    tools.append((
        create_tool_schema(
            name="file_move",
            description="Move or rename a file or directory",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "source", "type": "string", "description": "Source path"},
                {"name": "destination", "type": "string", "description": "Destination path"},
            ],
        ),
        lambda args: fs.move(args["source"], args["destination"])
    ))
    
    # directory_list
    tools.append((
        create_tool_schema(
            name="directory_list",
            description="List contents of a directory",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "path", "type": "string", "description": "Directory path"},
                {"name": "pattern", "type": "string", "description": "Glob pattern filter", "default": "*", "required": False},
                {"name": "recursive", "type": "boolean", "description": "Include subdirectories", "default": False, "required": False},
            ],
        ),
        lambda args: fs.list_directory(args["path"], args.get("pattern", "*"), args.get("recursive", False))
    ))
    
    # directory_create
    tools.append((
        create_tool_schema(
            name="directory_create",
            description="Create a new directory",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "path", "type": "string", "description": "Directory path to create"},
            ],
        ),
        lambda args: fs.create_directory(args["path"])
    ))
    
    # file_search
    tools.append((
        create_tool_schema(
            name="file_search",
            description="Search for files by name pattern or content",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "path", "type": "string", "description": "Directory to search in"},
                {"name": "pattern", "type": "string", "description": "File name pattern (glob)"},
                {"name": "content", "type": "string", "description": "Search for text in files", "required": False},
                {"name": "max_results", "type": "integer", "description": "Maximum results", "default": 100, "required": False},
            ],
        ),
        lambda args: fs.search_files(
            args["path"], 
            args["pattern"], 
            args.get("content"),
            args.get("max_results", 100)
        )
    ))
    
    # file_info
    tools.append((
        create_tool_schema(
            name="file_info",
            description="Get detailed information about a file or directory",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "path", "type": "string", "description": "Path to file or directory"},
            ],
        ),
        lambda args: fs.get_file_info(args["path"])
    ))
    
    # ========== APPLICATION TOOLS ==========
    
    # app_open
    tools.append((
        create_tool_schema(
            name="app_open",
            description="Open/launch an application",
            category=ToolCategory.APPLICATION,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "identifier", "type": "string", "description": "Application name or path (e.g., 'notepad', 'chrome', 'C:\\path\\to\\app.exe')"},
                {"name": "arguments", "type": "array", "description": "Command line arguments", "default": [], "required": False},
                {"name": "working_dir", "type": "string", "description": "Working directory", "required": False},
                {"name": "wait", "type": "boolean", "description": "Wait for app to close", "default": False, "required": False},
            ],
        ),
        lambda args: app.open_application(
            args["identifier"],
            args.get("arguments", []),
            args.get("working_dir"),
            args.get("wait", False),
        )
    ))
    
    # app_close
    tools.append((
        create_tool_schema(
            name="app_close",
            description="Close an application",
            category=ToolCategory.APPLICATION,
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            parameters=[
                {"name": "identifier", "type": "string", "description": "Application name", "required": False},
                {"name": "pid", "type": "integer", "description": "Process ID", "required": False},
                {"name": "force", "type": "boolean", "description": "Force close", "default": False, "required": False},
            ],
        ),
        lambda args: app.close_application(
            identifier=args.get("identifier"),
            pid=args.get("pid"),
            force=args.get("force", False),
        )
    ))
    
    # app_list_installed
    tools.append((
        create_tool_schema(
            name="app_list_installed",
            description="List installed applications",
            category=ToolCategory.APPLICATION,
            risk_level=RiskLevel.LOW,
            parameters=[],
        ),
        lambda args: app.list_installed_applications()
    ))
    
    # ========== PROCESS TOOLS ==========
    
    # process_list
    tools.append((
        create_tool_schema(
            name="process_list",
            description="List running processes",
            category=ToolCategory.SYSTEM,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "filter", "type": "string", "description": "Filter by process name", "required": False},
            ],
        ),
        lambda args: proc.list_processes(args.get("filter"))
    ))
    
    # process_info
    tools.append((
        create_tool_schema(
            name="process_info",
            description="Get detailed information about a process",
            category=ToolCategory.SYSTEM,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "pid", "type": "integer", "description": "Process ID"},
            ],
        ),
        lambda args: proc.get_process_info(args["pid"])
    ))
    
    # process_kill
    tools.append((
        create_tool_schema(
            name="process_kill",
            description="Terminate a process",
            category=ToolCategory.SYSTEM,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            parameters=[
                {"name": "pid", "type": "integer", "description": "Process ID", "required": False},
                {"name": "name", "type": "string", "description": "Process name", "required": False},
                {"name": "force", "type": "boolean", "description": "Force kill", "default": False, "required": False},
            ],
        ),
        lambda args: proc.kill_process(
            pid=args.get("pid"),
            name=args.get("name"),
            force=args.get("force", False),
        )
    ))
    
    # ========== WINDOW TOOLS ==========
    
    # window_list
    tools.append((
        create_tool_schema(
            name="window_list",
            description="List all visible windows",
            category=ToolCategory.UI_AUTOMATION,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "filter", "type": "string", "description": "Filter by window title", "required": False},
            ],
        ),
        lambda args: win.list_windows(args.get("filter"))
    ))
    
    # window_focus
    tools.append((
        create_tool_schema(
            name="window_focus",
            description="Bring a window to the foreground",
            category=ToolCategory.UI_AUTOMATION,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "handle", "type": "integer", "description": "Window handle", "required": False},
                {"name": "title", "type": "string", "description": "Window title", "required": False},
            ],
        ),
        lambda args: win.focus_window(args.get("handle"), args.get("title"))
    ))
    
    # window_minimize
    tools.append((
        create_tool_schema(
            name="window_minimize",
            description="Minimize a window",
            category=ToolCategory.UI_AUTOMATION,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "handle", "type": "integer", "description": "Window handle"},
            ],
        ),
        lambda args: win.minimize_window(args["handle"])
    ))
    
    # window_maximize
    tools.append((
        create_tool_schema(
            name="window_maximize",
            description="Maximize a window",
            category=ToolCategory.UI_AUTOMATION,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "handle", "type": "integer", "description": "Window handle"},
            ],
        ),
        lambda args: win.maximize_window(args["handle"])
    ))
    
    # window_close
    tools.append((
        create_tool_schema(
            name="window_close",
            description="Close a window",
            category=ToolCategory.UI_AUTOMATION,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "handle", "type": "integer", "description": "Window handle"},
            ],
        ),
        lambda args: win.close_window(args["handle"])
    ))
    
    # ========== INPUT TOOLS ==========
    
    # keyboard_type
    tools.append((
        create_tool_schema(
            name="keyboard_type",
            description="Type text using the keyboard",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "text", "type": "string", "description": "Text to type"},
                {"name": "interval", "type": "number", "description": "Delay between keys (seconds)", "default": 0.02, "required": False},
            ],
        ),
        lambda args: kbd.type_text(args["text"], args.get("interval", 0.02))
    ))
    
    # keyboard_press
    tools.append((
        create_tool_schema(
            name="keyboard_press",
            description="Press a single key",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "key", "type": "string", "description": "Key to press (e.g., 'enter', 'tab', 'escape', 'a', 'f1')"},
            ],
        ),
        lambda args: kbd.press_key(args["key"])
    ))
    
    # keyboard_hotkey
    tools.append((
        create_tool_schema(
            name="keyboard_hotkey",
            description="Press a keyboard shortcut/hotkey combination",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "keys", "type": "array", "description": "Keys to press together (e.g., ['ctrl', 'c'], ['alt', 'f4'])"},
            ],
        ),
        lambda args: kbd.press_hotkey(args["keys"])
    ))
    
    # mouse_click
    tools.append((
        create_tool_schema(
            name="mouse_click",
            description="Click the mouse at a position",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "x", "type": "integer", "description": "X coordinate", "required": False},
                {"name": "y", "type": "integer", "description": "Y coordinate", "required": False},
                {"name": "button", "type": "string", "description": "Button: 'left', 'right', 'middle'", "default": "left", "required": False},
                {"name": "clicks", "type": "integer", "description": "Number of clicks", "default": 1, "required": False},
            ],
        ),
        lambda args: mouse.click(
            args.get("x"),
            args.get("y"),
            args.get("button", "left"),
            args.get("clicks", 1),
        )
    ))
    
    # mouse_move
    tools.append((
        create_tool_schema(
            name="mouse_move",
            description="Move the mouse to a position",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "x", "type": "integer", "description": "X coordinate"},
                {"name": "y", "type": "integer", "description": "Y coordinate"},
                {"name": "duration", "type": "number", "description": "Animation duration (seconds)", "default": 0, "required": False},
            ],
        ),
        lambda args: mouse.move_to(args["x"], args["y"], args.get("duration", 0))
    ))
    
    # mouse_scroll
    tools.append((
        create_tool_schema(
            name="mouse_scroll",
            description="Scroll the mouse wheel",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "clicks", "type": "integer", "description": "Scroll amount (positive=up, negative=down)"},
                {"name": "x", "type": "integer", "description": "X coordinate", "required": False},
                {"name": "y", "type": "integer", "description": "Y coordinate", "required": False},
            ],
        ),
        lambda args: mouse.scroll(args["clicks"], args.get("x"), args.get("y"))
    ))
    
    # mouse_drag
    tools.append((
        create_tool_schema(
            name="mouse_drag",
            description="Drag the mouse from one position to another",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.MEDIUM,
            parameters=[
                {"name": "start_x", "type": "integer", "description": "Start X coordinate"},
                {"name": "start_y", "type": "integer", "description": "Start Y coordinate"},
                {"name": "end_x", "type": "integer", "description": "End X coordinate"},
                {"name": "end_y", "type": "integer", "description": "End Y coordinate"},
                {"name": "duration", "type": "number", "description": "Drag duration (seconds)", "default": 0.5, "required": False},
            ],
        ),
        lambda args: mouse.drag(
            args["start_x"],
            args["start_y"],
            args["end_x"],
            args["end_y"],
            args.get("duration", 0.5),
        )
    ))
    
    # mouse_position
    tools.append((
        create_tool_schema(
            name="mouse_position",
            description="Get current mouse cursor position",
            category=ToolCategory.INPUT,
            risk_level=RiskLevel.LOW,
            parameters=[],
        ),
        lambda args: mouse.get_position()
    ))
    
    # ========== CLIPBOARD TOOLS ==========
    
    # clipboard_get
    tools.append((
        create_tool_schema(
            name="clipboard_get",
            description="Get text from clipboard",
            category=ToolCategory.CLIPBOARD,
            risk_level=RiskLevel.LOW,
            parameters=[],
        ),
        lambda args: clip.get_text()
    ))
    
    # clipboard_set
    tools.append((
        create_tool_schema(
            name="clipboard_set",
            description="Set text to clipboard",
            category=ToolCategory.CLIPBOARD,
            risk_level=RiskLevel.LOW,
            parameters=[
                {"name": "text", "type": "string", "description": "Text to copy to clipboard"},
            ],
        ),
        lambda args: clip.set_text(args["text"])
    ))
    
    # clipboard_clear
    tools.append((
        create_tool_schema(
            name="clipboard_clear",
            description="Clear the clipboard",
            category=ToolCategory.CLIPBOARD,
            risk_level=RiskLevel.LOW,
            parameters=[],
        ),
        lambda args: clip.clear()
    ))
    
    return tools


def register_all_tools(server: ToolServer):
    """Register all tools with the server"""
    tools = create_all_tools()
    
    for schema, handler in tools:
        server.register_tool(schema, handler)
    
    logger.info(f"Registered {len(tools)} tools")
    return server


def get_tool_server() -> ToolServer:
    """Create and return a configured tool server with all tools registered"""
    server = ToolServer()
    register_all_tools(server)
    return server
