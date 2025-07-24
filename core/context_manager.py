"""
PyCline上下文管理器
基于Cline的智能上下文管理机制实现，包括智能截断、内容去重和文件跟踪功能
"""

import json
import os
import time
from typing import Dict, List, Tuple, Optional, Set, Any, Union
from dataclasses import dataclass, asdict
from enum import IntEnum
import re
from pathlib import Path
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class EditType(IntEnum):
    """编辑类型枚举"""
    UNDEFINED = 0
    NO_FILE_READ = 1
    READ_FILE_TOOL = 2
    ALTER_FILE_TOOL = 3
    FILE_MENTION = 4

@dataclass
class ContextUpdate:
    """上下文更新记录"""
    timestamp: float
    update_type: str
    content: List[str]
    metadata: List[List[str]]

@dataclass
class FileMetadataEntry:
    """文件元数据条目"""
    path: str
    record_state: str  # "active" | "stale"
    record_source: str  # "read_tool" | "user_edited" | "cline_edited" | "file_mentioned"
    cline_read_date: Optional[float] = None
    cline_edit_date: Optional[float] = None
    user_edit_date: Optional[float] = None

@dataclass
class ContextWindowInfo:
    """上下文窗口信息"""
    context_window: int
    max_allowed_size: int

class ContextManager:
    """
    智能上下文管理器
    负责管理对话历史、文件内容去重和智能截断
    """
    
    def __init__(self, task_id: str, working_directory: str):
        self.task_id = task_id
        self.working_directory = working_directory
        
        # 上下文历史更新映射: {message_index: (edit_type, {block_index: [updates]})}
        self.context_history_updates: Dict[int, Tuple[int, Dict[int, List[ContextUpdate]]]] = {}
        
        # 文件跟踪
        self.file_context_tracker = FileContextTracker(task_id, working_directory)
        
        # 任务目录
        self.task_directory = os.path.join(working_directory, ".pycline", "tasks", task_id)
        os.makedirs(self.task_directory, exist_ok=True)
    
    async def initialize_context_history(self):
        """初始化上下文历史"""
        await self._load_context_history()
        await self.file_context_tracker.initialize()
    
    def get_context_window_info(self, model_name: str, context_window: Optional[int] = None) -> ContextWindowInfo:
        """
        获取上下文窗口信息
        根据不同模型动态计算上下文窗口大小和最大允许使用量
        """
        if context_window is None:
            context_window = 128_000  # 默认值
        
        # 特殊模型处理
        model_lower = model_name.lower()
        if "deepseek" in model_lower:
            context_window = 64_000
        elif "claude" in model_lower:
            context_window = 200_000
        elif "gpt-4" in model_lower:
            context_window = 128_000
        
        # 计算最大允许使用量（保留缓冲区）
        if context_window == 64_000:  # deepseek
            max_allowed_size = context_window - 27_000
        elif context_window == 128_000:  # 大多数模型
            max_allowed_size = context_window - 30_000
        elif context_window == 200_000:  # claude
            max_allowed_size = context_window - 40_000
        else:
            max_allowed_size = max(context_window - 40_000, int(context_window * 0.8))
        
        return ContextWindowInfo(context_window, max_allowed_size)
    
    async def get_optimized_context_messages(
        self,
        conversation_history: List[Dict[str, Any]],
        model_name: str,
        previous_token_usage: Optional[Dict[str, int]] = None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        获取优化后的上下文消息
        主要入口点，负责智能截断和内容优化
        """
        updated_conversation = False
        
        # 检查是否需要优化
        if previous_token_usage:
            total_tokens = sum(previous_token_usage.values())
            context_info = self.get_context_window_info(model_name)
            
            if total_tokens >= context_info.max_allowed_size:
                print(f"[ContextManager] 接近上下文窗口限制: {total_tokens}/{context_info.max_allowed_size}")
                
                # 1. 首先尝试内容优化
                optimization_result = await self._apply_context_optimizations(
                    conversation_history, 
                    timestamp=time.time()
                )
                
                need_truncate = True
                if optimization_result["updated"]:
                    # 计算优化效果
                    savings_percentage = optimization_result["savings_percentage"]
                    print(f"[ContextManager] 内容优化节省: {savings_percentage:.1%}")
                    
                    # 如果节省了30%以上的字符，就不需要截断
                    if savings_percentage >= 0.3:
                        need_truncate = False
                        print("[ContextManager] 内容优化效果良好，跳过截断")
                
                if need_truncate:
                    # 2. 执行智能截断
                    keep_strategy = "quarter" if total_tokens / 2 > context_info.max_allowed_size else "half"
                    conversation_history = self._apply_intelligent_truncation(
                        conversation_history, 
                        keep_strategy
                    )
                    updated_conversation = True
                    print(f"[ContextManager] 执行智能截断，策略: {keep_strategy}")
                
                # 保存上下文历史
                await self._save_context_history()
        
        # 应用所有上下文更新
        optimized_messages = self._apply_context_history_updates(conversation_history)
        
        return optimized_messages, updated_conversation
    
    async def _apply_context_optimizations(
        self, 
        conversation_history: List[Dict[str, Any]], 
        timestamp: float
    ) -> Dict[str, Any]:
        """应用上下文优化（主要是文件内容去重）"""
        
        # 查找重复的文件读取
        file_read_indices = self._find_duplicate_file_reads(conversation_history)
        
        # 应用文件读取优化
        updated_indices, total_chars, saved_chars = self._apply_file_read_optimizations(
            file_read_indices, 
            conversation_history, 
            timestamp
        )
        
        savings_percentage = saved_chars / total_chars if total_chars > 0 else 0
        
        return {
            "updated": len(updated_indices) > 0,
            "updated_indices": updated_indices,
            "savings_percentage": savings_percentage,
            "total_characters": total_chars,
            "saved_characters": saved_chars
        }
    
    def _find_duplicate_file_reads(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, List[Tuple[int, int, str, str]]]:
        """
        查找重复的文件读取操作
        返回: {file_path: [(message_index, edit_type, search_text, replace_text), ...]}
        """
        file_read_indices = {}
        
        for i, message in enumerate(conversation_history):
            if message.get("role") != "user":
                continue
                
            content = message.get("content", "")
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            
            # 检查工具调用
            tool_match = self._parse_tool_call(content)
            if tool_match:
                tool_name, file_path = tool_match
                if tool_name == "read_file":
                    self._handle_read_file_tool(i, file_path, file_read_indices)
                elif tool_name in ["write_to_file", "replace_in_file"]:
                    self._handle_file_change_tool(i, file_path, content, file_read_indices)
            
            # 检查文件提及
            self._handle_file_mentions(i, content, file_read_indices)
        
        return file_read_indices
    
    def _parse_tool_call(self, text: str) -> Optional[Tuple[str, str]]:
        """解析工具调用格式"""
        # 匹配 [tool_name for 'file_path'] Result: 格式
        match = re.search(r'^\[([^\s]+) for \'([^\']+)\'\] Result:', text, re.MULTILINE)
        if match:
            return match.group(1), match.group(2)
        return None
    
    def _handle_read_file_tool(self, message_index: int, file_path: str, file_read_indices: Dict):
        """处理read_file工具调用"""
        if file_path not in file_read_indices:
            file_read_indices[file_path] = []
        
        file_read_indices[file_path].append((
            message_index,
            EditType.READ_FILE_TOOL,
            "",  # search_text (空字符串表示整个消息)
            "[NOTE] This file content was previously shown and has been replaced with this notice to save context space."
        ))
    
    def _handle_file_change_tool(self, message_index: int, file_path: str, content: str, file_read_indices: Dict):
        """处理文件修改工具调用"""
        # 检查是否包含final_file_content
        pattern = r'<final_file_content path="[^"]*">[\s\S]*?</final_file_content>'
        if re.search(pattern, content):
            if file_path not in file_read_indices:
                file_read_indices[file_path] = []
            
            replacement = re.sub(
                pattern,
                lambda m: f'{m.group(0).split(">")[0]}> [NOTE] File content replaced to save context space. </final_file_content>',
                content
            )
            
            file_read_indices[file_path].append((
                message_index,
                EditType.ALTER_FILE_TOOL,
                "",
                replacement
            ))
    
    def _handle_file_mentions(self, message_index: int, content: str, file_read_indices: Dict):
        """处理文件内容提及"""
        # 匹配 <file_content path="...">...</file_content> 格式
        pattern = r'<file_content path="([^"]*)">[\s\S]*?</file_content>'
        matches = re.finditer(pattern, content)
        
        for match in matches:
            file_path = match.group(1)
            entire_match = match.group(0)
            
            if file_path not in file_read_indices:
                file_read_indices[file_path] = []
            
            replacement = f'<file_content path="{file_path}">[NOTE] File content replaced to save context space.</file_content>'
            
            file_read_indices[file_path].append((
                message_index,
                EditType.FILE_MENTION,
                entire_match,
                replacement
            ))
    
    def _apply_file_read_optimizations(
        self, 
        file_read_indices: Dict[str, List[Tuple[int, int, str, str]]], 
        conversation_history: List[Dict[str, Any]], 
        timestamp: float
    ) -> Tuple[Set[int], int, int]:
        """应用文件读取优化"""
        updated_indices = set()
        total_chars = 0
        saved_chars = 0
        
        for file_path, indices in file_read_indices.items():
            # 只有当同一文件有多次读取时才处理
            if len(indices) > 1:
                # 处理除最后一次外的所有读取（保留最新的）
                for i in range(len(indices) - 1):
                    message_index, edit_type, search_text, replacement_text = indices[i]
                    
                    # 计算节省的字符数
                    original_content = conversation_history[message_index].get("content", "")
                    if isinstance(original_content, list):
                        original_content = " ".join(str(item) for item in original_content)
                    
                    if search_text:
                        # 文件提及的情况
                        new_content = original_content.replace(search_text, replacement_text)
                        saved_chars += len(search_text) - len(replacement_text)
                    else:
                        # 整个消息替换的情况
                        saved_chars += len(original_content) - len(replacement_text)
                        new_content = replacement_text
                    
                    total_chars += len(original_content)
                    
                    # 更新上下文历史
                    self._update_context_history(message_index, edit_type, new_content, timestamp)
                    updated_indices.add(message_index)
        
        return updated_indices, total_chars, saved_chars
    
    def _apply_intelligent_truncation(
        self, 
        conversation_history: List[Dict[str, Any]], 
        keep_strategy: str = "half"
    ) -> List[Dict[str, Any]]:
        """
        应用智能截断
        保留第一对用户-助手消息，然后根据策略截断中间部分
        """
        if len(conversation_history) <= 2:
            return conversation_history
        
        # 保留第一对消息
        first_pair = conversation_history[:2]
        remaining_messages = conversation_history[2:]
        
        if keep_strategy == "none":
            messages_to_keep = 0
        elif keep_strategy == "lastTwo":
            messages_to_keep = min(2, len(remaining_messages))
        elif keep_strategy == "half":
            messages_to_keep = len(remaining_messages) // 2
            # 确保保持偶数个消息（用户-助手对）
            messages_to_keep = (messages_to_keep // 2) * 2
        elif keep_strategy == "quarter":
            messages_to_keep = len(remaining_messages) // 4
            messages_to_keep = (messages_to_keep // 2) * 2
        else:
            messages_to_keep = len(remaining_messages) // 2
        
        if messages_to_keep > 0:
            kept_messages = remaining_messages[-messages_to_keep:]
        else:
            kept_messages = []
        
        # 添加截断通知到第一个助手消息
        if len(first_pair) > 1:
            self._add_truncation_notice(1, time.time())
        
        return first_pair + kept_messages
    
    def _add_truncation_notice(self, message_index: int, timestamp: float):
        """添加截断通知"""
        if message_index not in self.context_history_updates:
            notice = "[NOTE] Some previous conversation history with the user has been removed to maintain optimal context window length. The initial user task and the most recent exchanges have been retained for continuity."
            
            self._update_context_history(
                message_index, 
                EditType.UNDEFINED, 
                notice, 
                timestamp
            )
    
    def _update_context_history(
        self, 
        message_index: int, 
        edit_type: int, 
        content: str, 
        timestamp: float
    ):
        """更新上下文历史"""
        if message_index not in self.context_history_updates:
            self.context_history_updates[message_index] = (edit_type, {})
        
        _, inner_map = self.context_history_updates[message_index]
        block_index = 0  # 简化处理，假设都是第一个块
        
        if block_index not in inner_map:
            inner_map[block_index] = []
        
        update = ContextUpdate(
            timestamp=timestamp,
            update_type="text",
            content=[content],
            metadata=[]
        )
        
        inner_map[block_index].append(update)
    
    def _apply_context_history_updates(self, conversation_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用所有上下文历史更新"""
        updated_history = []
        
        for i, message in enumerate(conversation_history):
            if i in self.context_history_updates:
                _, inner_map = self.context_history_updates[i]
                
                # 应用最新的更新
                updated_message = message.copy()
                for block_index, updates in inner_map.items():
                    if updates:
                        latest_update = updates[-1]
                        if latest_update.update_type == "text":
                            updated_message["content"] = latest_update.content[0]
                
                updated_history.append(updated_message)
            else:
                updated_history.append(message)
        
        return updated_history
    
    async def truncate_context_history(self, timestamp: float):
        """截断指定时间戳之后的上下文历史"""
        to_remove = []
        
        for message_index, (edit_type, inner_map) in self.context_history_updates.items():
            for block_index, updates in inner_map.items():
                # 移除时间戳之后的更新
                inner_map[block_index] = [
                    update for update in updates 
                    if update.timestamp <= timestamp
                ]
                
                # 如果没有更新了，标记为删除
                if not inner_map[block_index]:
                    to_remove.append((message_index, block_index))
        
        # 清理空的条目
        for message_index, block_index in to_remove:
            if message_index in self.context_history_updates:
                _, inner_map = self.context_history_updates[message_index]
                if block_index in inner_map:
                    del inner_map[block_index]
                
                # 如果inner_map为空，删除整个条目
                if not inner_map:
                    del self.context_history_updates[message_index]
        
        await self._save_context_history()
    
    async def _save_context_history(self):
        """保存上下文历史到磁盘"""
        # 序列化数据
        serialized_data = []
        for message_index, (edit_type, inner_map) in self.context_history_updates.items():
            inner_array = []
            for block_index, updates in inner_map.items():
                updates_data = [asdict(update) for update in updates]
                inner_array.append([block_index, updates_data])
            
            serialized_data.append([message_index, [edit_type, inner_array]])
        
        # 保存到文件
        context_file = os.path.join(self.task_directory, "context_history.json")
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(serialized_data, f, ensure_ascii=False, indent=2)
    
    async def _load_context_history(self):
        """从磁盘加载上下文历史"""
        context_file = os.path.join(self.task_directory, "context_history.json")
        if os.path.exists(context_file):
            with open(context_file, 'r', encoding='utf-8') as f:
                serialized_data = json.load(f)
            
            # 反序列化数据
            for message_index, (edit_type, inner_array) in serialized_data:
                inner_map = {}
                for block_index, updates_data in inner_array:
                    updates = [
                        ContextUpdate(**update_data) 
                        for update_data in updates_data
                    ]
                    inner_map[block_index] = updates
                
                self.context_history_updates[message_index] = (edit_type, inner_map)


class FileContextTracker:
    """
    文件上下文跟踪器
    监控文件变更，防止上下文过期
    """
    
    def __init__(self, task_id: str, working_directory: str):
        self.task_id = task_id
        self.working_directory = working_directory
        
        # 文件监控
        self.file_watchers = {}
        self.recently_modified_files = set()
        self.recently_edited_by_cline = set()
        
        # 文件元数据
        self.files_in_context: List[FileMetadataEntry] = []
        
        # 任务目录
        self.task_directory = os.path.join(working_directory, ".pycline", "tasks", task_id)
        os.makedirs(self.task_directory, exist_ok=True)
        
        # 文件监控器
        self.observer = Observer()
        self.observer.start()
    
    async def initialize(self):
        """初始化文件上下文跟踪器"""
        await self._load_file_metadata()
        
        # 为已跟踪的文件设置监听器
        for entry in self.files_in_context:
            if entry.record_state == "active":
                await self._setup_file_watcher(entry.path)
    
    async def track_file_context(
        self, 
        file_path: str, 
        operation: str  # "read_tool" | "user_edited" | "cline_edited" | "file_mentioned"
    ):
        """跟踪文件操作"""
        # 添加到元数据
        await self._add_file_to_tracker(file_path, operation)
        
        # 设置文件监听器
        await self._setup_file_watcher(file_path)
    
    async def _setup_file_watcher(self, file_path: str):
        """为文件设置监听器"""
        if file_path in self.file_watchers:
            return  # 已经设置过了
        
        full_path = os.path.join(self.working_directory, file_path)
        if not os.path.exists(full_path):
            return
        
        # 创建文件事件处理器
        event_handler = FileChangeHandler(self, file_path)
        
        # 监听文件所在目录
        watch_dir = os.path.dirname(full_path)
        if not watch_dir:
            watch_dir = self.working_directory
        
        watch = self.observer.schedule(event_handler, watch_dir, recursive=False)
        self.file_watchers[file_path] = watch
    
    async def _add_file_to_tracker(self, file_path: str, operation: str):
        """添加文件到跟踪器"""
        now = time.time()
        
        # 将现有条目标记为过期
        for entry in self.files_in_context:
            if entry.path == file_path and entry.record_state == "active":
                entry.record_state = "stale"
        
        # 获取最新的时间戳
        def get_latest_date(path: str, field: str) -> Optional[float]:
            relevant_entries = [
                entry for entry in self.files_in_context 
                if entry.path == path and getattr(entry, field) is not None
            ]
            if relevant_entries:
                return max(getattr(entry, field) for entry in relevant_entries)
            return None
        
        # 创建新条目
        new_entry = FileMetadataEntry(
            path=file_path,
            record_state="active",
            record_source=operation,
            cline_read_date=get_latest_date(file_path, "cline_read_date"),
            cline_edit_date=get_latest_date(file_path, "cline_edit_date"),
            user_edit_date=get_latest_date(file_path, "user_edit_date")
        )
        
        # 根据操作类型更新时间戳
        if operation == "user_edited":
            new_entry.user_edit_date = now
            self.recently_modified_files.add(file_path)
        elif operation == "cline_edited":
            new_entry.cline_read_date = now
            new_entry.cline_edit_date = now
        elif operation in ["read_tool", "file_mentioned"]:
            new_entry.cline_read_date = now
        
        self.files_in_context.append(new_entry)
        await self._save_file_metadata()
    
    def get_and_clear_recently_modified_files(self) -> List[str]:
        """获取并清空最近修改的文件列表"""
        files = list(self.recently_modified_files)
        self.recently_modified_files.clear()
        return files
    
    def mark_file_as_edited_by_cline(self, file_path: str):
        """标记文件为Cline编辑，防止误报"""
        self.recently_edited_by_cline.add(file_path)
    
    async def detect_files_edited_after_timestamp(self, timestamp: float) -> List[str]:
        """检测在指定时间戳之后编辑的文件"""
        edited_files = []
        
        for entry in self.files_in_context:
            cline_edited_after = entry.cline_edit_date and entry.cline_edit_date > timestamp
            user_edited_after = entry.user_edit_date and entry.user_edit_date > timestamp
            
            if cline_edited_after or user_edited_after:
                edited_files.append(entry.path)
        
        return list(set(edited_files))
    
    async def _save_file_metadata(self):
        """保存文件元数据"""
        metadata_file = os.path.join(self.task_directory, "file_metadata.json")
        data = {
            "files_in_context": [asdict(entry) for entry in self.files_in_context]
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def _load_file_metadata(self):
        """加载文件元数据"""
        metadata_file = os.path.join(self.task_directory, "file_metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.files_in_context = [
                FileMetadataEntry(**entry_data)
                for entry_data in data.get("files_in_context", [])
            ]
    
    def _sync_update_file_metadata(self, file_path: str, operation: str):
        """同步更新文件元数据（用于文件监控器）"""
        now = time.time()
        
        # 将现有条目标记为过期
        for entry in self.files_in_context:
            if entry.path == file_path and entry.record_state == "active":
                entry.record_state = "stale"
        
        # 获取最新的时间戳
        def get_latest_date(path: str, field: str) -> Optional[float]:
            relevant_entries = [
                entry for entry in self.files_in_context 
                if entry.path == path and getattr(entry, field) is not None
            ]
            if relevant_entries:
                return max(getattr(entry, field) for entry in relevant_entries)
            return None
        
        # 创建新条目
        new_entry = FileMetadataEntry(
            path=file_path,
            record_state="active",
            record_source=operation,
            cline_read_date=get_latest_date(file_path, "cline_read_date"),
            cline_edit_date=get_latest_date(file_path, "cline_edit_date"),
            user_edit_date=get_latest_date(file_path, "user_edit_date")
        )
        
        # 根据操作类型更新时间戳
        if operation == "user_edited":
            new_entry.user_edit_date = now
            self.recently_modified_files.add(file_path)
        elif operation == "cline_edited":
            new_entry.cline_read_date = now
            new_entry.cline_edit_date = now
        elif operation in ["read_tool", "file_mentioned"]:
            new_entry.cline_read_date = now
        
        self.files_in_context.append(new_entry)
        
        # 同步保存元数据（不依赖事件循环）
        self._sync_save_file_metadata()
    
    def _sync_save_file_metadata(self):
        """同步保存文件元数据"""
        metadata_file = os.path.join(self.task_directory, "file_metadata.json")
        data = {
            "files_in_context": [asdict(entry) for entry in self.files_in_context]
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def dispose(self):
        """清理资源"""
        self.observer.stop()
        self.observer.join()


class FileChangeHandler(FileSystemEventHandler):
    """文件变更事件处理器"""
    
    def __init__(self, tracker: FileContextTracker, file_path: str):
        self.tracker = tracker
        self.file_path = file_path
        self.full_path = os.path.join(tracker.working_directory, file_path)
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        if os.path.abspath(event.src_path) == os.path.abspath(self.full_path):
            if self.file_path in self.tracker.recently_edited_by_cline:
                # Cline的编辑，忽略
                self.tracker.recently_edited_by_cline.discard(self.file_path)
            else:
                # 用户编辑，需要通知
                self.tracker.recently_modified_files.add(self.file_path)
                # 同步更新文件元数据（避免异步调用）
                self.tracker._sync_update_file_metadata(self.file_path, "user_edited")


# 使用示例
async def example_usage():
    """使用示例"""
    # 创建上下文管理器
    context_manager = ContextManager("task_123", "/path/to/project")
    await context_manager.initialize_context_history()
    
    # 模拟对话历史
    conversation_history = [
        {"role": "user", "content": "请读取 main.py 文件"},
        {"role": "assistant", "content": "[read_file for 'main.py'] Result: def main(): pass"},
        {"role": "user", "content": "再次读取 main.py 文件"},
        {"role": "assistant", "content": "[read_file for 'main.py'] Result: def main(): pass"},
    ]
    
    # 模拟token使用情况
    token_usage = {"input_tokens": 50000, "output_tokens": 30000}
    
    # 获取优化后的上下文
    optimized_history, was_updated = await context_manager.get_optimized_context_messages(
        conversation_history,
        "claude-3-sonnet",
        token_usage
    )
    
    print(f"上下文是否更新: {was_updated}")
    print(f"优化后的对话历史长度: {len(optimized_history)}")
    
    # 文件跟踪示例
    await context_manager.file_context_tracker.track_file_context("main.py", "read_tool")
    
    # 获取最近修改的文件
    modified_files = context_manager.file_context_tracker.get_and_clear_recently_modified_files()
    print(f"最近修改的文件: {modified_files}")


if __name__ == "__main__":
    asyncio.run(example_usage())
