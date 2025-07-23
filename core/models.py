"""PyCline数据模型定义"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileChange(BaseModel):
    """文件变更记录"""
    path: str = Field(description="文件路径")
    action: str = Field(description="操作类型: create, modify, delete")
    content: Optional[str] = Field(None, description="文件内容")
    diff: Optional[str] = Field(None, description="变更差异")


class ToolCall(BaseModel):
    """工具调用记录"""
    tool_name: str = Field(description="工具名称")
    parameters: Dict[str, Any] = Field(description="工具参数")
    result: Optional[str] = Field(None, description="执行结果")
    success: bool = Field(True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间(秒)")


class TaskResult(BaseModel):
    """任务执行结果"""
    task_id: str = Field(description="任务ID")
    description: str = Field(description="任务描述")
    status: TaskStatus = Field(description="任务状态")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    
    # 执行结果
    generated_code: Optional[str] = Field(None, description="生成的代码")
    files_created: List[str] = Field(default_factory=list, description="创建的文件")
    files_modified: List[str] = Field(default_factory=list, description="修改的文件")
    file_changes: List[FileChange] = Field(default_factory=list, description="文件变更详情")
    
    # 执行过程
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用记录")
    ai_messages: List[Dict[str, Any]] = Field(default_factory=list, description="AI对话记录")
    
    # 统计信息
    total_tokens: Optional[int] = Field(None, description="总Token使用量")
    execution_time: Optional[float] = Field(None, description="总执行时间")
    error: Optional[str] = Field(None, description="错误信息")


class TaskUpdate(BaseModel):
    """任务进度更新"""
    task_id: str = Field(description="任务ID")
    status: TaskStatus = Field(description="当前状态")
    progress: float = Field(description="进度百分比 0-100")
    current_step: str = Field(description="当前步骤描述")
    ai_thinking: Optional[str] = Field(None, description="AI思考过程")
    tool_call: Optional[ToolCall] = Field(None, description="当前工具调用")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class Context(BaseModel):
    """任务上下文"""
    task_description: str = Field(description="任务描述")
    workspace_path: str = Field(description="工作空间路径")
    files: List[Dict[str, Any]] = Field(default_factory=list, description="相关文件")
    project_info: Optional[Dict[str, Any]] = Field(None, description="项目信息")
    token_usage: int = Field(0, description="Token使用量")


class ProjectInfo(BaseModel):
    """项目信息"""
    path: str = Field(description="项目路径")
    name: str = Field(description="项目名称")
    type: str = Field(description="项目类型")
    structure: Dict[str, Any] = Field(description="项目结构")
    config_files: List[str] = Field(default_factory=list, description="配置文件")
    entry_points: List[str] = Field(default_factory=list, description="入口文件")
