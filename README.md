# 🤖 Windows AI Agent

**Offline AI-powered Windows control system using LLaMA 4 + MCP-style tools**

A fully offline desktop agent that can control your Windows PC through natural language. Built with local LLM inference via Ollama, inspired by the Model Context Protocol (MCP) architecture.

## ✨ Features

- **100% Offline** - No internet required after setup
- **Natural Language Control** - Just tell it what to do
- **30+ Tools** - File operations, app control, input simulation, and more
- **Safe by Design** - Confirmation prompts for destructive actions
- **Extensible** - Easy to add new tools

## 🚀 Quick Start

### Prerequisites

1. **Ollama** - Install from [ollama.ai](https://ollama.ai)
2. **Python 3.10+** - Install from [python.org](https://python.org)
3. **LLaMA 4** - Pull the model:
   ```bash
   ollama pull llama4
   ```

### Installation

```bash
# Clone or extract the project
cd windows-ai-agent

# Install dependencies
pip install requests

# Optional: For Windows-specific features
pip install psutil pywin32

# Optional: For GUI
pip install PyQt6
```

### Running

**Test the system first:**
```bash
python test_system.py
```

**CLI Interface:**
```bash
python main.py
```

**GUI Interface:**
```bash
python ui/gui.py
```

**Or on Windows, just double-click:**
- `run_cli.bat` - Command line interface
- `run_gui.bat` - Graphical interface
- `run_test.bat` - System test

## 📁 Project Structure

```
windows-ai-agent/
├── main.py                 # Entry point
├── test_system.py          # System verification
├── requirements.txt        # Dependencies
│
├── core/                   # Core types and utilities
│   └── types.py            # Data classes and enums
│
├── config/                 # Configuration
│   └── settings.py         # Agent settings
│
├── llm/                    # LLM integration
│   └── client.py           # Ollama client
│
├── tools/                  # Tool system
│   ├── server.py           # MCP-style tool server
│   └── registry.py         # Tool definitions
│
├── windows_control/        # Windows control layer
│   ├── filesystem.py       # File operations
│   ├── processes.py        # Process/app control
│   └── input.py            # Keyboard/mouse
│
├── orchestrator/           # Agent intelligence
│   └── agent.py            # Main agent logic
│
└── ui/                     # User interfaces
    ├── cli.py              # Command line
    └── gui.py              # PyQt6 GUI
```

## 🔧 Available Tools

### File System
- `file_read` - Read file contents
- `file_write` - Write/create files
- `file_delete` - Delete files/folders
- `file_copy` - Copy files
- `file_move` - Move/rename files
- `file_search` - Search by name/content
- `file_info` - Get file metadata
- `directory_list` - List folder contents
- `directory_create` - Create folders

### Applications
- `app_open` - Launch applications
- `app_close` - Close applications
- `app_list_installed` - List installed apps

### Processes
- `process_list` - List running processes
- `process_info` - Get process details
- `process_kill` - Terminate processes

### Windows
- `window_list` - List open windows
- `window_focus` - Focus a window
- `window_minimize` - Minimize window
- `window_maximize` - Maximize window
- `window_close` - Close window

### Input
- `keyboard_type` - Type text
- `keyboard_press` - Press key
- `keyboard_hotkey` - Press key combo
- `mouse_click` - Click mouse
- `mouse_move` - Move cursor
- `mouse_scroll` - Scroll wheel
- `mouse_drag` - Drag operation
- `mouse_position` - Get cursor position

### Clipboard
- `clipboard_get` - Get clipboard text
- `clipboard_set` - Set clipboard text
- `clipboard_clear` - Clear clipboard

## 💡 Example Usage

```
You: Open notepad
🤖 I'll open Notepad for you.
   🔧 Executing: app_open
   ✅ Success
🤖 Notepad is now open!

You: List files in my Documents folder
🤖 Let me check your Documents folder.
   🔧 Executing: directory_list
   ✅ Success
🤖 Found 15 items in your Documents folder:
   - report.docx (2.3 MB)
   - photos/ (folder)
   ...

You: Create a new folder called "Projects" on my desktop
🤖 I'll create that folder for you.
   🔧 Executing: directory_create
   ✅ Success
🤖 Created "Projects" folder on your desktop!
```

## ⚙️ Configuration

Edit `config/settings.py` or create `config/agent_config.json`:

```json
{
  "llm": {
    "model": "llama4",
    "base_url": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "security": {
    "default_permission_tier": "operator",
    "tools_requiring_confirmation": [
      "file_delete",
      "process_kill"
    ]
  }
}
```

## 🔒 Security

- **Protected Paths**: Cannot modify C:\Windows, Program Files
- **Confirmation**: Destructive actions require approval
- **Permission Tiers**: Observer → Operator → Administrator → System
- **Audit Trail**: All actions are logged

## 🛠️ Troubleshooting

**"Cannot connect to Ollama"**
```bash
# Make sure Ollama is running
ollama serve

# Check if model is available
ollama list
```

**"Model not found"**
```bash
# Pull the model
ollama pull llama4

# Or try a specific version
ollama pull llama4:latest
```

**"Tool execution failed"**
- Check if you have necessary permissions
- Some tools require admin rights on Windows
- Install `psutil` and `pywin32` for full functionality

## 📝 Adding Custom Tools

Create a new tool in `tools/registry.py`:

```python
# Add to create_all_tools() function
tools.append((
    create_tool_schema(
        name="my_custom_tool",
        description="Description of what it does",
        category=ToolCategory.SYSTEM,
        risk_level=RiskLevel.LOW,
        parameters=[
            {"name": "param1", "type": "string", "description": "Parameter description"},
        ],
    ),
    lambda args: {"result": {"success": True, "data": args["param1"]}}
))
```

## 🗺️ Roadmap

- [ ] Voice input (Whisper)
- [ ] Voice output (TTS)
- [ ] UI Automation (clicking buttons by name)
- [ ] Screenshot analysis
- [ ] Memory/context persistence
- [ ] Multi-step task planning
- [ ] Plugin system

## 📜 License

MIT License - Use freely for personal and commercial projects.

## 🙏 Credits

- **Ollama** - Local LLM inference
- **LLaMA** - Meta's language model
- **Anthropic MCP** - Protocol inspiration

---

Built with ❤️ for offline AI automation
