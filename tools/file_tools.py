"""文件操作工具"""

import os
from typing import Dict, Any
from langchain_core.tools import StructuredTool
from .base import Tool


class FileReadTool(Tool):
    """文件读取工具"""
    
    def __init__(self):
        super().__init__("read_file", "读取文件内容")
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要读取的文件路径"
                }
            },
            "required": ["file_path"]
        }
    
    def execute(self, file_path: str) -> str:
        """读取文件内容"""
        if not os.path.exists(file_path):
            return f"错误：文件 {file_path} 不存在"
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return f"文件 {file_path} 的内容：\n```\n{content}\n```"


class FileWriteTool(Tool):
    """文件写入工具"""
    
    def __init__(self):
        super().__init__("write_file", "写入文件内容")
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要写入的文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容"
                }
            },
            "required": ["file_path", "content"]
        }
    
    def execute(self, file_path: str, content: str) -> str:
        """写入文件内容"""
        # 创建目录（如果不存在）
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"成功写入文件 {file_path}"


class ListDirectoryTool(Tool):
    """目录列表工具"""
    
    def __init__(self):
        super().__init__("list_directory", "列出目录内容")
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "要列出的目录路径"
                }
            },
            "required": ["directory_path"]
        }
    
    def execute(self, directory_path: str) -> str:
        """列出目录内容"""
        if not os.path.exists(directory_path):
            return f"错误：目录 {directory_path} 不存在"
        
        if not os.path.isdir(directory_path):
            return f"错误：{directory_path} 不是一个目录"
        
        items = []
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path):
                items.append(f"📁 {item}/")
            else:
                size = os.path.getsize(item_path)
                items.append(f"📄 {item} ({size} bytes)")
        
        if not items:
            return f"目录 {directory_path} 为空"
        
        return f"目录 {directory_path} 的内容：\n" + "\n".join(items)
