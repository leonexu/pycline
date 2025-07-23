"""命令执行工具"""

import subprocess
from typing import Dict, Any
from .base import Tool


class CommandExecuteTool(Tool):
    """命令执行工具"""
    
    def __init__(self):
        super().__init__("execute_command", "执行系统命令")
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的命令"
                },
                "working_directory": {
                    "type": "string",
                    "description": "工作目录",
                    "default": "."
                }
            },
            "required": ["command"]
        }
    
    def execute(self, command: str, working_directory: str = ".") -> str:
        """执行系统命令"""
        # 安全检查 - 阻止危险命令
        dangerous_commands = ["rm -rf", "format", "del", "sudo rm", "dd if="]
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return f"错误：拒绝执行危险命令: {command}"
        
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            cwd=working_directory,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = f"命令: {command}\n"
        output += f"工作目录: {working_directory}\n"
        output += f"返回码: {result.returncode}\n"
        
        if result.stdout:
            output += f"输出:\n{result.stdout}\n"
        
        if result.stderr:
            output += f"错误:\n{result.stderr}\n"
        
        return output
