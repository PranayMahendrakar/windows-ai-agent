"""
Windows AI Agent - Core Types and Base Classes
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from datetime import datetime
import uuid
import json


class ToolCategory(Enum):
    """Tool categories"""
    FILE_SYSTEM = "file_system"
    APPLICATION = "application"
    INPUT = "input"
    UI_AUTOMATION = "ui_automation"
    SYSTEM = "system"
    CLIPBOARD = "clipboard"
    NOTIFICATION = "notification"
    DATA_EXTRACTION = "data_extraction"
    SCHEDULING = "scheduling"
    SECURITY = "security"


class RiskLevel(Enum):
    """Risk level for tools"""
    LOW = "low"           # Read-only operations
    MEDIUM = "medium"     # Reversible modifications
    HIGH = "high"         # Potentially destructive
    CRITICAL = "critical" # System-level changes


class PermissionTier(Enum):
    """Permission tiers"""
    OBSERVER = "observer"         # Read-only
    OPERATOR = "operator"         # Standard operations
    ADMINISTRATOR = "administrator"  # Elevated operations
    SYSTEM = "system"             # Full system access


class ExecutionStatus(Enum):
    """Status of tool execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    CONFIRMATION_REQUIRED = "confirmation_required"


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: str  # string, integer, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    examples: Optional[List[Any]] = None


@dataclass
class ToolSchema:
    """Schema definition for a tool"""
    name: str
    description: str
    category: ToolCategory
    risk_level: RiskLevel
    parameters: List[ToolParameter]
    returns_description: str
    requires_confirmation: bool = False
    permission_tier: PermissionTier = PermissionTier.OPERATOR
    examples: List[Dict] = field(default_factory=list)
    
    def to_llm_schema(self) -> Dict:
        """Convert to schema format for LLM"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.examples:
                prop["examples"] = param.examples
            if param.default is not None:
                prop["default"] = param.default
                
            properties[param.name] = prop
            
            if param.required and param.default is None:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }


@dataclass
class ToolRequest:
    """A request to execute a tool"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    conversation_id: Optional[str] = None
    step_number: int = 0
    requires_confirmation: bool = False
    confirmed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "tool": self.tool,
            "arguments": self.arguments,
            "timestamp": self.timestamp.isoformat(),
            "conversation_id": self.conversation_id,
            "step_number": self.step_number,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ToolRequest":
        return cls(
            request_id=data.get("request_id", str(uuid.uuid4())),
            tool=data.get("tool", ""),
            arguments=data.get("arguments", {}),
            conversation_id=data.get("conversation_id"),
            step_number=data.get("step_number", 0),
        )


@dataclass
class SideEffect:
    """A side effect from tool execution (for rollback)"""
    type: str  # file_created, file_modified, file_deleted, process_started, etc.
    path: Optional[str] = None
    data: Optional[Any] = None
    reversible: bool = True
    rollback_action: Optional[Dict] = None


@dataclass
class ToolResult:
    """Result of tool execution"""
    request_id: str
    status: ExecutionStatus
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    side_effects: List[SideEffect] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "side_effects": [
                {"type": se.type, "path": se.path, "reversible": se.reversible}
                for se in self.side_effects
            ],
            "warnings": self.warnings,
        }


@dataclass
class Message:
    """A conversation message"""
    role: str  # user, assistant, system, tool
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[ToolRequest] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_results": [tr.to_dict() for tr in self.tool_results],
        }


@dataclass
class Conversation:
    """A conversation with the agent"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: Message):
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_history_for_llm(self, max_messages: int = 20) -> List[Dict]:
        """Get conversation history formatted for LLM"""
        history = []
        for msg in self.messages[-max_messages:]:
            entry = {"role": msg.role, "content": msg.content}
            history.append(entry)
        return history


@dataclass
class Plan:
    """A multi-step execution plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    steps: List[ToolRequest] = field(default_factory=list)
    current_step: int = 0
    status: ExecutionStatus = ExecutionStatus.PENDING
    results: List[ToolResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def is_complete(self) -> bool:
        return self.current_step >= len(self.steps)
    
    def get_current_step(self) -> Optional[ToolRequest]:
        if self.is_complete():
            return None
        return self.steps[self.current_step]
    
    def advance(self, result: ToolResult):
        self.results.append(result)
        self.current_step += 1


@dataclass
class AgentState:
    """Current state of the agent"""
    conversation: Optional[Conversation] = None
    current_plan: Optional[Plan] = None
    is_executing: bool = False
    last_error: Optional[str] = None
    system_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "conversation_id": self.conversation.id if self.conversation else None,
            "has_plan": self.current_plan is not None,
            "is_executing": self.is_executing,
            "last_error": self.last_error,
        }
