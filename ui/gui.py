"""
Windows AI Agent - PyQt6 GUI Interface
Modern chat-style interface for the Windows AI Agent
"""
import sys
import os
from typing import Optional
from datetime import datetime

# Check if PyQt6 is available
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QPushButton, QLabel, QScrollArea,
        QFrame, QSplitter, QListWidget, QListWidgetItem, QMessageBox,
        QSystemTrayIcon, QMenu, QStatusBar, QToolBar, QDialog,
        QDialogButtonBox, QCheckBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
    from PyQt6.QtGui import QFont, QIcon, QAction, QColor, QPalette, QTextCursor
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
    print("PyQt6 not installed. Install with: pip install PyQt6")

if HAS_PYQT:
    # Add parent to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from orchestrator.agent import AgentOrchestrator, create_agent
    from core.types import ToolRequest, ToolResult, ExecutionStatus
    
    
    class AgentWorker(QThread):
        """Worker thread for agent processing"""
        response_ready = pyqtSignal(str)
        thinking = pyqtSignal(str)
        tool_call = pyqtSignal(str, dict)
        tool_result = pyqtSignal(str, bool)
        error = pyqtSignal(str)
        
        def __init__(self, agent: AgentOrchestrator, message: str):
            super().__init__()
            self.agent = agent
            self.message = message
        
        def run(self):
            try:
                # Set up callbacks
                self.agent.set_callbacks(
                    on_thinking=lambda t: self.thinking.emit(t),
                    on_tool_call=lambda r: self.tool_call.emit(r.tool, r.arguments),
                    on_tool_result=lambda r: self.tool_result.emit(
                        r.status.value, 
                        r.status == ExecutionStatus.SUCCESS
                    ),
                )
                
                response = self.agent.process(self.message)
                self.response_ready.emit(response)
            except Exception as e:
                self.error.emit(str(e))
    
    
    class ConfirmationDialog(QDialog):
        """Dialog for confirming tool execution"""
        
        def __init__(self, request: ToolRequest, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Confirm Action")
            self.setMinimumWidth(400)
            
            layout = QVBoxLayout(self)
            
            # Warning icon and message
            msg = QLabel(f"⚠️ The AI wants to perform: <b>{request.tool}</b>")
            msg.setWordWrap(True)
            layout.addWidget(msg)
            
            # Arguments
            args_text = QTextEdit()
            args_text.setReadOnly(True)
            args_text.setMaximumHeight(100)
            import json
            args_text.setPlainText(json.dumps(request.arguments, indent=2))
            layout.addWidget(args_text)
            
            # Remember choice checkbox
            self.remember = QCheckBox("Remember this choice for this session")
            layout.addWidget(self.remember)
            
            # Buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Yes | 
                QDialogButtonBox.StandardButton.No
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
    
    
    class ChatMessage(QFrame):
        """A single chat message widget"""
        
        def __init__(self, text: str, is_user: bool, parent=None):
            super().__init__(parent)
            self.setFrameStyle(QFrame.Shape.StyledPanel)
            
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 5, 10, 5)
            
            # Role label
            role = QLabel("You" if is_user else "🤖 WindowsAI")
            role.setStyleSheet("font-weight: bold; color: #666;")
            layout.addWidget(role)
            
            # Message text
            msg = QLabel(text)
            msg.setWordWrap(True)
            msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(msg)
            
            # Style based on sender
            if is_user:
                self.setStyleSheet("""
                    ChatMessage {
                        background-color: #e3f2fd;
                        border-radius: 10px;
                        margin-left: 50px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    ChatMessage {
                        background-color: #f5f5f5;
                        border-radius: 10px;
                        margin-right: 50px;
                    }
                """)
    
    
    class MainWindow(QMainWindow):
        """Main application window"""
        
        def __init__(self, model: str = "llama4"):
            super().__init__()
            self.model = model
            self.agent: Optional[AgentOrchestrator] = None
            self.worker: Optional[AgentWorker] = None
            self.auto_confirm = False
            
            self.setWindowTitle("Windows AI Agent")
            self.setMinimumSize(800, 600)
            
            self._setup_ui()
            self._setup_agent()
        
        def _setup_ui(self):
            """Setup the user interface"""
            # Central widget
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            
            # Chat area
            self.chat_scroll = QScrollArea()
            self.chat_scroll.setWidgetResizable(True)
            self.chat_widget = QWidget()
            self.chat_layout = QVBoxLayout(self.chat_widget)
            self.chat_layout.addStretch()
            self.chat_scroll.setWidget(self.chat_widget)
            layout.addWidget(self.chat_scroll, stretch=1)
            
            # Status area for tool execution
            self.status_label = QLabel("")
            self.status_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(self.status_label)
            
            # Input area
            input_layout = QHBoxLayout()
            
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Type your message...")
            self.input_field.returnPressed.connect(self._send_message)
            input_layout.addWidget(self.input_field)
            
            self.send_button = QPushButton("Send")
            self.send_button.clicked.connect(self._send_message)
            input_layout.addWidget(self.send_button)
            
            layout.addLayout(input_layout)
            
            # Status bar
            self.statusBar().showMessage("Initializing...")
            
            # Toolbar
            toolbar = QToolBar()
            self.addToolBar(toolbar)
            
            new_action = QAction("New Chat", self)
            new_action.triggered.connect(self._new_chat)
            toolbar.addAction(new_action)
            
            tools_action = QAction("Show Tools", self)
            tools_action.triggered.connect(self._show_tools)
            toolbar.addAction(tools_action)
            
            autoconfirm_action = QAction("Auto-Confirm", self)
            autoconfirm_action.setCheckable(True)
            autoconfirm_action.triggered.connect(self._toggle_autoconfirm)
            toolbar.addAction(autoconfirm_action)
        
        def _setup_agent(self):
            """Initialize the agent"""
            self.agent = create_agent(
                model=self.model,
                verbose=False,
                confirmation_handler=self._handle_confirmation,
            )
            
            if self.agent.is_ready():
                tool_count = len(self.agent.get_available_tools())
                self.statusBar().showMessage(f"Ready - {tool_count} tools available")
                self._add_system_message(
                    f"Welcome! I'm your Windows AI assistant with {tool_count} tools. "
                    "How can I help you today?"
                )
            else:
                self.statusBar().showMessage("Error: Cannot connect to Ollama")
                self._add_system_message(
                    "⚠️ Cannot connect to Ollama. Please make sure it's running."
                )
        
        def _handle_confirmation(self, request: ToolRequest) -> bool:
            """Handle confirmation requests"""
            if self.auto_confirm:
                return True
            
            dialog = ConfirmationDialog(request, self)
            result = dialog.exec()
            return result == QDialog.DialogCode.Accepted
        
        def _add_message(self, text: str, is_user: bool):
            """Add a message to the chat"""
            # Remove stretch
            self.chat_layout.takeAt(self.chat_layout.count() - 1)
            
            # Add message
            msg_widget = ChatMessage(text, is_user)
            self.chat_layout.addWidget(msg_widget)
            
            # Re-add stretch
            self.chat_layout.addStretch()
            
            # Scroll to bottom
            QTimer.singleShot(100, self._scroll_to_bottom)
        
        def _add_system_message(self, text: str):
            """Add a system message"""
            self._add_message(text, is_user=False)
        
        def _scroll_to_bottom(self):
            """Scroll chat to bottom"""
            scrollbar = self.chat_scroll.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        def _send_message(self):
            """Send the current message"""
            text = self.input_field.text().strip()
            if not text:
                return
            
            if not self.agent or not self.agent.is_ready():
                QMessageBox.warning(self, "Error", "Agent not ready")
                return
            
            # Disable input while processing
            self.input_field.setEnabled(False)
            self.send_button.setEnabled(False)
            
            # Add user message
            self._add_message(text, is_user=True)
            self.input_field.clear()
            
            # Start worker thread
            self.worker = AgentWorker(self.agent, text)
            self.worker.thinking.connect(self._on_thinking)
            self.worker.tool_call.connect(self._on_tool_call)
            self.worker.tool_result.connect(self._on_tool_result)
            self.worker.response_ready.connect(self._on_response)
            self.worker.error.connect(self._on_error)
            self.worker.finished.connect(self._on_finished)
            self.worker.start()
        
        def _on_thinking(self, thought: str):
            """Handle thinking event"""
            self.status_label.setText(f"💭 {thought}")
        
        def _on_tool_call(self, tool: str, args: dict):
            """Handle tool call event"""
            self.status_label.setText(f"🔧 Executing: {tool}")
        
        def _on_tool_result(self, status: str, success: bool):
            """Handle tool result event"""
            icon = "✅" if success else "❌"
            self.status_label.setText(f"{icon} {status}")
        
        def _on_response(self, response: str):
            """Handle response ready"""
            self._add_message(response, is_user=False)
            self.status_label.setText("")
        
        def _on_error(self, error: str):
            """Handle error"""
            self._add_system_message(f"❌ Error: {error}")
            self.status_label.setText("")
        
        def _on_finished(self):
            """Handle worker finished"""
            self.input_field.setEnabled(True)
            self.send_button.setEnabled(True)
            self.input_field.setFocus()
        
        def _new_chat(self):
            """Start a new chat"""
            if self.agent:
                self.agent.reset_conversation()
            
            # Clear chat
            while self.chat_layout.count() > 1:
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            self._add_system_message("Chat reset. How can I help you?")
        
        def _show_tools(self):
            """Show available tools"""
            if not self.agent:
                return
            
            tools = sorted(self.agent.get_available_tools())
            tool_list = "\n".join([f"• {t}" for t in tools])
            
            QMessageBox.information(
                self,
                "Available Tools",
                f"The agent has access to {len(tools)} tools:\n\n{tool_list}"
            )
        
        def _toggle_autoconfirm(self, checked: bool):
            """Toggle auto-confirm mode"""
            self.auto_confirm = checked
            status = "enabled" if checked else "disabled"
            self.statusBar().showMessage(f"Auto-confirm {status}", 3000)
    
    
    def run_gui(model: str = "llama4"):
        """Run the GUI application"""
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        window = MainWindow(model=model)
        window.show()
        
        sys.exit(app.exec())


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Windows AI Agent GUI")
    parser.add_argument("--model", default="llama4", help="Ollama model")
    args = parser.parse_args()
    
    if not HAS_PYQT:
        print("Error: PyQt6 is required for the GUI.")
        print("Install with: pip install PyQt6")
        sys.exit(1)
    
    run_gui(model=args.model)


if __name__ == "__main__":
    main()
