"""
Windows AI Agent - Configuration Settings
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json
import os

@dataclass
class LLMConfig:
    """LLM Configuration"""
    provider: str = "ollama"
    model: str = "llama4"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    
@dataclass
class SecurityConfig:
    """Security Configuration"""
    # Permission tier: observer, operator, administrator, system
    default_permission_tier: str = "operator"
    
    # Protected paths that should never be modified
    protected_paths: List[str] = field(default_factory=lambda: [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\ProgramData\\Microsoft",
    ])
    
    # Paths that are allowed for full access
    allowed_paths: List[str] = field(default_factory=lambda: [
        os.path.expanduser("~"),
    ])
    
    # Tools that require confirmation
    tools_requiring_confirmation: List[str] = field(default_factory=lambda: [
        "file_delete",
        "file_write",
        "process_kill",
        "registry_write",
        "app_install",
    ])
    
    # Maximum files to delete without extra confirmation
    bulk_delete_threshold: int = 5
    
    # Enable execution sandbox
    sandbox_enabled: bool = True
    
    # Execution timeout (seconds)
    tool_timeout: int = 30

@dataclass
class UIConfig:
    """UI Configuration"""
    theme: str = "dark"
    window_width: int = 800
    window_height: int = 600
    system_tray: bool = True
    hotkey: str = "Win+Shift+A"
    voice_enabled: bool = False

@dataclass 
class MemoryConfig:
    """Memory/Storage Configuration"""
    database_path: str = "data/memory.db"
    vector_store_path: str = "data/vectors.faiss"
    max_conversation_history: int = 100
    embedding_model: str = "all-MiniLM-L6-v2"

@dataclass
class AgentConfig:
    """Main Agent Configuration"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    
    # Agent behavior
    max_planning_steps: int = 10
    max_retries: int = 3
    verbose: bool = True
    
    @classmethod
    def load(cls, path: str = "config/agent_config.json") -> "AgentConfig":
        """Load configuration from JSON file"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            return cls._from_dict(data)
        return cls()
    
    @classmethod
    def _from_dict(cls, data: dict) -> "AgentConfig":
        """Create config from dictionary"""
        return cls(
            llm=LLMConfig(**data.get('llm', {})),
            security=SecurityConfig(**data.get('security', {})),
            ui=UIConfig(**data.get('ui', {})),
            memory=MemoryConfig(**data.get('memory', {})),
            max_planning_steps=data.get('max_planning_steps', 10),
            max_retries=data.get('max_retries', 3),
            verbose=data.get('verbose', True),
        )
    
    def save(self, path: str = "config/agent_config.json"):
        """Save configuration to JSON file"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self._to_dict(), f, indent=2)
    
    def _to_dict(self) -> dict:
        """Convert config to dictionary"""
        return {
            'llm': self.llm.__dict__,
            'security': {
                **self.security.__dict__,
                'protected_paths': list(self.security.protected_paths),
                'allowed_paths': list(self.security.allowed_paths),
                'tools_requiring_confirmation': list(self.security.tools_requiring_confirmation),
            },
            'ui': self.ui.__dict__,
            'memory': self.memory.__dict__,
            'max_planning_steps': self.max_planning_steps,
            'max_retries': self.max_retries,
            'verbose': self.verbose,
        }


# Global config instance
_config: Optional[AgentConfig] = None

def get_config() -> AgentConfig:
    """Get global configuration"""
    global _config
    if _config is None:
        _config = AgentConfig.load()
    return _config

def set_config(config: AgentConfig):
    """Set global configuration"""
    global _config
    _config = config
