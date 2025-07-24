"""
PyCline工具执行器
与Cline的ToolExecutor保持一致的接口
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from .types import (
    ToolUse, ToolResponse, ClineSay, ClineAsk, AskResponse, 
    ClineAskResponse, ToolUseName
)


class ToolInterface(ABC):
    """工具接口基类"""
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any], partial: bool = False) -> ToolResponse:
        """执行工具"""
        pass
    
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass


class ReadFileTool(ToolInterface):
    """读取文件工具"""
    
    def __init__(self, working_directory: str):
        self.working_directory = working_directory
        os.makedirs(working_directory, exist_ok=True)
    
    async def execute(self, params: Dict[str, Any], partial: bool = False) -> ToolResponse:
        file_path = params.get("path")
        if not file_path:
            raise ValueError("Missing required parameter: path")
        
        # 解析相对路径
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.working_directory, file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return ToolResponse(content)
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "path" in params
    
    def get_description(self) -> str:
        return "Read the contents of a file"


class WriteToFileTool(ToolInterface):
    """写入文件工具"""
    
    def __init__(self, working_directory: str):
        self.working_directory = working_directory
    
    async def execute(self, params: Dict[str, Any], partial: bool = False) -> ToolResponse:
        file_path = params.get("path")
        content = params.get("content")
        
        if not file_path:
            raise ValueError("Missing required parameter: path")
        if content is None:
            raise ValueError("Missing required parameter: content")
        
        # 解析相对路径
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.working_directory, file_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return ToolResponse(f"File written successfully to {file_path}")
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "path" in params and "content" in params
    
    def get_description(self) -> str:
        return "Write content to a file"


class ReplaceInFileTool(ToolInterface):
    """文件内容替换工具"""
    
    def __init__(self, working_directory: str):
        self.working_directory = working_directory
    
    async def execute(self, params: Dict[str, Any], partial: bool = False) -> ToolResponse:
        file_path = params.get("path")
        diff = params.get("diff")
        
        if not file_path:
            raise ValueError("Missing required parameter: path")
        if not diff:
            raise ValueError("Missing required parameter: diff")
        
        # 解析相对路径
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.working_directory, file_path)
        
        # 读取原文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 解析diff并应用更改
        new_content = self._apply_diff(original_content, diff)
        
        # 写入新内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return ToolResponse(f"File {file_path} updated successfully")
    
    def _apply_diff(self, original_content: str, diff: str) -> str:
        """应用diff到原内容"""
        # 解析diff中的SEARCH/REPLACE块
        diff_blocks = self._parse_diff_blocks(diff)
        
        for search_text, replace_text in diff_blocks:
            if search_text in original_content:
                original_content = original_content.replace(search_text, replace_text, 1)
            else:
                raise ValueError(f"Search text not found in file: {search_text}")
        
        return original_content
    
    def _parse_diff_blocks(self, diff: str) -> List[tuple]:
        """解析diff中的SEARCH/REPLACE块"""
        blocks = []
        lines = diff.split('\n')
        
        i = 0
        while i < len(lines):
            if lines[i].strip() == "------- SEARCH":
                search_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() != "=======":
                    search_lines.append(lines[i])
                    i += 1
                
                if i < len(lines) and lines[i].strip() == "=======":
                    replace_lines = []
                    i += 1
                    while i < len(lines) and lines[i].strip() != "+++++++ REPLACE":
                        replace_lines.append(lines[i])
                        i += 1
                    
                    if i < len(lines) and lines[i].strip() == "+++++++ REPLACE":
                        search_text = '\n'.join(search_lines)
                        replace_text = '\n'.join(replace_lines)
                        blocks.append((search_text, replace_text))
            i += 1
        
        if not blocks:
            raise ValueError("No valid SEARCH/REPLACE blocks found in diff")
        
        return blocks
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "path" in params and "diff" in params
    
    def get_description(self) -> str:
        return "Replace content in a file using SEARCH/REPLACE blocks"


class ListFilesTool(ToolInterface):
    """列出文件工具"""
    
    def __init__(self, working_directory: str):
        self.working_directory = working_directory
    
    async def execute(self, params: Dict[str, Any], partial: bool = False) -> ToolResponse:
        dir_path = params.get("path", ".")
        recursive = params.get("recursive", "false").lower() == "true"
        
        # 解析相对路径
        if not os.path.isabs(dir_path):
            dir_path = os.path.join(self.working_directory, dir_path)
        
        if recursive:
            files = []
            for root, dirs, filenames in os.walk(dir_path):
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), dir_path)
                    files.append(rel_path)
            result = '\n'.join(sorted(files))
        else:
            files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
            dirs = [f for f in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, f))]
            result = '\n'.join(sorted(dirs + files))
        
        return ToolResponse(result)
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True  # path是可选的
    
    def get_description(self) -> str:
        return "List files and directories"


class ExecuteCommandTool(ToolInterface):
    """执行命令工具"""
    
    def __init__(self, working_directory: str):
        self.working_directory = working_directory
    
    async def execute(self, params: Dict[str, Any], partial: bool = False) -> ToolResponse:
        command = params.get("command")
        requires_approval = params.get("requires_approval", "true").lower() == "true"
        
        if not command:
            raise ValueError("Missing required parameter: command")
        
        # 在工作目录中执行命令
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=self.working_directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        output = ""
        if stdout:
            output += stdout.decode('utf-8')
        if stderr:
            output += stderr.decode('utf-8')
        
        result = f"Command executed with exit code {process.returncode}."
        if output:
            result += f"\nOutput:\n{output}"
        
        return ToolResponse(result)
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "command" in params and "requires_approval" in params
    
    def get_description(self) -> str:
        return "Execute a command in the terminal"


class ToolExecutor:
    """工具执行器 - 与Cline的ToolExecutor接口一致"""
    
    def __init__(self, working_directory: str, 
                 say_callback=None, ask_callback=None):
        self.working_directory = working_directory
        self.say_callback = say_callback
        self.ask_callback = ask_callback
        self.tools = self._register_tools()
        
        # 自动审批设置
        self.auto_approval_enabled = False
        self.auto_approve_safe_tools = True
        self.auto_approve_all_tools = False
    
    def _register_tools(self) -> Dict[str, ToolInterface]:
        """注册所有工具"""
        return {
            "read_file": ReadFileTool(self.working_directory),
            "write_to_file": WriteToFileTool(self.working_directory),
            "replace_in_file": ReplaceInFileTool(self.working_directory),
            "list_files": ListFilesTool(self.working_directory),
            "execute_command": ExecuteCommandTool(self.working_directory),
        }
    
    async def execute_tool(self, block: ToolUse) -> None:
        """执行工具 - 主要接口方法"""
        tool_name = block.name
        params = block.params
        partial = block.partial or False
        
        # 验证工具是否存在
        if tool_name not in self.tools:
            await self._handle_error(f"using tool {tool_name}", 
                                   Exception(f"Unknown tool: {tool_name}"), block)
            return
        
        tool = self.tools[tool_name]
        
        # 验证参数
        if not tool.validate_params(params):
            await self._handle_error(f"validating parameters for {tool_name}",
                                   Exception("Invalid parameters"), block)
            return
        
        # 检查是否需要用户审批
        if not partial and not self.should_auto_approve_tool(tool_name):
            approved = await self.ask_approval(ClineAsk.TOOL, block, 
                                             f"Execute {tool_name} with params: {params}")
            if not approved:
                return
        
        # 执行工具
        result = await tool.execute(params, partial)
        
        # 发送结果
        if self.say_callback:
            await self.say_callback(ClineSay.TOOL, str(result))
    
    def should_auto_approve_tool(self, tool_name: ToolUseName) -> bool:
        """检查工具是否应该自动审批"""
        if not self.auto_approval_enabled:
            return False
        
        # 安全工具列表
        safe_tools = ["read_file", "list_files"]
        
        if tool_name in safe_tools and self.auto_approve_safe_tools:
            return True
        
        return self.auto_approve_all_tools
    
    async def ask_approval(self, ask_type: ClineAsk, block: ToolUse, 
                          partial_message: str) -> bool:
        """请求用户审批"""
        if self.ask_callback:
            response = await self.ask_callback(ask_type, partial_message)
            return response.response == ClineAskResponse.YES_BUTTON_CLICKED
        
        # 如果没有回调，默认批准
        return True
    
    async def _handle_error(self, action: str, error: Exception, block: ToolUse) -> None:
        """处理错误"""
        error_message = f"Error {action}: {str(error)}"
        
        if self.say_callback:
            await self.say_callback(ClineSay.ERROR, error_message)
        
        print(f"ToolExecutor Error: {error_message}")
        # 直接抛出错误以便调试
        raise error
    
    def update_auto_approval_settings(self, enabled: bool, safe_tools: bool = True, 
                                    all_tools: bool = False) -> None:
        """更新自动审批设置"""
        self.auto_approval_enabled = enabled
        self.auto_approve_safe_tools = safe_tools
        self.auto_approve_all_tools = all_tools
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self.tools.keys())
    
    def get_tool_description(self, tool_name: str) -> str:
        """获取工具描述"""
        if tool_name in self.tools:
            return self.tools[tool_name].get_description()
        return f"Unknown tool: {tool_name}"
