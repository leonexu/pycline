"""工具执行器 - 安全执行工具调用"""

import time
from typing import Dict, Any, List
from .models import ToolCall
from .config import SecurityConfig
from ..tools.base import Tool


class ToolExecutor:
    """工具执行器，负责安全执行工具"""
    
    def __init__(self, security_config: SecurityConfig):
        self.security_config = security_config
        self.tools: Dict[str, Tool] = {}
    
    def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
    
    def get_available_tools(self) -> List[Tool]:
        """获取可用工具列表"""
        return list(self.tools.values())
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolCall:
        """执行工具调用"""
        
        start_time = time.time()
        tool_call = ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            success=False
        )
        
        # 1. 检查工具是否存在
        if tool_name not in self.tools:
            tool_call.error = f"Tool '{tool_name}' not found"
            return tool_call
        
        tool = self.tools[tool_name]
        
        # 2. 验证参数
        if not tool.validate_parameters(parameters):
            tool_call.error = f"Invalid parameters for tool '{tool_name}'"
            return tool_call
        
        # 3. 执行工具
        result = tool.execute(**parameters)
        tool_call.result = result
        tool_call.success = True
        tool_call.execution_time = time.time() - start_time
        
        return tool_call
