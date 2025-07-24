"""
PyCline任务管理器
集成上下文管理和Plan模式功能

对应Cline模块关系:
- TaskManager -> Cline的Controller + TaskManager组合
- TaskMetadata -> Cline的HistoryItem + TaskState部分功能
- create_task() -> Cline的Controller.initTask()
- process_user_input() -> Cline的Task.startTask()
- switch_mode() -> Cline的ChatSettings模式切换
- get_optimized_context() -> Cline的ContextManager.buildContext()
"""

import asyncio
import json
import os
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .context_manager import ContextManager
from .plan_mode import PlanModeManager
from .types import (
    ClineSay, ClineAsk, AskResponse, ClineAskResponse, WebviewMessage,
    ClineMessage, ChatSettings, HistoryItem, ToolUse
)
from .tool_executor import ToolExecutor
from tools.advanced_tools import AdvancedToolManager


@dataclass
class TaskMetadata:
    """任务元数据"""
    task_id: str
    title: str
    description: str
    created_at: float
    updated_at: float
    status: str  # "active" | "completed" | "paused" | "failed"
    mode: str  # "plan" | "act"
    model_name: str
    total_tokens: int = 0
    total_cost: float = 0.0
    conversation_length: int = 0


class TaskManager:
    """
    PyCline任务管理器
    负责任务的创建、管理和执行，集成上下文管理和Plan模式
    """
    
    def __init__(self, working_directory: str = "."):
        self.working_directory = os.path.abspath(working_directory)
        self.tasks_directory = os.path.join(self.working_directory, ".pycline", "tasks")
        os.makedirs(self.tasks_directory, exist_ok=True)
        
        # 当前活跃任务
        self.current_task: Optional[TaskMetadata] = None
        self.context_manager: Optional[ContextManager] = None
        self.plan_mode_manager: Optional[PlanModeManager] = None
        self.tool_manager = AdvancedToolManager()
        
        # 对话历史
        self.conversation_history: List[Dict[str, Any]] = []
        
        # 任务历史
        self.task_history: List[TaskMetadata] = []
        self._load_task_history()
    
    async def _create_task_internal(
        self, 
        title: str, 
        description: str, 
        mode: str = "act",
        model_name: str = "claude-3-sonnet"
    ) -> str:
        """
        内部创建任务方法
        """
        task_id = str(uuid.uuid4())
        now = time.time()
        
        # 创建任务元数据
        task_metadata = TaskMetadata(
            task_id=task_id,
            title=title,
            description=description,
            created_at=now,
            updated_at=now,
            status="active",
            mode=mode,
            model_name=model_name
        )
        
        # 设置为当前任务
        self.current_task = task_metadata
        
        # 初始化上下文管理器
        self.context_manager = ContextManager(task_id, self.working_directory)
        await self.context_manager.initialize_context_history()
        
        # 初始化Plan模式管理器
        from providers.langgraph_provider import LangGraphProvider
        from core.config import AIConfig
        
        # 创建AI配置
        ai_config = AIConfig(
            provider="deepseek",
            model=model_name,
            temperature=0.7,
            max_tokens=4000
        )
        
        # 创建AI提供者
        ai_provider = LangGraphProvider(ai_config)
        self.plan_mode_manager = PlanModeManager(ai_provider)
        
        # 清空对话历史
        self.conversation_history = []
        
        # 添加初始消息
        await self.add_message("user", description)
        
        # 保存任务
        await self._save_task_metadata(task_metadata)
        self.task_history.append(task_metadata)
        await self._save_task_history()
        
        print(f"[TaskManager] 创建任务: {title} (ID: {task_id}, 模式: {mode})")
        return task_id
    
    async def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功恢复
        """
        # 查找任务
        task_metadata = None
        for task in self.task_history:
            if task.task_id == task_id:
                task_metadata = task
                break
        
        if not task_metadata:
            print(f"[TaskManager] 任务不存在: {task_id}")
            return False
        
        # 加载任务数据
        task_data = await self._load_task_data(task_id)
        if not task_data:
            print(f"[TaskManager] 无法加载任务数据: {task_id}")
            return False
        
        # 设置为当前任务
        self.current_task = task_metadata
        self.conversation_history = task_data.get("conversation_history", [])
        
        # 初始化上下文管理器
        self.context_manager = ContextManager(task_id, self.working_directory)
        await self.context_manager.initialize_context_history()
        
        # 初始化Plan模式管理器
        from providers.langgraph_provider import LangGraphProvider
        from core.config import AIConfig
        
        # 创建AI配置
        ai_config = AIConfig(
            provider="deepseek",
            model=task_metadata.model_name,
            temperature=0.7,
            max_tokens=4000
        )
        
        # 创建AI提供者
        ai_provider = LangGraphProvider(ai_config)
        self.plan_mode_manager = PlanModeManager(ai_provider)
        
        # 更新任务状态
        task_metadata.status = "active"
        task_metadata.updated_at = time.time()
        await self._save_task_metadata(task_metadata)
        
        print(f"[TaskManager] 恢复任务: {task_metadata.title} (ID: {task_id})")
        return True
    
    async def switch_mode(self, mode: str) -> bool:
        """
        切换任务模式
        
        Args:
            mode: 目标模式 ("plan" | "act")
            
        Returns:
            是否成功切换
        """
        if not self.current_task:
            print("[TaskManager] 没有活跃任务")
            return False
        
        if self.current_task.mode == mode:
            print(f"[TaskManager] 已经是 {mode} 模式")
            return True
        
        # 更新任务模式
        self.current_task.mode = mode
        self.current_task.updated_at = time.time()
        
        # 保存任务
        await self._save_task_metadata(self.current_task)
        
        # 添加模式切换消息
        await self.add_message(
            "system", 
            f"[MODE_SWITCH] 切换到 {mode.upper()} 模式"
        )
        
        print(f"[TaskManager] 切换到 {mode.upper()} 模式")
        return True
    
    async def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        添加消息到对话历史
        
        Args:
            role: 消息角色 ("user" | "assistant" | "system")
            content: 消息内容
            metadata: 额外元数据
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(message)
        
        # 更新任务统计
        if self.current_task:
            self.current_task.conversation_length = len(self.conversation_history)
            self.current_task.updated_at = time.time()
        
        # 文件跟踪
        if self.context_manager and role == "assistant":
            await self._track_file_operations(content)
    
    async def get_optimized_context(
        self, 
        token_usage: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        获取优化后的上下文
        
        Args:
            token_usage: 上次请求的token使用情况
            
        Returns:
            (优化后的对话历史, 是否进行了优化)
        """
        if not self.context_manager or not self.current_task:
            return self.conversation_history, False
        
        return await self.context_manager.get_optimized_context_messages(
            self.conversation_history,
            self.current_task.model_name,
            token_usage
        )
    
    async def process_user_input(self, user_input: str) -> str:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI响应
        """
        if not self.current_task:
            return "错误: 没有活跃任务。请先创建或恢复任务。"
        
        # 添加用户消息
        await self.add_message("user", user_input)
        
        # 根据模式处理
        if self.current_task.mode == "plan":
            response = await self._process_plan_mode(user_input)
        else:
            response = await self._process_act_mode(user_input)
        
        # 添加AI响应
        await self.add_message("assistant", response)
        
        # 保存任务数据
        await self._save_current_task_data()
        
        return response
    
    async def _process_plan_mode(self, user_input: str) -> str:
        """处理Plan模式输入"""
        if not self.plan_mode_manager:
            return "错误: Plan模式管理器未初始化"
        
        # 获取优化后的上下文
        context, _ = await self.get_optimized_context()
        
        # 使用Plan模式处理
        # 创建执行计划
        plan = self.plan_mode_manager.create_plan(user_input, self.working_directory)
        
        # 获取计划摘要
        plan_summary = self.plan_mode_manager.get_plan_summary(plan)
        
        response = f"""
🎯 Plan模式分析完成

{plan_summary}

💡 建议：
1. 按照上述顺序执行子任务
2. 每完成一个子任务后进行验证
3. 如需调整计划，可以切换到Act模式进行具体实施

是否需要开始执行此计划？请切换到Act模式开始实施。
"""
        
        return response
    
    async def _process_act_mode(self, user_input: str) -> str:
        """处理Act模式输入"""
        # 获取优化后的上下文
        context, was_optimized = await self.get_optimized_context()
        
        if was_optimized:
            print("[TaskManager] 上下文已优化")
        
        # 检查是否需要使用工具
        if self._should_use_tools(user_input):
            # 使用工具处理
            tool_response = await self.tool_manager.process_request(
                user_input, 
                context,
                self.working_directory
            )
            return tool_response
        else:
            # 直接AI对话
            return await self._get_ai_response(context)
    
    def _should_use_tools(self, user_input: str) -> bool:
        """判断是否需要使用工具"""
        tool_keywords = [
            "读取", "写入", "创建", "删除", "修改", "执行", "运行",
            "read", "write", "create", "delete", "modify", "execute", "run",
            "文件", "目录", "代码", "脚本", "命令"
        ]
        
        return any(keyword in user_input.lower() for keyword in tool_keywords)
    
    async def _get_ai_response(self, context: List[Dict[str, Any]]) -> str:
        """获取AI响应（模拟）"""
        # 这里应该调用实际的AI API
        # 目前返回模拟响应
        return f"我理解您的请求。当前模式: {self.current_task.mode.upper()}。上下文长度: {len(context)}条消息。"
    
    async def _track_file_operations(self, content: str):
        """跟踪文件操作"""
        if not self.context_manager:
            return
        
        # 检查文件读取操作
        import re
        
        # 匹配文件路径
        file_patterns = [
            r'\[read_file for \'([^\']+)\'\]',
            r'\[write_to_file for \'([^\']+)\'\]',
            r'\[replace_in_file for \'([^\']+)\'\]',
            r'<file_content path="([^"]*)">'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            for file_path in matches:
                operation = "read_tool" if "read_file" in pattern else "cline_edited"
                await self.context_manager.file_context_tracker.track_file_context(
                    file_path, 
                    operation
                )
    
    async def get_task_status(self) -> Dict[str, Any]:
        """获取当前任务状态"""
        if not self.current_task:
            return {"status": "no_active_task"}
        
        # 获取最近修改的文件
        recently_modified = []
        if self.context_manager:
            recently_modified = self.context_manager.file_context_tracker.get_and_clear_recently_modified_files()
        
        return {
            "task_id": self.current_task.task_id,
            "title": self.current_task.title,
            "status": self.current_task.status,
            "mode": self.current_task.mode,
            "model_name": self.current_task.model_name,
            "conversation_length": len(self.conversation_history),
            "total_tokens": self.current_task.total_tokens,
            "total_cost": self.current_task.total_cost,
            "created_at": datetime.fromtimestamp(self.current_task.created_at).isoformat(),
            "updated_at": datetime.fromtimestamp(self.current_task.updated_at).isoformat(),
            "recently_modified_files": recently_modified
        }
    
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        return [
            {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status,
                "mode": task.mode,
                "created_at": datetime.fromtimestamp(task.created_at).isoformat(),
                "updated_at": datetime.fromtimestamp(task.updated_at).isoformat(),
                "conversation_length": task.conversation_length
            }
            for task in self.task_history
        ]
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        # 从历史中移除
        self.task_history = [task for task in self.task_history if task.task_id != task_id]
        
        # 删除任务文件
        task_dir = os.path.join(self.tasks_directory, task_id)
        if os.path.exists(task_dir):
            import shutil
            shutil.rmtree(task_dir)
        
        # 如果是当前任务，清空
        if self.current_task and self.current_task.task_id == task_id:
            self.current_task = None
            self.conversation_history = []
            if self.context_manager:
                self.context_manager.file_context_tracker.dispose()
                self.context_manager = None
        
        await self._save_task_history()
        print(f"[TaskManager] 删除任务: {task_id}")
        return True
    
    async def _save_task_metadata(self, task: TaskMetadata):
        """保存任务元数据"""
        task_dir = os.path.join(self.tasks_directory, task.task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        metadata_file = os.path.join(task_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(task), f, ensure_ascii=False, indent=2)
    
    async def _save_current_task_data(self):
        """保存当前任务数据"""
        if not self.current_task:
            return
        
        task_dir = os.path.join(self.tasks_directory, self.current_task.task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # 保存对话历史
        conversation_file = os.path.join(task_dir, "conversation.json")
        with open(conversation_file, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        
        # 更新元数据
        await self._save_task_metadata(self.current_task)
    
    async def _load_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载任务数据"""
        task_dir = os.path.join(self.tasks_directory, task_id)
        if not os.path.exists(task_dir):
            return None
        
        data = {}
        
        # 加载对话历史
        conversation_file = os.path.join(task_dir, "conversation.json")
        if os.path.exists(conversation_file):
            with open(conversation_file, 'r', encoding='utf-8') as f:
                data["conversation_history"] = json.load(f)
        
        return data
    
    def _load_task_history(self):
        """加载任务历史"""
        history_file = os.path.join(self.tasks_directory, "task_history.json")
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                self.task_history = [
                    TaskMetadata(**task_data) 
                    for task_data in history_data
                ]
    
    async def _save_task_history(self):
        """保存任务历史"""
        history_file = os.path.join(self.tasks_directory, "task_history.json")
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(task) for task in self.task_history], 
                f, 
                ensure_ascii=False, 
                indent=2
            )
    
    async def cleanup(self):
        """清理资源"""
        if self.context_manager:
            self.context_manager.file_context_tracker.dispose()
        
        print("[TaskManager] 资源清理完成")
    
    # ========== Cline标准化接口 ==========
    # 以下方法与Cline的Controller + Task接口保持一致
    
    async def init_task(self, task: Optional[str] = None, images: Optional[List[str]] = None,
                       files: Optional[List[str]] = None, history_item: Optional[HistoryItem] = None) -> str:
        """
        初始化任务 - 对应Cline的Controller.initTask()
        """
        if history_item:
            # 从历史恢复任务
            success = await self.resume_task(history_item.id)
            if success:
                return history_item.id
            else:
                raise ValueError(f"Failed to resume task: {history_item.id}")
        elif task or images or files:
            # 创建新任务
            task_text = task or "New task"
            return await self._create_task_internal(
                title="User Task",
                description=task_text,
                mode="act"
            )
        else:
            raise ValueError("Either history_item or task/images/files must be provided")
    
    async def handle_message(self, message: WebviewMessage) -> None:
        """
        处理消息 - 对应Cline的Controller.handleWebviewMessage()
        """
        message_type = message.type
        
        if message_type == "user_input":
            await self.process_user_input(message.text or "")
        elif message_type == "mode_switch":
            await self.switch_mode(message.text or "act")
        else:
            print(f"[TaskManager] Unknown message type: {message_type}")
    
    async def get_current_mode(self) -> str:
        """获取当前模式 - 对应Cline的Controller.getCurrentMode()"""
        if self.current_task:
            return self.current_task.mode
        return "act"
    
    async def toggle_plan_act_mode(self, chat_settings: ChatSettings, 
                                  chat_content: Optional[Dict] = None) -> bool:
        """
        切换Plan/Act模式 - 对应Cline的Controller.togglePlanActModeWithChatSettings()
        """
        return await self.switch_mode(chat_settings.mode)
    
    async def say(self, message_type: ClineSay, text: Optional[str] = None,
                 images: Optional[List[str]] = None, files: Optional[List[str]] = None,
                 partial: Optional[bool] = None) -> None:
        """
        发送Say消息 - 对应Cline的Task.say()
        """
        # 转换为内部消息格式
        role = "assistant" if message_type in [ClineSay.TEXT, ClineSay.TOOL] else "system"
        content = text or f"[{message_type}]"
        
        await self.add_message(role, content, {
            "message_type": message_type,
            "images": images,
            "files": files,
            "partial": partial
        })
        
        print(f"[SAY {message_type}] {text}")
    
    async def ask(self, message_type: ClineAsk, text: Optional[str] = None,
                 partial: Optional[bool] = None) -> AskResponse:
        """
        发送Ask消息 - 对应Cline的Task.ask()
        """
        # 添加询问消息
        await self.add_message("system", f"[ASK {message_type}] {text}", {
            "message_type": message_type,
            "partial": partial
        })
        
        print(f"[ASK {message_type}] {text}")
        
        # 简化的用户交互 - 在实际应用中应该等待用户响应
        # 这里默认返回批准
        return AskResponse(
            response=ClineAskResponse.YES_BUTTON_CLICKED,
            text=None,
            images=None,
            files=None
        )
    
    def get_cline_messages(self) -> List[ClineMessage]:
        """
        获取Cline消息列表 - 转换内部消息格式
        """
        cline_messages = []
        for msg in self.conversation_history:
            # 转换为ClineMessage格式
            ts = int(msg.get("timestamp", time.time()) * 1000)
            role = msg.get("role", "user")
            content = msg.get("content", "")
            metadata = msg.get("metadata", {})
            
            if role == "user":
                cline_msg = ClineMessage.create_ask(ClineAsk.FOLLOWUP, content)
            else:
                message_type = metadata.get("message_type", ClineSay.TEXT)
                cline_msg = ClineMessage.create_say(message_type, content)
            
            cline_msg.ts = ts
            cline_messages.append(cline_msg)
        
        return cline_messages
    
    def get_api_conversation_history(self) -> List[Dict[str, Any]]:
        """
        获取API对话历史 - 对应Cline的消息格式
        """
        api_history = []
        for msg in self.conversation_history:
            if msg.get("role") in ["user", "assistant"]:
                api_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        return api_history
    
    async def get_new_context_messages_and_metadata(
        self, 
        api_conversation_history: List[Dict[str, Any]],
        cline_messages: List[ClineMessage],
        api_handler: Optional[Any],
        conversation_history_deleted_range: Optional[Tuple[int, int]],
        previous_api_req_index: int,
        task_dir: str
    ) -> Any:
        """
        获取新的上下文消息和元数据 - 对应Cline的ContextManager.getNewContextMessagesAndMetadata()
        """
        if self.context_manager:
            return await self.context_manager.get_new_context_messages_and_metadata(
                api_conversation_history,
                cline_messages,
                api_handler,
                conversation_history_deleted_range,
                previous_api_req_index,
                task_dir
            )
        
        # 返回默认结果
        from .types import ContextMetadata
        return ContextMetadata(
            truncated_conversation_history=api_conversation_history,
            conversation_history_deleted_range=conversation_history_deleted_range
        )
    
    async def execute_tool(self, tool_use: ToolUse) -> None:
        """
        执行工具 - 对应Cline的ToolExecutor.executeTool()
        """
        # 初始化工具执行器（如果还没有）
        if not hasattr(self, 'tool_executor'):
            self.tool_executor = ToolExecutor(
                working_directory=self.working_directory,
                say_callback=self.say,
                ask_callback=self.ask
            )
        
        await self.tool_executor.execute_tool(tool_use)
    
    async def clear_task(self) -> None:
        """清理当前任务"""
        if self.current_task:
            self.current_task = None
            self.conversation_history = []
            if self.context_manager:
                self.context_manager.file_context_tracker.dispose()
                self.context_manager = None
            print("[TaskManager] 任务已清理")
