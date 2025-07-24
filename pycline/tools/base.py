"""工具基类定义"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class Tool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式
        
        Returns:
            Dict: JSON Schema格式的参数定义
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            str: 执行结果
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """验证参数
        
        Args:
            parameters: 参数字典
            
        Returns:
            bool: 是否有效
        """
        return True
