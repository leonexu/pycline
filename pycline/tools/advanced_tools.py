"""高级工具实现 - replace_in_file, str_replace_editor, grep_search"""

import os
import re
import shutil
import time
import fnmatch
import difflib
from typing import List, Optional
from langchain_core.tools import tool


@tool
def replace_in_file(file_path: str, old_str: str, new_str: str, occurrence: int = -1) -> str:
    """文件内容替换工具
    
    Args:
        file_path: 要修改的文件路径
        old_str: 要替换的原始字符串
        new_str: 替换后的新字符串
        occurrence: 替换第几个匹配项，-1表示替换所有
    """
    if not os.path.exists(file_path):
        return f"错误：文件 {file_path} 不存在"
        
    # 创建备份
    backup_path = f"{file_path}.backup.{int(time.time())}"
    shutil.copy2(file_path, backup_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original_content = content
    
    if occurrence == -1:
        # 替换所有出现
        new_content = content.replace(old_str, new_str)
        count = content.count(old_str)
    else:
        # 替换指定出现次数
        parts = content.split(old_str)
        if len(parts) > occurrence:
            new_content = old_str.join(parts[:occurrence]) + new_str + old_str.join(parts[occurrence+1:])
            count = 1
        else:
            new_content = content
            count = 0
            
    if count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        # 生成差异报告
        diff_lines = list(difflib.unified_diff(
            original_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"{file_path} (原始)",
            tofile=f"{file_path} (修改后)",
            lineterm=""
        ))
        
        diff_output = "".join(diff_lines[:20])  # 限制差异输出长度
        if len(diff_lines) > 20:
            diff_output += "\n... (差异过长，已截断)"
            
        return f"成功替换 {count} 处内容\n\n差异预览:\n{diff_output}"
    else:
        # 删除备份
        os.remove(backup_path)
        return f"未找到要替换的内容: '{old_str}'"


@tool  
def str_replace_editor(file_path: str, old_str: str, new_str: str) -> str:
    """精确字符串替换编辑器
    
    Args:
        file_path: 要编辑的文件路径
        old_str: 要替换的精确字符串（支持多行）
        new_str: 替换后的新字符串
    """
    if not os.path.exists(file_path):
        return f"错误：文件 {file_path} 不存在"
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 精确匹配并替换（只替换第一个匹配）
    if old_str in content:
        new_content = content.replace(old_str, new_str, 1)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        # 生成差异报告
        diff_lines = list(difflib.unified_diff(
            content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"{file_path} (原始)",
            tofile=f"{file_path} (修改后)",
            lineterm=""
        ))
        
        diff_output = "".join(diff_lines[:15])
        if len(diff_lines) > 15:
            diff_output += "\n... (差异过长，已截断)"
            
        return f"文件已成功更新\n\n差异预览:\n{diff_output}"
    else:
        # 提供相似内容建议
        suggestions = _find_similar_content(content, old_str)
        if suggestions:
            return f"未找到完全匹配的内容。\n\n相似内容建议:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions[:3]))
        else:
            return f"未找到要替换的内容: '{old_str[:100]}...'" if len(old_str) > 100 else f"未找到要替换的内容: '{old_str}'"


@tool
def grep_search(pattern: str, directory: str = ".", file_pattern: str = "*", 
                max_results: int = 50, include_context: bool = True) -> str:
    """文件内容搜索工具
    
    Args:
        pattern: 搜索的正则表达式模式
        directory: 搜索目录
        file_pattern: 文件名模式（如 *.py）
        max_results: 最大结果数量
        include_context: 是否包含上下文行
    """
    matches = []
    pattern_regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    
    # 忽略的目录
    ignore_dirs = {
        '.git', 'node_modules', '__pycache__', '.venv', 'venv',
        'build', 'dist', '.next', '.nuxt', 'target', 'bin', 'obj',
        '.pytest_cache', '.mypy_cache', '.tox'
    }
    
    for root, dirs, files in os.walk(directory):
        # 过滤忽略的目录
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if fnmatch.fnmatch(file, file_pattern):
                file_path = os.path.join(root, file)
                
                # 跳过二进制文件
                if _is_binary_file(file_path):
                    continue
                    
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if pattern_regex.search(line):
                        if include_context:
                            # 提供上下文行
                            start_line = max(0, line_num - 2)
                            end_line = min(len(lines), line_num + 1)
                            context_lines = []
                            
                            for i in range(start_line, end_line):
                                prefix = ">>> " if i == line_num - 1 else "    "
                                context_lines.append(f"{prefix}{i+1:4d}: {lines[i]}")
                            
                            context = '\n'.join(context_lines)
                            matches.append(f"\n📁 {file_path}:{line_num}\n{context}")
                        else:
                            matches.append(f"{file_path}:{line_num}: {line.strip()}")
                        
                        if len(matches) >= max_results:
                            break
                            
                if len(matches) >= max_results:
                    break
                    
    if matches:
        result = f"🔍 搜索结果 (模式: '{pattern}', 文件: {file_pattern}):\n"
        result += "\n".join(matches)
        if len(matches) >= max_results:
            result += f"\n\n⚠️  结果已限制为 {max_results} 条，可能还有更多匹配"
        return result
    else:
        return f"❌ 未找到匹配 '{pattern}' 的内容"


def _find_similar_content(content: str, target: str, max_suggestions: int = 3) -> List[str]:
    """查找相似内容"""
    lines = content.split('\n')
    target_lines = target.split('\n')
    
    if len(target_lines) == 1:
        # 单行匹配
        target_line = target_lines[0].strip()
        similar_lines = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped and target_line:
                # 计算相似度
                similarity = difflib.SequenceMatcher(None, target_line.lower(), line_stripped.lower()).ratio()
                if similarity > 0.6:  # 相似度阈值
                    similar_lines.append((similarity, f"第{i+1}行: {line.strip()}"))
        
        # 按相似度排序
        similar_lines.sort(key=lambda x: x[0], reverse=True)
        return [line[1] for line in similar_lines[:max_suggestions]]
    else:
        # 多行匹配
        suggestions = []
        
        # 查找包含目标第一行的位置
        first_line = target_lines[0].strip()
        for i, line in enumerate(lines):
            if first_line.lower() in line.lower():
                # 提取周围几行作为建议
                start = max(0, i - 1)
                end = min(len(lines), i + len(target_lines) + 1)
                suggestion = '\n'.join(lines[start:end])
                suggestions.append(f"第{i+1}行附近:\n{suggestion}")
                
        return suggestions[:max_suggestions]


def _is_binary_file(file_path: str) -> bool:
    """检查是否为二进制文件"""
    with open(file_path, 'rb') as f:
        chunk = f.read(1024)
        return b'\0' in chunk


class AdvancedToolManager:
    """
    高级工具管理器 - 已废弃，由AI直接决定工具使用
    
    注意：这个类已经不再使用基于规则的工具选择
    现在由LangGraphProvider的AI直接决定使用哪些工具
    """
    
    def __init__(self):
        self.tools = {
            'replace_in_file': replace_in_file,
            'str_replace_editor': str_replace_editor,
            'grep_search': grep_search
        }
    
    async def process_request(self, user_input: str, context: list, working_directory: str) -> str:
        """
        这个方法已废弃 - 现在由AI直接处理请求
        """
        return "错误：此方法已废弃，应该由AI直接处理请求"


# 导出工具列表
ADVANCED_TOOLS = [replace_in_file, str_replace_editor, grep_search]
