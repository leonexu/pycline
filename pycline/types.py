"""
PyCline标准化数据类型定义
与Cline接口保持一致
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import time


class ClineSay(str, Enum):
    """Cline Say消息类型枚举"""
    TEXT = "text"
    TOOL = "tool"
    ERROR = "error"
    API_REQ_STARTED = "api_req_started"
    API_REQ_RETRIED = "api_req_retried"
    COMPLETION_RESULT = "completion_result"
    USER_FEEDBACK = "user_feedback"
    USER_FEEDBACK_DIFF = "user_feedback_diff"
    BROWSER_ACTION = "browser_action"
    BROWSER_ACTION_LAUNCH = "browser_action_launch"
    BROWSER_ACTION_RESULT = "browser_action_result"
    USE_MCP_SERVER = "use_mcp_server"
    MCP_SERVER_REQUEST_STARTED = "mcp_server_request_started"
    MCP_SERVER_RESPONSE = "mcp_server_response"
    MCP_NOTIFICATION = "mcp_notification"
    COMMAND = "command"
    CHECKPOINT_CREATED = "checkpoint_created"
    SHELL_INTEGRATION_WARNING = "shell_integration_warning"
    CLINEIGNORE_ERROR = "clineignore_error"
    DIFF_ERROR = "diff_error"
    REASONING = "reasoning"
    DELETED_API_REQS = "deleted_api_reqs"
    LOAD_MCP_DOCUMENTATION = "load_mcp_documentation"


class ClineAsk(str, Enum):
    """Cline Ask消息类型枚举"""
    TOOL = "tool"
    COMMAND = "command"
    COMPLETION_RESULT = "completion_result"
    FOLLOWUP = "followup"
    API_REQ_FAILED = "api_req_failed"
    RESUME_TASK = "resume_task"
    RESUME_COMPLETED_TASK = "resume_completed_task"
    MISTAKE_LIMIT_REACHED = "mistake_limit_reached"
    AUTO_APPROVAL_MAX_REQ_REACHED = "auto_approval_max_req_reached"
    BROWSER_ACTION_LAUNCH = "browser_action_launch"
    USE_MCP_SERVER = "use_mcp_server"
    NEW_TASK = "new_task"
    CONDENSE = "condense"
    REPORT_BUG = "report_bug"
    PLAN_MODE_RESPOND = "plan_mode_respond"


class ClineAskResponse(str, Enum):
    """Cline Ask响应类型枚举"""
    YES_BUTTON_CLICKED = "yesButtonClicked"
    NO_BUTTON_CLICKED = "noButtonClicked"
    MESSAGE_RESPONSE = "messageResponse"


@dataclass
class AskResponse:
    """Ask响应数据结构"""
    response: ClineAskResponse
    text: Optional[str] = None
    images: Optional[List[str]] = None
    files: Optional[List[str]] = None


@dataclass
class WebviewMessage:
    """Webview消息数据结构"""
    type: str
    text: Optional[str] = None
    images: Optional[List[str]] = None
    files: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ClineMessage:
    """Cline消息数据结构"""
    ts: int
    type: str  # "say" | "ask"
    say: Optional[ClineSay] = None
    ask: Optional[ClineAsk] = None
    text: Optional[str] = None
    images: Optional[List[str]] = None
    files: Optional[List[str]] = None
    partial: Optional[bool] = None
    
    # 额外字段
    metadata: Optional[Dict[str, Any]] = None
    conversation_history_index: Optional[int] = None
    conversation_history_deleted_range: Optional[tuple] = None
    last_checkpoint_hash: Optional[str] = None
    is_checkpoint_checked_out: Optional[bool] = None

    @classmethod
    def create_say(cls, say_type: ClineSay, text: Optional[str] = None, 
                   images: Optional[List[str]] = None, files: Optional[List[str]] = None,
                   partial: Optional[bool] = None) -> "ClineMessage":
        """创建Say类型消息"""
        return cls(
            ts=int(time.time() * 1000),
            type="say",
            say=say_type,
            text=text,
            images=images,
            files=files,
            partial=partial
        )
    
    @classmethod
    def create_ask(cls, ask_type: ClineAsk, text: Optional[str] = None,
                   partial: Optional[bool] = None) -> "ClineMessage":
        """创建Ask类型消息"""
        return cls(
            ts=int(time.time() * 1000),
            type="ask",
            ask=ask_type,
            text=text,
            partial=partial
        )


@dataclass
class ToolUse:
    """工具使用数据结构"""
    name: str
    params: Dict[str, Any]
    partial: Optional[bool] = None


class ToolResponse:
    """工具响应数据结构"""
    def __init__(self, content: Union[str, List[Dict[str, Any]]]):
        self.content = content
    
    def __str__(self) -> str:
        if isinstance(self.content, str):
            return self.content
        return str(self.content)


@dataclass
class ChatSettings:
    """聊天设置数据结构"""
    mode: str = "act"  # "plan" | "act"
    preferred_language: Optional[str] = None
    openai_reasoning_effort: Optional[str] = None


@dataclass
class HistoryItem:
    """历史项目数据结构"""
    id: str
    ts: int
    task: str
    tokens_in: int = 0
    tokens_out: int = 0
    total_cost: float = 0.0
    api_provider: Optional[str] = None
    api_model: Optional[str] = None
    is_favorite: Optional[bool] = None
    conversation_history_deleted_range: Optional[tuple] = None


@dataclass
class ContextMetadata:
    """上下文元数据"""
    truncated_conversation_history: List[Dict[str, Any]]
    conversation_history_deleted_range: Optional[tuple] = None
    updated_conversation_history_deleted_range: Optional[bool] = None


@dataclass
class ContextWindowInfo:
    """上下文窗口信息"""
    context_window: int
    max_allowed_size: int


# 工具相关类型
ToolUseName = str

# API相关类型
class ApiHandler:
    """API处理器接口"""
    def get_model(self) -> Dict[str, Any]:
        raise NotImplementedError
    
    def create_message(self, system_prompt: str, messages: List[Dict[str, Any]]) -> Any:
        raise NotImplementedError


# 消息内容类型
MessageContent = Union[str, List[Dict[str, Any]]]
MessageMetadata = List[List[str]]
