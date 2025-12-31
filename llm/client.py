"""
Windows AI Agent - LLM Client for Ollama
Updated with better parsing for LLaMA 4's response format
"""
import json
import re
import requests
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass
import logging

from core.types import ToolSchema, ToolRequest

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    tool_calls: List[ToolRequest]
    raw_response: Dict
    finish_reason: str = "stop"
    

class OllamaClient:
    """Client for Ollama API"""
    
    def __init__(
        self,
        model: str = "llama4",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
    def _build_system_prompt(self, tools: List[ToolSchema]) -> str:
        """Build system prompt with tool definitions"""
        tool_descriptions = []
        for tool in tools:
            schema = tool.to_llm_schema()
            tool_descriptions.append(json.dumps(schema, indent=2))
        
        tools_json = "\n".join(tool_descriptions)
        
        return f'''You are WindowsAI, an intelligent assistant that can control Windows computers.
You have access to tools that let you interact with the Windows operating system.

AVAILABLE TOOLS:
{tools_json}

CRITICAL RESPONSE FORMAT:
When you need to use a tool, respond with ONLY a JSON object like this (no other text before or after):
```json
{{
    "thought": "Brief explanation of what you're doing",
    "tool": "tool_name",
    "arguments": {{
        "param1": "value1"
    }}
}}
```

IMPORTANT RULES:
1. Only use ONE tool at a time - wait for the result before using another tool
2. For multi-step tasks, do them one step at a time
3. Always put your JSON in a ```json code block
4. Do NOT use <|python_start|> or <|python_end|> tags
5. When you don't need a tool, just respond with normal text
6. For destructive actions (delete, kill), confirm with user first

Example - Opening an app:
```json
{{
    "thought": "Opening Notepad for the user",
    "tool": "app_open",
    "arguments": {{
        "identifier": "notepad"
    }}
}}
```

Example - Typing text:
```json
{{
    "thought": "Typing the requested text",
    "tool": "keyboard_type",
    "arguments": {{
        "text": "Hello World"
    }}
}}
```
'''

    def _parse_tool_call(self, content: str) -> Optional[ToolRequest]:
        """Extract tool call from LLM response"""
        
        # Try multiple patterns to extract JSON
        json_patterns = [
            # LLaMA 4 specific: <|python_start|> ... <|python_end|>
            r'<\|python_start\|>\s*(.*?)\s*<\|python_end\|>',
            # Markdown code block with json
            r'```json\s*(.*?)\s*```',
            # Markdown code block generic
            r'```\s*(.*?)\s*```',
            # Raw JSON object with tool key
            r'(\{[^{}]*"tool"\s*:\s*"[^"]+?"[^{}]*\})',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Try to parse each match
                json_candidates = []
                
                # The match might contain multiple JSON objects
                # Try to find individual JSON objects
                brace_count = 0
                current_json = ""
                for char in match:
                    if char == '{':
                        brace_count += 1
                    if brace_count > 0:
                        current_json += char
                    if char == '}':
                        brace_count -= 1
                        if brace_count == 0 and current_json:
                            json_candidates.append(current_json)
                            current_json = ""
                
                # If no candidates found, try the whole match
                if not json_candidates:
                    json_candidates = [match.strip()]
                
                # Try to parse each candidate
                for json_str in json_candidates:
                    try:
                        if not json_str.strip().startswith('{'):
                            continue
                        
                        data = json.loads(json_str)
                        
                        if "tool" in data:
                            logger.info(f"Parsed tool call: {data['tool']}")
                            return ToolRequest(
                                tool=data["tool"],
                                arguments=data.get("arguments", {}),
                            )
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON parse failed: {e}")
                        continue
        
        # Last resort: try to find any JSON-like structure with "tool"
        try:
            # Find anything that looks like {"tool": "..."}
            tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', content)
            if tool_match:
                tool_name = tool_match.group(1)
                
                # Try to find arguments
                args = {}
                args_match = re.search(r'"arguments"\s*:\s*(\{[^}]+\})', content)
                if args_match:
                    try:
                        args = json.loads(args_match.group(1))
                    except:
                        pass
                
                logger.info(f"Extracted tool call via regex: {tool_name}")
                return ToolRequest(tool=tool_name, arguments=args)
        except Exception as e:
            logger.debug(f"Regex extraction failed: {e}")
        
        return None
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[ToolSchema]] = None,
        stream: bool = False,
    ) -> LLMResponse:
        """Send chat request to Ollama"""
        
        # Build messages with system prompt
        formatted_messages = []
        
        if tools:
            system_prompt = self._build_system_prompt(tools)
            formatted_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        formatted_messages.extend(messages)
        
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
                stream=stream,
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream(response)
            else:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                logger.debug(f"Raw LLM response: {content[:500]}...")
                
                # Try to parse tool call
                tool_calls = []
                tool_call = self._parse_tool_call(content)
                if tool_call:
                    tool_calls.append(tool_call)
                
                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    raw_response=data,
                    finish_reason=data.get("done_reason", "stop"),
                )
                
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise TimeoutError("LLM request timed out")
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama")
            raise ConnectionError("Could not connect to Ollama. Is it running?")
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise
    
    def _handle_stream(self, response) -> Generator[str, None, LLMResponse]:
        """Handle streaming response"""
        full_content = ""
        raw_response = {}
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "message" in data:
                        chunk = data["message"].get("content", "")
                        full_content += chunk
                        yield chunk
                    
                    if data.get("done"):
                        raw_response = data
                        break
                except json.JSONDecodeError:
                    continue
        
        # Parse tool calls from complete response
        tool_calls = []
        tool_call = self._parse_tool_call(full_content)
        if tool_call:
            tool_calls.append(tool_call)
        
        return LLMResponse(
            content=full_content,
            tool_calls=tool_calls,
            raw_response=raw_response,
        )
    
    def generate(self, prompt: str, stream: bool = False) -> str:
        """Simple text generation without chat format"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", "")
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """List available models"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except:
            return []


class LLMManager:
    """Manager for LLM operations"""
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.client = OllamaClient(
            model=config.get("model", "llama4"),
            base_url=config.get("base_url", "http://localhost:11434"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 4096),
            timeout=config.get("timeout", 120),
        )
        self._tools: List[ToolSchema] = []
    
    def register_tools(self, tools: List[ToolSchema]):
        """Register tools for the LLM to use"""
        self._tools = tools
    
    def chat(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Send chat with registered tools"""
        return self.client.chat(messages, tools=self._tools)
    
    def is_ready(self) -> bool:
        """Check if LLM is ready"""
        return self.client.is_available()
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return self.client.list_models()
