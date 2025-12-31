"""
Windows AI Agent - Tool Server (MCP-Style Local Tool Runtime)
"""
import time
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import traceback

from core.types import (
    ToolSchema, ToolRequest, ToolResult, SideEffect,
    ExecutionStatus, RiskLevel, PermissionTier, ToolCategory, ToolParameter
)

logger = logging.getLogger(__name__)


# Type for tool handler functions
ToolHandler = Callable[[Dict[str, Any]], Any]


@dataclass
class RegisteredTool:
    """A registered tool with its schema and handler"""
    schema: ToolSchema
    handler: ToolHandler
    enabled: bool = True


class ToolServer:
    """
    Local Tool Server - MCP-style tool execution runtime
    
    Responsibilities:
    - Tool registration and schema management
    - Request validation
    - Permission checking
    - Sandboxed execution
    - Result formatting
    """
    
    def __init__(
        self,
        permission_tier: PermissionTier = PermissionTier.OPERATOR,
        timeout: int = 30,
        max_workers: int = 4,
    ):
        self._tools: Dict[str, RegisteredTool] = {}
        self._permission_tier = permission_tier
        self._timeout = timeout
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._confirmation_callback: Optional[Callable[[ToolRequest], bool]] = None
        self._execution_history: List[ToolResult] = []
        
    def register_tool(
        self,
        schema: ToolSchema,
        handler: ToolHandler,
    ):
        """Register a tool with its schema and handler"""
        self._tools[schema.name] = RegisteredTool(
            schema=schema,
            handler=handler,
            enabled=True,
        )
        logger.info(f"Registered tool: {schema.name}")
    
    def register_tools(self, tools: List[tuple]):
        """Register multiple tools: [(schema, handler), ...]"""
        for schema, handler in tools:
            self.register_tool(schema, handler)
    
    def set_confirmation_callback(self, callback: Callable[[ToolRequest], bool]):
        """Set callback for confirmation dialogs"""
        self._confirmation_callback = callback
    
    def get_tool_schemas(self) -> List[ToolSchema]:
        """Get all registered tool schemas"""
        return [t.schema for t in self._tools.values() if t.enabled]
    
    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Get schema for a specific tool"""
        tool = self._tools.get(name)
        return tool.schema if tool else None
    
    def validate_request(self, request: ToolRequest) -> tuple[bool, Optional[str]]:
        """Validate a tool request"""
        # Check if tool exists
        if request.tool not in self._tools:
            return False, f"Unknown tool: {request.tool}"
        
        tool = self._tools[request.tool]
        
        # Check if tool is enabled
        if not tool.enabled:
            return False, f"Tool is disabled: {request.tool}"
        
        # Check permission tier
        if tool.schema.permission_tier.value > self._permission_tier.value:
            return False, f"Insufficient permissions for tool: {request.tool}"
        
        # Validate required parameters
        schema = tool.schema
        for param in schema.parameters:
            if param.required and param.name not in request.arguments:
                if param.default is None:
                    return False, f"Missing required parameter: {param.name}"
        
        # Type validation (basic)
        for param in schema.parameters:
            if param.name in request.arguments:
                value = request.arguments[param.name]
                if not self._validate_type(value, param.type):
                    return False, f"Invalid type for {param.name}: expected {param.type}"
        
        return True, None
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Basic type validation"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        if expected_type not in type_map:
            return True  # Unknown type, allow
        
        return isinstance(value, type_map[expected_type])
    
    def _check_confirmation(self, request: ToolRequest) -> bool:
        """Check if confirmation is needed and get it"""
        tool = self._tools.get(request.tool)
        if not tool:
            return False
        
        # Check if confirmation is required
        if tool.schema.requires_confirmation and not request.confirmed:
            if self._confirmation_callback:
                return self._confirmation_callback(request)
            else:
                # No callback set, deny by default
                logger.warning(f"Confirmation required but no callback set for: {request.tool}")
                return False
        
        return True
    
    def execute(self, request: ToolRequest) -> ToolResult:
        """Execute a tool request"""
        start_time = time.time()
        
        # Validate request
        valid, error = self.validate_request(request)
        if not valid:
            return ToolResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                error=error,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        tool = self._tools[request.tool]
        
        # Check confirmation
        if tool.schema.requires_confirmation and not request.confirmed:
            return ToolResult(
                request_id=request.request_id,
                status=ExecutionStatus.CONFIRMATION_REQUIRED,
                result={"message": f"Action '{request.tool}' requires confirmation"},
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        # Execute in thread pool with timeout
        try:
            future = self._executor.submit(tool.handler, request.arguments)
            result = future.result(timeout=self._timeout)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Handle result
            if isinstance(result, dict):
                if "error" in result:
                    tool_result = ToolResult(
                        request_id=request.request_id,
                        status=ExecutionStatus.FAILED,
                        error=result["error"],
                        execution_time_ms=execution_time,
                    )
                else:
                    side_effects = []
                    if "side_effects" in result:
                        for se in result["side_effects"]:
                            side_effects.append(SideEffect(**se))
                    
                    tool_result = ToolResult(
                        request_id=request.request_id,
                        status=ExecutionStatus.SUCCESS,
                        result=result.get("result", result),
                        side_effects=side_effects,
                        warnings=result.get("warnings", []),
                        execution_time_ms=execution_time,
                    )
            else:
                tool_result = ToolResult(
                    request_id=request.request_id,
                    status=ExecutionStatus.SUCCESS,
                    result=result,
                    execution_time_ms=execution_time,
                )
            
            self._execution_history.append(tool_result)
            return tool_result
            
        except FutureTimeoutError:
            return ToolResult(
                request_id=request.request_id,
                status=ExecutionStatus.TIMEOUT,
                error=f"Tool execution timed out after {self._timeout}s",
                execution_time_ms=self._timeout * 1000,
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}\n{traceback.format_exc()}")
            return ToolResult(
                request_id=request.request_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def execute_batch(self, requests: List[ToolRequest]) -> List[ToolResult]:
        """Execute multiple tool requests"""
        results = []
        for request in requests:
            result = self.execute(request)
            results.append(result)
            
            # Stop on failure if it's a sequential batch
            if result.status == ExecutionStatus.FAILED:
                break
        
        return results
    
    def enable_tool(self, name: str):
        """Enable a tool"""
        if name in self._tools:
            self._tools[name].enabled = True
    
    def disable_tool(self, name: str):
        """Disable a tool"""
        if name in self._tools:
            self._tools[name].enabled = False
    
    def set_permission_tier(self, tier: PermissionTier):
        """Set the current permission tier"""
        self._permission_tier = tier
    
    def get_execution_history(self, limit: int = 100) -> List[ToolResult]:
        """Get recent execution history"""
        return self._execution_history[-limit:]
    
    def shutdown(self):
        """Shutdown the tool server"""
        self._executor.shutdown(wait=True)


def create_tool_schema(
    name: str,
    description: str,
    category: ToolCategory,
    parameters: List[Dict],
    risk_level: RiskLevel = RiskLevel.LOW,
    requires_confirmation: bool = False,
    permission_tier: PermissionTier = PermissionTier.OPERATOR,
    examples: List[Dict] = None,
) -> ToolSchema:
    """Helper to create tool schemas"""
    params = []
    for p in parameters:
        params.append(ToolParameter(
            name=p["name"],
            type=p.get("type", "string"),
            description=p.get("description", ""),
            required=p.get("required", True),
            default=p.get("default"),
            enum=p.get("enum"),
            examples=p.get("examples"),
        ))
    
    return ToolSchema(
        name=name,
        description=description,
        category=category,
        risk_level=risk_level,
        parameters=params,
        returns_description="",
        requires_confirmation=requires_confirmation,
        permission_tier=permission_tier,
        examples=examples or [],
    )
