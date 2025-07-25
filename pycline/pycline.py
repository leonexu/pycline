"""PyCline主类 - 核心功能入口"""

import uuid
from datetime import datetime
from typing import List, Optional

from .config import Config
from .models import TaskResult, TaskStatus, ToolCall, FileChange
from .context_manager import ContextManager
from .tool_executor import ToolExecutor
from .repo_analyzer import RepoAnalyzer
from ..tools.file_tools import FileReadTool, FileWriteTool, ListDirectoryTool
from ..tools.command_tools import CommandExecuteTool
from ..providers.langgraph_provider import LangGraphProvider


class PyCline:
    """PyCline主类，提供统一的编程接口"""
    
    def __init__(self, config: Config):
        self.config = config
        self.context_manager = ContextManager(config.context)
        self.tool_executor = ToolExecutor(config.security)
        self.ai_provider = LangGraphProvider(config.ai)
        self.task_history: List[TaskResult] = []
        
        # 代码库分析器（延迟初始化）
        self.repo_analyzer = None
        
        # 注册内置工具
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        if "file" in self.config.enable_tools:
            self.tool_executor.register_tool(FileReadTool())
            self.tool_executor.register_tool(FileWriteTool())
            self.tool_executor.register_tool(ListDirectoryTool())
        
        if "command" in self.config.enable_tools:
            self.tool_executor.register_tool(CommandExecuteTool())
    
    def execute_task(self, 
                    task_description: str,
                    workspace_path: Optional[str] = None,
                    context_files: Optional[List[str]] = None,
                    **kwargs) -> TaskResult:
        """执行编程任务"""
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # 使用默认工作空间路径
        if workspace_path is None:
            workspace_path = self.config.workspace_path
        
        # 创建任务结果对象
        task_result = TaskResult(
            task_id=task_id,
            description=task_description,
            status=TaskStatus.RUNNING,
            start_time=start_time
        )
        
        # 1. 构建增强上下文
        context = self.context_manager.build_enhanced_context(
            task_description, workspace_path, context_files, **kwargs
        )
        
        # 2. 格式化上下文为字符串
        context_str = self._format_enhanced_context_for_ai(context)
        
        # 3. 获取可用工具
        available_tools = self.tool_executor.get_available_tools()
        
        # 4. 使用AI Agent执行任务
        ai_result = self.ai_provider.execute_task(context_str, task_description, available_tools)
        
        # 5. 处理AI响应和工具调用
        ai_response = ai_result.get("content", "")
        tool_calls = []
        
        # 从Agent的完整消息历史中提取实际的工具调用
        full_messages = ai_result.get("full_messages", [])
        for message in full_messages:
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call_data in message.tool_calls:
                    tool_name = tool_call_data['name']
                    tool_args = tool_call_data.get('args', {})
                    
                    # 实际执行工具获取结果
                    actual_tool_call = self.tool_executor.execute_tool(tool_name, tool_args)
                    tool_calls.append(actual_tool_call)
                    
                    # 记录文件变更
                    if tool_name == "write_file" and actual_tool_call.success:
                        file_path = tool_args.get("file_path", "")
                        if file_path:
                            task_result.files_created.append(file_path)
                            task_result.file_changes.append(FileChange(
                                path=file_path,
                                action="create",
                                content=tool_args.get("content", "")
                            ))
                    elif tool_name == "read_file":
                        # 记录读取的文件
                        file_path = tool_args.get("file_path", "")
                        if file_path and file_path not in task_result.files_modified:
                            task_result.files_modified.append(file_path)
        
        # 6. 更新任务结果
        task_result.status = TaskStatus.COMPLETED
        task_result.end_time = datetime.now()
        task_result.execution_time = (task_result.end_time - task_result.start_time).total_seconds()
        task_result.tool_calls = tool_calls
        task_result.ai_messages = [{"role": "assistant", "content": ai_response}]
        task_result.total_tokens = context.token_usage
        task_result.generated_code = self._extract_generated_code(tool_calls)
        
        # 添加到历史记录
        self.task_history.append(task_result)
        
        return task_result
    
    def _format_context_for_ai(self, context) -> str:
        """将上下文格式化为AI可理解的字符串"""
        context_str = f"项目路径: {context.workspace_path}\n"
        context_str += f"任务描述: {context.task_description}\n\n"
        
        if context.project_info:
            project_info = context.project_info
            context_str += f"项目类型: {project_info['type']}\n"
            context_str += f"项目名称: {project_info['name']}\n"
            context_str += f"文件总数: {project_info['structure']['total_files']}\n\n"
        
        context_str += "相关文件:\n"
        for file_info in context.files:
            context_str += f"\n--- {file_info['path']} ---\n"
            context_str += file_info['content']
            context_str += "\n"
        
        return context_str
    
    def _extract_generated_code(self, tool_calls: List[ToolCall]) -> Optional[str]:
        """从工具调用中提取生成的代码"""
        for tool_call in tool_calls:
            if tool_call.tool_name == "write_file" and tool_call.success:
                return tool_call.parameters.get("content", "")
        return None
    
    def register_tool(self, tool) -> None:
        """注册自定义工具"""
        self.tool_executor.register_tool(tool)
    
    def get_task_history(self) -> List[TaskResult]:
        """获取任务历史"""
        return self.task_history.copy()
    
    def clear_cache(self) -> None:
        """清理缓存"""
        # TODO: 实现缓存清理逻辑
        pass
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.tool_executor.get_available_tools()]
