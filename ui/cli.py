"""
Windows AI Agent - Command Line Interface
Interactive CLI for testing and using the agent
"""
import sys
import os
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.agent import AgentOrchestrator, create_agent
from core.types import ToolRequest, ToolResult, ExecutionStatus
from tools.registry import get_tool_server


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentCLI:
    """
    Command Line Interface for Windows AI Agent
    """
    
    def __init__(self, model: str = "llama4"):
        self.model = model
        self.agent: Optional[AgentOrchestrator] = None
        self.auto_confirm = False
        
    def _print_header(self):
        """Print welcome header"""
        print("\n" + "=" * 60)
        print("  🤖 Windows AI Agent - Offline Desktop Control")
        print("=" * 60)
        print(f"  Model: {self.model}")
        print("  Type 'help' for commands, 'quit' to exit")
        print("=" * 60 + "\n")
    
    def _print_help(self):
        """Print help information"""
        print("""
Available Commands:
  help              - Show this help message
  quit/exit         - Exit the agent
  reset             - Start a new conversation
  tools             - List available tools
  status            - Show agent status
  autoconfirm [on/off] - Toggle auto-confirmation for actions
  
Just type naturally to interact with the AI agent.
Examples:
  "Open notepad"
  "List files in my Documents folder"
  "What processes are running?"
  "Create a new folder called Test on my desktop"
""")
    
    def _confirmation_handler(self, request: ToolRequest) -> bool:
        """Handle confirmation requests"""
        if self.auto_confirm:
            print(f"  [Auto-confirmed: {request.tool}]")
            return True
        
        print(f"\n⚠️  Confirmation Required")
        print(f"   Tool: {request.tool}")
        print(f"   Arguments: {request.arguments}")
        
        while True:
            response = input("   Proceed? (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
    
    def _on_thinking(self, thought: str):
        """Handle thinking events"""
        print(f"  💭 {thought}")
    
    def _on_tool_call(self, request: ToolRequest):
        """Handle tool call events"""
        print(f"  🔧 Executing: {request.tool}")
    
    def _on_tool_result(self, result: ToolResult):
        """Handle tool result events"""
        if result.status == ExecutionStatus.SUCCESS:
            print(f"  ✅ Success")
        else:
            print(f"  ❌ {result.status.value}: {result.error or ''}")
    
    def _initialize_agent(self):
        """Initialize the agent"""
        print("Initializing agent...")
        
        self.agent = create_agent(
            model=self.model,
            verbose=False,
            confirmation_handler=self._confirmation_handler,
        )
        
        self.agent.set_callbacks(
            on_thinking=self._on_thinking,
            on_tool_call=self._on_tool_call,
            on_tool_result=self._on_tool_result,
        )
        
        # Check if LLM is available
        if not self.agent.is_ready():
            print("\n❌ Error: Cannot connect to Ollama.")
            print("   Please make sure Ollama is running:")
            print("   1. Install Ollama from https://ollama.ai")
            print("   2. Run: ollama serve")
            print("   3. Pull the model: ollama pull llama4")
            return False
        
        print(f"✅ Agent ready with {len(self.agent.get_available_tools())} tools\n")
        return True
    
    def _process_command(self, command: str) -> bool:
        """Process a command, return False to exit"""
        cmd = command.strip().lower()
        
        if cmd in ['quit', 'exit', 'q']:
            print("\nGoodbye! 👋")
            return False
        
        elif cmd == 'help':
            self._print_help()
        
        elif cmd == 'reset':
            self.agent.reset_conversation()
            print("  Conversation reset.\n")
        
        elif cmd == 'tools':
            print("\n  Available Tools:")
            for tool_name in sorted(self.agent.get_available_tools()):
                print(f"    • {tool_name}")
            print()
        
        elif cmd == 'status':
            print(f"\n  Agent Status:")
            print(f"    Model: {self.model}")
            print(f"    LLM Ready: {self.agent.is_ready()}")
            print(f"    Tools: {len(self.agent.get_available_tools())}")
            print(f"    Auto-confirm: {self.auto_confirm}")
            print()
        
        elif cmd.startswith('autoconfirm'):
            parts = cmd.split()
            if len(parts) > 1:
                self.auto_confirm = parts[1] in ['on', 'true', '1']
            else:
                self.auto_confirm = not self.auto_confirm
            print(f"  Auto-confirm: {'ON' if self.auto_confirm else 'OFF'}\n")
        
        elif cmd:
            # Send to agent
            try:
                print()
                response = self.agent.process(command)
                print(f"\n🤖 {response}\n")
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
                logger.exception("Agent error")
        
        return True
    
    def run(self):
        """Run the CLI"""
        self._print_header()
        
        if not self._initialize_agent():
            return
        
        # Main loop
        while True:
            try:
                user_input = input("You: ").strip()
                if not self._process_command(user_input):
                    break
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit.")
            except EOFError:
                print("\nGoodbye! 👋")
                break


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Windows AI Agent - Offline Desktop Control"
    )
    parser.add_argument(
        "--model",
        default="llama4",
        help="Ollama model to use (default: llama4)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    cli = AgentCLI(model=args.model)
    cli.run()


if __name__ == "__main__":
    main()
