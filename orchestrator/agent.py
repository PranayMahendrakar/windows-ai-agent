"""
Windows AI Agent - Orchestrator
Main agent logic: intent parsing, planning, and execution coordination
"""
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

from core.types import (
    Message, Conversation, Plan, ToolRequest, ToolResult,
    ExecutionStatus, AgentState
)
from tools.server import ToolServer
from tools.registry import get_tool_server
from llm.client import LLMManager, LLMResponse

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent Orchestrator
    
    Coordinates between:
    - User input
    - LLM reasoning
    - Tool execution
    - Result presentation
    """
    
    def __init__(
        self,
        llm_config: Dict = None,
        tool_server: ToolServer = None,
        max_iterations: int = 10,
        verbose: bool = True,
    ):
        self.llm = LLMManager(llm_config or {})
        self.tool_server = tool_server or get_tool_server()
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # State
        self.state = AgentState()
        self.conversation = Conversation()
        
        # Callbacks
        self._on_thinking: Optional[Callable[[str], None]] = None
        self._on_tool_call: Optional[Callable[[ToolRequest], None]] = None
        self._on_tool_result: Optional[Callable[[ToolResult], None]] = None
        self._on_response: Optional[Callable[[str], None]] = None
        self._confirmation_handler: Optional[Callable[[ToolRequest], bool]] = None
        
        # Register tool schemas with LLM
        self.llm.register_tools(self.tool_server.get_tool_schemas())
        
        # Set confirmation callback on tool server
        self.tool_server.set_confirmation_callback(self._handle_confirmation)
    
    def set_callbacks(
        self,
        on_thinking: Callable[[str], None] = None,
        on_tool_call: Callable[[ToolRequest], None] = None,
        on_tool_result: Callable[[ToolResult], None] = None,
        on_response: Callable[[str], None] = None,
        confirmation_handler: Callable[[ToolRequest], bool] = None,
    ):
        """Set event callbacks"""
        self._on_thinking = on_thinking
        self._on_tool_call = on_tool_call
        self._on_tool_result = on_tool_result
        self._on_response = on_response
        self._confirmation_handler = confirmation_handler
    
    def _handle_confirmation(self, request: ToolRequest) -> bool:
        """Handle confirmation requests"""
        if self._confirmation_handler:
            return self._confirmation_handler(request)
        # Default: deny if no handler
        return False
    
    def _emit_thinking(self, thought: str):
        """Emit thinking event"""
        if self._on_thinking:
            self._on_thinking(thought)
        if self.verbose:
            logger.info(f"🤔 Thinking: {thought}")
    
    def _emit_tool_call(self, request: ToolRequest):
        """Emit tool call event"""
        if self._on_tool_call:
            self._on_tool_call(request)
        if self.verbose:
            logger.info(f"🔧 Tool call: {request.tool}({request.arguments})")
    
    def _emit_tool_result(self, result: ToolResult):
        """Emit tool result event"""
        if self._on_tool_result:
            self._on_tool_result(result)
        if self.verbose:
            status = "✅" if result.status == ExecutionStatus.SUCCESS else "❌"
            logger.info(f"{status} Result: {result.status.value}")
    
    def _emit_response(self, response: str):
        """Emit response event"""
        if self._on_response:
            self._on_response(response)
    
    def _format_tool_result_for_llm(self, result: ToolResult) -> str:
        """Format tool result for LLM context"""
        if result.status == ExecutionStatus.SUCCESS:
            # Truncate large results
            result_str = json.dumps(result.result, indent=2)
            if len(result_str) > 1000:
                result_str = result_str[:1000] + "... (truncated)"
            return f"Tool '{result.request_id}' executed successfully.\nResult: {result_str}"
        elif result.status == ExecutionStatus.CONFIRMATION_REQUIRED:
            return "Tool requires confirmation from user. Please ask the user if they want to proceed."
        elif result.status == ExecutionStatus.CANCELLED:
            return "User cancelled this operation."
        else:
            return f"Tool failed with error: {result.error}"
    
    def _clean_response(self, content: str) -> str:
        """Clean up LLM response - remove tool JSON and formatting artifacts"""
        import re
        
        # Remove <|python_start|> ... <|python_end|> blocks
        content = re.sub(r'<\|python_start\|>.*?<\|python_end\|>', '', content, flags=re.DOTALL)
        
        # Remove ```json ... ``` blocks
        content = re.sub(r'```json\s*\{[^`]*\}\s*```', '', content, flags=re.DOTALL)
        content = re.sub(r'```\s*\{[^`]*\}\s*```', '', content, flags=re.DOTALL)
        
        # Remove standalone JSON objects with "tool" key
        content = re.sub(r'\{[^{}]*"tool"[^{}]*\}', '', content)
        
        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        return content
    
    async def process_async(self, user_input: str) -> str:
        """Process user input asynchronously (for UI integration)"""
        return self.process(user_input)
    
    def process(self, user_input: str) -> str:
        """
        Process user input and return response
        
        This is the main entry point for the agent.
        It runs a loop: LLM -> Tool -> LLM -> Tool -> ... until done
        """
        # Add user message to conversation
        user_message = Message(role="user", content=user_input)
        self.conversation.add_message(user_message)
        
        # Build initial messages
        messages = []
        for msg in self.conversation.messages[-20:]:  # Last 20 messages
            messages.append({"role": msg.role, "content": msg.content})
        
        # Agent loop
        iterations = 0
        final_response = ""
        
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                llm_response = self.llm.chat(messages)
            except Exception as e:
                logger.error(f"LLM error: {e}")
                final_response = f"I encountered an error communicating with the AI model: {str(e)}"
                break
            
            content = llm_response.content
            
            # Check for tool calls
            if llm_response.tool_calls:
                tool_request = llm_response.tool_calls[0]
                
                # Extract thought if present
                thought = f"Using tool: {tool_request.tool}"
                self._emit_thinking(thought)
                self._emit_tool_call(tool_request)
                
                # Execute tool
                result = self.tool_server.execute(tool_request)
                self._emit_tool_result(result)
                
                # Handle confirmation required
                if result.status == ExecutionStatus.CONFIRMATION_REQUIRED:
                    if self._confirmation_handler:
                        confirmed = self._confirmation_handler(tool_request)
                        if confirmed:
                            tool_request.confirmed = True
                            result = self.tool_server.execute(tool_request)
                            self._emit_tool_result(result)
                        else:
                            result = ToolResult(
                                request_id=tool_request.request_id,
                                status=ExecutionStatus.CANCELLED,
                                error="User cancelled the operation",
                            )
                
                # Add assistant message (with tool call)
                messages.append({
                    "role": "assistant",
                    "content": content
                })
                
                # Add tool result
                tool_result_text = self._format_tool_result_for_llm(result)
                messages.append({
                    "role": "user",  # Tool results go as user messages
                    "content": f"[Tool Result]\n{tool_result_text}\n\nPlease continue with the task or provide a summary if complete."
                })
                
                # Store in conversation
                tool_message = Message(
                    role="assistant",
                    content=content,
                    tool_calls=[tool_request],
                )
                self.conversation.add_message(tool_message)
                
                result_message = Message(
                    role="tool",
                    content=tool_result_text,
                    tool_results=[result],
                )
                self.conversation.add_message(result_message)
                
                # Continue loop to let LLM decide next action
                continue
                
            else:
                # No tool call - this is the final response
                final_response = self._clean_response(content)
                
                # If response is empty, generate a summary
                if not final_response or len(final_response) < 5:
                    final_response = "Done!"
                
                break
        
        # Add final response to conversation
        if final_response:
            assistant_message = Message(role="assistant", content=final_response)
            self.conversation.add_message(assistant_message)
            self._emit_response(final_response)
        
        return final_response
    
    def reset_conversation(self):
        """Start a new conversation"""
        self.conversation = Conversation()
        self.state = AgentState()
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation.get_history_for_llm()
    
    def is_ready(self) -> bool:
        """Check if the agent is ready"""
        return self.llm.is_ready()
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return [t.name for t in self.tool_server.get_tool_schemas()]


class SimpleAgent:
    """
    Simplified agent interface for quick usage
    """
    
    def __init__(self, model: str = "llama4"):
        self.orchestrator = AgentOrchestrator(
            llm_config={"model": model},
            verbose=True,
        )
    
    def chat(self, message: str) -> str:
        """Send a message and get a response"""
        return self.orchestrator.process(message)
    
    def reset(self):
        """Reset the conversation"""
        self.orchestrator.reset_conversation()
    
    def is_ready(self) -> bool:
        """Check if ready"""
        return self.orchestrator.is_ready()


def create_agent(
    model: str = "llama4",
    verbose: bool = True,
    confirmation_handler: Callable[[ToolRequest], bool] = None,
) -> AgentOrchestrator:
    """Factory function to create a configured agent"""
    agent = AgentOrchestrator(
        llm_config={"model": model},
        verbose=verbose,
    )
    
    if confirmation_handler:
        agent.set_callbacks(confirmation_handler=confirmation_handler)
    
    return agent
