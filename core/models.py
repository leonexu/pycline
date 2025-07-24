"""
PyCline数据模型定义

对应Cline模块关系:
- TaskResult -> Cline的HistoryItem (src/shared/HistoryItem.ts) + Task执行结果
- TaskUpdate -> Cline的TaskState (src/core/task/TaskState.ts) 状态更新
- Context -> Cline的环境详情 (Task.getEnvironmentDetails())
- FileChange -> Cline的文件变更记录 (FileContextTracker.trackFileContext())
- ToolCall -> Cline的工具调用记录 (ToolExecutor.executeTool())
- ProjectInfo -> Cline的工作区信息 (WorkspaceTracker)
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCallStatus(str, Enum):
    """工具调用状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class TaskResult(BaseModel):
    """
    任务执行结果
    
    对应Cline的HistoryItem扩展:
    - task_id -> HistoryItem.id
    - description -> HistoryItem.task
    - status -> TaskState状态
    - start_time/end_time -> 时间戳记录
    - generated_code -> 生成的代码内容
    - files_created/modified -> 文件操作记录
    - tool_calls -> 工具调用历史
    - ai_messages -> 对话消息记录
    """
    task_id: str = Field(description="任务ID")
    description: str = Field(description="任务描述")
    status: TaskStatus = Field(description="任务状态")
    start_time: datetime = Field(description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    
    # 执行结果
    generated_code: Optional[str] = Field(None, description="生成的代码")
    files_created: List[str] = Field(default_factory=list, description="创建的文件列表")
    files_modified: List[str] = Field(default_factory=list, description="修改的文件列表")
    
    # 统计信息
    total_tokens: int = Field(0, description="总Token使用量")
    total_cost: float = Field(0.0, description="总成本")
    tool_calls_count: int = Field(0, description="工具调用次数")
    
    # 详细记录
    tool_calls: List["ToolCall"] = Field(default_factory=list, description="工具调用记录")
    ai_messages: List[Dict[str, Any]] = Field(default_factory=list, description="AI对话记录")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskUpdate(BaseModel):
    """
    任务状态更新
    
    对应Cline的TaskState更新机制:
    - task_id -> Task.taskId
    - status -> TaskState各种状态标志
    - current_step -> 当前执行步骤
    - progress -> 进度信息
    """
    task_id: str = Field(description="任务ID")
    status: TaskStatus = Field(description="任务状态")
    current_step: Optional[str] = Field(None, description="当前执行步骤")
    progress: float = Field(0.0, description="进度百分比 (0-100)")
    message: Optional[str] = Field(None, description="状态消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间")


class Context(BaseModel):
    """
    上下文信息
    
    对应Cline的环境详情:
    - working_directory -> Task.cwd
    - visible_files -> VSCode可见文件
    - open_tabs -> VSCode打开的标签页
    - terminal_info -> 终端状态信息
    - git_info -> Git仓库信息
    """
    working_directory: str = Field(description="工作目录")
    visible_files: List[str] = Field(default_factory=list, description="可见文件列表")
    open_tabs: List[str] = Field(default_factory=list, description="打开的标签页")
    terminal_info: Dict[str, Any] = Field(default_factory=dict, description="终端信息")
    git_info: Optional[Dict[str, Any]] = Field(None, description="Git信息")
    recently_modified: List[str] = Field(default_factory=list, description="最近修改的文件")
    current_time: datetime = Field(default_factory=datetime.now, description="当前时间")
    
    # 上下文窗口信息
    context_window_usage: Dict[str, int] = Field(default_factory=dict, description="上下文窗口使用情况")
    mode: str = Field("act", description="当前模式 (plan/act)")


class FileChange(BaseModel):
    """
    文件变更记录
    
    对应Cline的文件跟踪:
    - file_path -> FileContextTracker.trackFileContext()
    - operation -> 操作类型
    - content_before/after -> 变更内容
    - timestamp -> 变更时间
    """
    file_path: str = Field(description="文件路径")
    operation: str = Field(description="操作类型: create, modify, delete, read")
    content_before: Optional[str] = Field(None, description="变更前内容")
    content_after: Optional[str] = Field(None, description="变更后内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="变更时间")
    source: str = Field(description="变更来源: user, cline, system")
    
    # 差异信息
    diff: Optional[str] = Field(None, description="差异内容")
    lines_added: int = Field(0, description="新增行数")
    lines_removed: int = Field(0, description="删除行数")


class ToolCall(BaseModel):
    """
    工具调用记录
    
    对应Cline的工具执行:
    - tool_name -> ToolExecutor.executeTool()
    - parameters -> 工具参数
    - result -> 执行结果
    - status -> 执行状态
    """
    tool_name: str = Field(description="工具名称")
    parameters: Dict[str, Any] = Field(description="工具参数")
    status: ToolCallStatus = Field(description="调用状态")
    
    # 执行信息
    start_time: datetime = Field(default_factory=datetime.now, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_ms: Optional[int] = Field(None, description="执行时长(毫秒)")
    
    # 结果信息
    result: Optional[Union[str, Dict[str, Any]]] = Field(None, description="执行结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 审批信息
    requires_approval: bool = Field(False, description="是否需要审批")
    auto_approved: bool = Field(False, description="是否自动审批")
    user_feedback: Optional[str] = Field(None, description="用户反馈")


class ProjectInfo(BaseModel):
    """
    项目信息
    
    对应Cline的工作区信息:
    - project_path -> WorkspaceTracker工作区路径
    - file_structure -> 文件结构
    - git_info -> Git仓库信息
    - dependencies -> 项目依赖
    """
    project_path: str = Field(description="项目路径")
    project_name: str = Field(description="项目名称")
    
    # 文件结构
    file_structure: Dict[str, Any] = Field(default_factory=dict, description="文件结构")
    total_files: int = Field(0, description="文件总数")
    total_lines: int = Field(0, description="代码总行数")
    
    # 技术栈信息
    languages: List[str] = Field(default_factory=list, description="编程语言")
    frameworks: List[str] = Field(default_factory=list, description="使用的框架")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="项目依赖")
    
    # Git信息
    git_info: Optional[Dict[str, Any]] = Field(None, description="Git仓库信息")
    
    # 配置文件
    config_files: List[str] = Field(default_factory=list, description="配置文件列表")
    
    # 最后更新时间
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")


class ApiUsage(BaseModel):
    """
    API使用统计
    
    对应Cline的API使用记录:
    - provider -> API提供者
    - model -> 使用的模型
    - tokens_in/out -> Token使用量
    - cost -> 成本
    """
    provider: str = Field(description="API提供者")
    model: str = Field(description="使用的模型")
    
    # Token统计
    tokens_in: int = Field(0, description="输入Token数")
    tokens_out: int = Field(0, description="输出Token数")
    cache_reads: int = Field(0, description="缓存读取Token数")
    cache_writes: int = Field(0, description="缓存写入Token数")
    
    # 成本统计
    cost: float = Field(0.0, description="成本")
    
    # 时间信息
    timestamp: datetime = Field(default_factory=datetime.now, description="使用时间")
    duration_ms: Optional[int] = Field(None, description="请求时长(毫秒)")


class ConversationMessage(BaseModel):
    """
    对话消息
    
    对应Cline的消息系统:
    - role -> 消息角色 (user/assistant/system)
    - content -> 消息内容
    - message_type -> 消息类型
    - metadata -> 元数据
    """
    role: str = Field(description="消息角色: user, assistant, system")
    content: Union[str, List[Dict[str, Any]]] = Field(description="消息内容")
    message_type: Optional[str] = Field(None, description="消息类型")
    
    # 时间信息
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="消息元数据")
    
    # 工具相关
    tool_calls: List[ToolCall] = Field(default_factory=list, description="关联的工具调用")
    
    # 媒体内容
    images: List[str] = Field(default_factory=list, description="图片内容")
    files: List[str] = Field(default_factory=list, description="文件内容")


# 更新前向引用
TaskResult.model_rebuild()
