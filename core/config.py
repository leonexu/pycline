"""PyCline配置管理"""

from pydantic import BaseModel, Field
from typing import Optional, List


class AIConfig(BaseModel):
    """AI提供者配置"""
    provider: str = Field(description="AI提供者: openai, anthropic, local")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    model: str = Field("gpt-4", description="模型名称")
    max_tokens: int = Field(4096, description="最大Token数")
    temperature: float = Field(0.1, description="温度参数")
    timeout: int = Field(60, description="请求超时时间(秒)")


class SecurityConfig(BaseModel):
    """安全配置"""
    allowed_paths: List[str] = Field(default_factory=lambda: ["."], description="允许访问的路径")
    blocked_commands: List[str] = Field(
        default_factory=lambda: ["rm -rf", "format", "del", "sudo rm"],
        description="禁止的命令"
    )
    max_file_size: int = Field(10 * 1024 * 1024, description="最大文件大小(字节)")
    max_execution_time: int = Field(30, description="最大执行时间(秒)")
    enable_command_execution: bool = Field(True, description="是否允许命令执行")
    sandbox_mode: bool = Field(False, description="是否启用沙箱模式")


class ContextConfig(BaseModel):
    """上下文配置"""
    max_tokens: int = Field(8000, description="最大上下文Token数")
    auto_discover: bool = Field(True, description="是否自动发现相关文件")
    cache_enabled: bool = Field(True, description="是否启用缓存")
    max_files: int = Field(50, description="最大文件数量")
    priority_strategy: str = Field("balanced", description="优先级策略")


class LogConfig(BaseModel):
    """日志配置"""
    level: str = Field("INFO", description="日志级别")
    file_path: Optional[str] = Field(None, description="日志文件路径")
    max_size: str = Field("10MB", description="日志文件最大大小")
    backup_count: int = Field(5, description="日志文件备份数量")


class Config(BaseModel):
    """主配置类"""
    ai: AIConfig = Field(description="AI配置")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="安全配置")
    context: ContextConfig = Field(default_factory=ContextConfig, description="上下文配置")
    log: LogConfig = Field(default_factory=LogConfig, description="日志配置")
    
    workspace_path: str = Field(".", description="默认工作空间路径")
    enable_cache: bool = Field(True, description="是否启用缓存")
    cache_dir: str = Field(".pycline_cache", description="缓存目录")
    enable_tools: List[str] = Field(
        default_factory=lambda: ["file", "command", "search"],
        description="启用的工具列表"
    )
    
    class Config:
        extra = "allow"  # 允许额外字段
