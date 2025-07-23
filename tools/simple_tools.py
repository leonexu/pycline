"""简化的工具实现 - 使用全局函数和@tool装饰符"""

import os
import subprocess
from langchain_core.tools import tool


@tool
def read_file(file_path: str) -> str:
    """读取文件内容"""
    if not os.path.exists(file_path):
        return f"错误：文件 {file_path} 不存在"
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    return f"文件 {file_path} 的内容：\n```\n{content}\n```"


@tool
def write_file(file_path: str, content: str) -> str:
    """写入文件内容"""
    # 创建目录（如果不存在）
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return f"成功写入文件 {file_path}"


@tool
def list_directory(directory_path: str) -> str:
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


@tool
def execute_command(command: str, working_directory: str = ".") -> str:
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


# 导出所有工具
SIMPLE_TOOLS = [read_file, write_file, list_directory, execute_command]
