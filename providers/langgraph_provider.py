"""基于LangGraph的AI提供者"""

import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from core.config import AIConfig
from tools.base import Tool


class LangGraphProvider:
    """基于LangGraph的AI提供者，使用ReAct Agent"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.llm = self._create_llm()
        self.agent = None
    
    def _create_llm(self):
        """根据配置创建LLM"""
        return ChatDeepSeek(
            model="deepseek-chat",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )
    
    def create_system_prompt(self) -> str:
        """创建系统提示"""
        return """你是PyCline，一个专业的AI编程助手。

可用工具：
- read_file: 读取文件内容，参数：file_path
- write_file: 创建文件，参数：file_path, content  
- list_directory: 列出目录，参数：directory_path
- execute_command: 执行命令，参数：command, working_directory

请直接完成用户的任务，使用合适的工具。完成后简要说明你做了什么。"""
    
    def create_langchain_tools(self, tools: List[Tool]) -> List:
        """将PyCline工具转换为LangChain工具"""
        # 简化版本：直接使用预定义的简单工具
        from tools.simple_tools import SIMPLE_TOOLS
        return SIMPLE_TOOLS

    def execute_task(self, context_str: str, task_description: str, tools: List[Tool]) -> Dict[str, Any]:
        """使用LangGraph Agent执行任务"""
        
        # 转换工具
        langchain_tools = self.create_langchain_tools(tools)
        
        # 创建Agent
        system_prompt = self.create_system_prompt()
        self.agent = create_react_agent(self.llm, langchain_tools, prompt=system_prompt)
        
        # 构建完整的用户消息
        user_message = f"""项目上下文：
{context_str}

任务：{task_description}

请分析上下文，理解任务需求，然后使用合适的工具来完成任务。"""
        
        # 执行Agent
        result = self.agent.invoke({"messages": [("user", user_message)]})
        
        # 提取最终响应
        final_message = result['messages'][-1]
        ai_response = final_message.content
        
        # 分析执行过程中的工具调用
        tool_calls = []
        for message in result['messages']:
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "name": tool_call['name'],
                        "args": tool_call.get('args', {}),
                        "result": "Tool executed successfully"  # LangGraph会自动处理结果
                    })
        
        return {
            "content": ai_response,
            "tool_calls": tool_calls,
            "finish_reason": "stop",
            "full_messages": result['messages']
        }
