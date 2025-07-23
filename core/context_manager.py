"""上下文管理器 - 智能构建和优化任务上下文"""

import os
import fnmatch
from typing import List, Optional, Dict, Any

from .models import Context, ProjectInfo
from .config import ContextConfig


class ContextManager:
    """上下文管理器，负责构建和优化上下文"""
    
    def __init__(self, config: ContextConfig):
        self.config = config
        self.project_analyzer = ProjectAnalyzer()
        self.file_discovery = FileDiscovery()
        self.token_calculator = TokenCalculator()
    
    def build_context(self, 
                     task_description: str,
                     workspace_path: str,
                     context_files: Optional[List[str]] = None,
                     **kwargs) -> Context:
        """构建任务上下文"""
        
        # 1. 分析项目结构
        project_info = self.project_analyzer.analyze(workspace_path)
        
        # 2. 发现相关文件
        if context_files:
            relevant_files = context_files
        else:
            relevant_files = self.file_discovery.discover_relevant_files(
                task_description, project_info, **kwargs
            )
        
        # 3. 读取文件内容
        files_with_content = []
        total_tokens = 0
        
        for file_path in relevant_files:
            full_path = os.path.join(workspace_path, file_path)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                file_tokens = self.token_calculator.calculate_tokens(content)
                
                # 检查是否超出限制
                if total_tokens + file_tokens > self.config.max_tokens:
                    # 尝试裁剪内容
                    remaining_tokens = self.config.max_tokens - total_tokens
                    if remaining_tokens > 100:  # 至少保留100个token
                        content = self._trim_content(content, remaining_tokens)
                        file_tokens = self.token_calculator.calculate_tokens(content)
                    else:
                        break
                
                files_with_content.append({
                    "path": file_path,
                    "content": content,
                    "tokens": file_tokens,
                    "size": len(content)
                })
                
                total_tokens += file_tokens
        
        # 4. 构建最终上下文
        context = Context(
            task_description=task_description,
            workspace_path=workspace_path,
            files=files_with_content,
            project_info=project_info.dict() if project_info else None,
            token_usage=total_tokens
        )
        
        return context
    
    def _trim_content(self, content: str, max_tokens: int) -> str:
        """裁剪内容以适应token限制"""
        lines = content.split('\n')
        
        # 优先保留重要行：类定义、函数定义、导入语句等
        important_lines = []
        other_lines = []
        
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith(('class ', 'def ', 'import ', 'from ')) or
                stripped.startswith('#') or
                '=' in stripped and 'def' not in stripped):
                important_lines.append(line)
            else:
                other_lines.append(line)
        
        # 先添加重要行
        result_lines = important_lines[:]
        current_tokens = self.token_calculator.calculate_tokens('\n'.join(result_lines))
        
        # 添加其他行直到达到限制
        for line in other_lines:
            line_tokens = self.token_calculator.calculate_tokens(line)
            if current_tokens + line_tokens <= max_tokens:
                result_lines.append(line)
                current_tokens += line_tokens
            else:
                break
        
        result = '\n'.join(result_lines)
        if len(result) < len(content):
            result += '\n# ... (内容被截断)'
        
        return result


class ProjectAnalyzer:
    """项目分析器，分析项目结构和特征"""
    
    def analyze(self, workspace_path: str) -> ProjectInfo:
        """分析项目结构"""
        
        project_info = ProjectInfo(
            path=workspace_path,
            name=os.path.basename(os.path.abspath(workspace_path)),
            type=self._detect_project_type(workspace_path),
            structure=self._analyze_structure(workspace_path),
            config_files=self._find_config_files(workspace_path),
            entry_points=self._find_entry_points(workspace_path)
        )
        
        return project_info
    
    def _detect_project_type(self, path: str) -> str:
        """检测项目类型"""
        if os.path.exists(os.path.join(path, "package.json")):
            return "nodejs"
        elif (os.path.exists(os.path.join(path, "requirements.txt")) or 
              os.path.exists(os.path.join(path, "pyproject.toml")) or
              os.path.exists(os.path.join(path, "setup.py"))):
            return "python"
        elif os.path.exists(os.path.join(path, "pom.xml")):
            return "java"
        elif os.path.exists(os.path.join(path, "Cargo.toml")):
            return "rust"
        elif os.path.exists(os.path.join(path, "go.mod")):
            return "go"
        else:
            return "unknown"
    
    def _analyze_structure(self, path: str) -> Dict[str, Any]:
        """分析目录结构"""
        structure = {
            "directories": [],
            "files": [],
            "total_files": 0,
            "total_size": 0
        }
        
        for root, dirs, files in os.walk(path):
            # 跳过隐藏目录和常见的忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and 
                      d not in ['node_modules', '__pycache__', 'target', 'build', 'dist']]
            
            rel_root = os.path.relpath(root, path)
            if rel_root != '.':
                structure["directories"].append(rel_root)
            
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(rel_root, file) if rel_root != '.' else file
                    file_size = os.path.getsize(os.path.join(root, file))
                    structure["files"].append({
                        "path": file_path,
                        "size": file_size,
                        "extension": os.path.splitext(file)[1]
                    })
                    structure["total_files"] += 1
                    structure["total_size"] += file_size
        
        return structure
    
    def _find_config_files(self, path: str) -> List[str]:
        """查找配置文件"""
        config_patterns = [
            "*.json", "*.yml", "*.yaml", "*.toml", "*.ini", "*.cfg",
            "Dockerfile", "docker-compose.*", "requirements.txt", "setup.py",
            "package.json", "pom.xml", "Cargo.toml", "go.mod"
        ]
        
        config_files = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                for pattern in config_patterns:
                    if fnmatch.fnmatch(file, pattern):
                        rel_path = os.path.relpath(os.path.join(root, file), path)
                        config_files.append(rel_path)
                        break
        
        return config_files
    
    def _find_entry_points(self, path: str) -> List[str]:
        """查找入口文件"""
        entry_patterns = [
            "main.py", "app.py", "server.py", "index.js", "main.js",
            "main.go", "main.rs", "Main.java"
        ]
        
        entry_points = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file in entry_patterns:
                    rel_path = os.path.relpath(os.path.join(root, file), path)
                    entry_points.append(rel_path)
        
        return entry_points


class FileDiscovery:
    """文件发现器，基于任务描述发现相关文件"""
    
    def discover_relevant_files(self, 
                              task_description: str,
                              project_info: ProjectInfo,
                              file_patterns: Optional[List[str]] = None,
                              exclude_patterns: Optional[List[str]] = None,
                              max_files: int = 50) -> List[str]:
        """发现相关文件"""
        
        # 1. 获取候选文件
        candidate_files = self._get_candidate_files(
            project_info, file_patterns, exclude_patterns
        )
        
        # 2. 简单的相关性评分（基于文件名和扩展名）
        scored_files = []
        task_lower = task_description.lower()
        
        for file_path in candidate_files:
            score = self._calculate_relevance_score(file_path, task_lower, project_info)
            scored_files.append((file_path, score))
        
        # 3. 按得分排序并限制数量
        scored_files.sort(key=lambda x: x[1], reverse=True)
        relevant_files = [file_path for file_path, score in scored_files[:max_files]]
        
        return relevant_files
    
    def _get_candidate_files(self, 
                           project_info: ProjectInfo,
                           file_patterns: Optional[List[str]] = None,
                           exclude_patterns: Optional[List[str]] = None) -> List[str]:
        """获取候选文件列表"""
        
        candidate_files = []
        
        for file_info in project_info.structure["files"]:
            file_path = file_info["path"]
            
            # 应用包含模式
            if file_patterns:
                if not any(fnmatch.fnmatch(file_path, pattern) for pattern in file_patterns):
                    continue
            
            # 应用排除模式
            if exclude_patterns:
                if any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns):
                    continue
            
            # 默认排除一些文件类型
            if self._should_exclude_file(file_path):
                continue
            
            candidate_files.append(file_path)
        
        return candidate_files
    
    def _calculate_relevance_score(self, file_path: str, task_description: str, project_info: ProjectInfo) -> float:
        """计算文件相关性得分"""
        score = 0.0
        
        filename = os.path.basename(file_path).lower()
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 1. 文件名相关性
        task_words = task_description.split()
        for word in task_words:
            if len(word) > 2 and word in filename:
                score += 0.5
        
        # 2. 文件类型相关性
        if project_info.type == "python" and file_ext == ".py":
            score += 0.3
        elif project_info.type == "nodejs" and file_ext in [".js", ".ts"]:
            score += 0.3
        elif project_info.type == "java" and file_ext == ".java":
            score += 0.3
        
        # 3. 配置文件和入口文件优先级
        if file_path in project_info.config_files:
            score += 0.2
        if file_path in project_info.entry_points:
            score += 0.4
        
        # 4. 文件位置相关性
        if "/" not in file_path:  # 根目录文件
            score += 0.1
        elif file_path.startswith("src/"):
            score += 0.2
        
        return min(score, 1.0)
    
    def _should_exclude_file(self, file_path: str) -> bool:
        """判断是否应该排除文件"""
        exclude_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', 
                            '.bin', '.obj', '.o', '.a', '.lib', '.jar', '.class',
                            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
                            '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.doc', '.docx'}
        
        exclude_names = {'__pycache__', '.git', '.svn', '.hg', 'node_modules',
                        '.pytest_cache', '.coverage', '.tox', 'dist', 'build'}
        
        file_ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)
        
        return (file_ext in exclude_extensions or 
                file_name in exclude_names or
                any(part in exclude_names for part in file_path.split(os.sep)))


class TokenCalculator:
    """Token计算器"""
    
    def calculate_tokens(self, text: str) -> int:
        """计算文本的token数量（简单估算）"""
        # 简单的token估算：大约1个token = 4个字符
        return len(text) // 4 + len(text.split())
