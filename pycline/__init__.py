"""
PyCline - Python implementation of Cline
AI-powered code generation and task automation
"""

__version__ = "0.1.0"
__author__ = "xling"
__email__ = "leonexu@qq.com"

# 导出主要的公共接口
from .task_manager import TaskManager, TaskMetadata
from .tool_executor import ToolExecutor
from .types import (
    WebviewMessage,
    ClineSay,
    ClineAsk,
    ToolUse,
    ChatSettings,
    HistoryItem
)

__all__ = [
    "TaskManager",
    "TaskMetadata",
    "ToolExecutor", 
    "WebviewMessage",
    "ClineSay",
    "ClineAsk",
    "ToolUse",
    "ChatSettings",
    "HistoryItem"
]
