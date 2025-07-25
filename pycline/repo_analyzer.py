"""
代码库分析器 - 基于Aider的RepoMap系统实现
提供智能代码理解和上下文生成能力
"""

import os
import re
import json
import time
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, NamedTuple
from collections import defaultdict, Counter
from dataclasses import dataclass
import math

import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_javascript
import networkx as nx
from diskcache import Cache


class Tag(NamedTuple):
    """代码标签，表示一个符号定义或引用"""
    rel_fname: str
    fname: str
    line: int
    name: str
    kind: str  # "def" or "ref"


@dataclass
class FileAnalysisResult:
    """文件分析结果"""
    file_path: str
    language: str
    definitions: List[Tag]
    references: List[Tag]
    imports: List[str]
    classes: List[str]
    functions: List[str]
    last_modified: float


class LanguageDetector:
    """语言检测器"""
    
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'bash',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.txt': 'text'
    }
    
    @classmethod
    def detect_language(cls, file_path: str) -> Optional[str]:
        """检测文件语言"""
        ext = Path(file_path).suffix.lower()
        return cls.LANGUAGE_MAP.get(ext)
    
    @classmethod
    def is_source_file(cls, file_path: str) -> bool:
        """判断是否为源代码文件"""
        return cls.detect_language(file_path) is not None


class TreeSitterParser:
    """Tree-sitter解析器"""
    
    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """初始化解析器"""
        # Python解析器
        python_language = Language(tree_sitter_python.language())
        python_parser = Parser()
        python_parser.language = python_language
        self.languages['python'] = python_language
        self.parsers['python'] = python_parser
        
        # JavaScript解析器
        js_language = Language(tree_sitter_javascript.language())
        js_parser = Parser()
        js_parser.language = js_language
        self.languages['javascript'] = js_language
        self.parsers['javascript'] = js_parser
        self.languages['typescript'] = js_language  # TypeScript使用JS解析器
        self.parsers['typescript'] = js_parser
    
    def parse_file(self, file_path: str, content: str) -> List[Tag]:
        """解析文件并提取标签"""
        language = LanguageDetector.detect_language(file_path)
        if not language or language not in self.parsers:
            return self._fallback_parse(file_path, content, language)
        
        parser = self.parsers[language]
        tree = parser.parse(bytes(content, 'utf8'))
        
        tags = []
        rel_fname = os.path.relpath(file_path)
        
        # 遍历AST节点
        self._extract_tags_from_node(tree.root_node, tags, rel_fname, file_path, content, language)
        
        return tags
    
    def _extract_tags_from_node(self, node, tags: List[Tag], rel_fname: str, fname: str, content: str, language: str):
        """从AST节点提取标签"""
        if language == 'python':
            self._extract_python_tags(node, tags, rel_fname, fname, content)
        elif language in ['javascript', 'typescript']:
            self._extract_js_tags(node, tags, rel_fname, fname, content)
        else:
            self._extract_generic_tags(node, tags, rel_fname, fname, content)
    
    def _extract_python_tags(self, node, tags: List[Tag], rel_fname: str, fname: str, content: str):
        """提取Python标签"""
        def traverse(node):
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=node.start_point[0],
                        name=name_node.text.decode('utf8'),
                        kind='def'
                    ))
            
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=node.start_point[0],
                        name=name_node.text.decode('utf8'),
                        kind='def'
                    ))
            
            elif node.type == 'identifier':
                # 简单的引用检测
                name = node.text.decode('utf8')
                if len(name) > 2 and name.isidentifier():
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=node.start_point[0],
                        name=name,
                        kind='ref'
                    ))
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
    
    def _extract_js_tags(self, node, tags: List[Tag], rel_fname: str, fname: str, content: str):
        """提取JavaScript/TypeScript标签"""
        def traverse(node):
            if node.type in ['function_declaration', 'function_expression', 'arrow_function']:
                name_node = node.child_by_field_name('name')
                if name_node:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=node.start_point[0],
                        name=name_node.text.decode('utf8'),
                        kind='def'
                    ))
            
            elif node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=node.start_point[0],
                        name=name_node.text.decode('utf8'),
                        kind='def'
                    ))
            
            elif node.type == 'identifier':
                name = node.text.decode('utf8')
                if len(name) > 2:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=node.start_point[0],
                        name=name,
                        kind='ref'
                    ))
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
    
    def _extract_generic_tags(self, node, tags: List[Tag], rel_fname: str, fname: str, content: str):
        """提取通用标签"""
        # 简单的通用提取逻辑
        def traverse(node):
            if node.type in ['identifier', 'name']:
                name = node.text.decode('utf8')
                if len(name) > 2:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=fname,
                        line=node.start_point[0],
                        name=name,
                        kind='ref'
                    ))
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
    
    def _fallback_parse(self, file_path: str, content: str, language: str) -> List[Tag]:
        """回退解析方法，使用正则表达式"""
        tags = []
        rel_fname = os.path.relpath(file_path)
        lines = content.split('\n')
        
        if language == 'python':
            # Python函数和类定义
            for i, line in enumerate(lines):
                # 函数定义
                func_match = re.match(r'^\s*def\s+(\w+)', line)
                if func_match:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=file_path,
                        line=i,
                        name=func_match.group(1),
                        kind='def'
                    ))
                
                # 类定义
                class_match = re.match(r'^\s*class\s+(\w+)', line)
                if class_match:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=file_path,
                        line=i,
                        name=class_match.group(1),
                        kind='def'
                    ))
        
        elif language in ['javascript', 'typescript']:
            # JavaScript函数和类定义
            for i, line in enumerate(lines):
                # 函数定义
                func_matches = re.finditer(r'function\s+(\w+)|(\w+)\s*=\s*function|(\w+)\s*=\s*\(.*?\)\s*=>', line)
                for match in func_matches:
                    name = match.group(1) or match.group(2) or match.group(3)
                    if name:
                        tags.append(Tag(
                            rel_fname=rel_fname,
                            fname=file_path,
                            line=i,
                            name=name,
                            kind='def'
                        ))
                
                # 类定义
                class_match = re.match(r'^\s*class\s+(\w+)', line)
                if class_match:
                    tags.append(Tag(
                        rel_fname=rel_fname,
                        fname=file_path,
                        line=i,
                        name=class_match.group(1),
                        kind='def'
                    ))
        
        return tags


class RepoAnalyzer:
    """代码库分析器"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.cache_dir = os.path.join(workspace_path, ".pycline", "repo_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化缓存
        self.cache = Cache(self.cache_dir)
        
        # 初始化解析器
        self.parser = TreeSitterParser()
        
        # 分析结果
        self.file_analyses: Dict[str, FileAnalysisResult] = {}
        self.dependency_graph = None
        self.ranked_files = []
        
        # 配置
        self.max_files_to_analyze = 1000
        self.max_file_size = 1024 * 1024  # 1MB
    
    def analyze_codebase(self, force_refresh: bool = False) -> Dict[str, Any]:
        """分析整个代码库"""
        print("[RepoAnalyzer] 开始分析代码库...")
        
        # 1. 发现源代码文件
        source_files = self._discover_source_files()
        print(f"[RepoAnalyzer] 发现 {len(source_files)} 个源代码文件")
        
        # 2. 分析每个文件
        analyzed_count = 0
        for file_path in source_files[:self.max_files_to_analyze]:
            if self._analyze_file(file_path, force_refresh):
                analyzed_count += 1
        
        print(f"[RepoAnalyzer] 成功分析 {analyzed_count} 个文件")
        
        # 3. 构建依赖图
        self._build_dependency_graph()
        
        # 4. 计算文件重要性排序
        self._rank_files()
        
        return {
            "total_files": len(source_files),
            "analyzed_files": analyzed_count,
            "top_files": self.ranked_files[:20],
            "languages": self._get_language_stats(),
            "analysis_time": time.time()
        }
    
    def get_relevant_context(self, 
                           task_description: str, 
                           mentioned_files: List[str] = None,
                           max_tokens: int = 8000) -> str:
        """根据任务描述获取相关代码上下文"""
        if not self.ranked_files:
            self.analyze_codebase()
        
        # 1. 提取任务描述中的关键词
        keywords = self._extract_keywords(task_description)
        
        # 2. 查找相关文件和符号
        relevant_items = self._find_relevant_items(keywords, mentioned_files)
        
        # 3. 生成上下文字符串
        context = self._generate_context_string(relevant_items, max_tokens)
        
        return context
    
    def _discover_source_files(self) -> List[str]:
        """发现源代码文件"""
        source_files = []
        
        # 忽略的目录
        ignore_dirs = {
            '.git', '.pycline', '__pycache__', 'node_modules', 
            '.venv', 'venv', '.env', 'dist', 'build', '.next',
            '.pytest_cache', '.mypy_cache', '.tox'
        }
        
        # 忽略的文件模式
        ignore_patterns = [
            r'\.pyc$', r'\.pyo$', r'\.pyd$',
            r'\.so$', r'\.dll$', r'\.dylib$',
            r'\.min\.js$', r'\.bundle\.js$',
            r'\.map$', r'\.lock$'
        ]
        
        for root, dirs, files in os.walk(self.workspace_path):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # 检查文件大小
                if os.path.getsize(file_path) > self.max_file_size:
                    continue
                
                # 检查是否为源代码文件
                if not LanguageDetector.is_source_file(file):
                    continue
                
                # 检查忽略模式
                if any(re.search(pattern, file) for pattern in ignore_patterns):
                    continue
                
                source_files.append(file_path)
        
        return source_files
    
    def _analyze_file(self, file_path: str, force_refresh: bool = False) -> bool:
        """分析单个文件"""
        # 检查缓存
        rel_path = os.path.relpath(file_path, self.workspace_path)
        mtime = os.path.getmtime(file_path)
        cache_key = f"file_analysis:{rel_path}:{mtime}"
        
        if not force_refresh:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.file_analyses[rel_path] = FileAnalysisResult(**cached_result)
                return True
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 检测语言
        language = LanguageDetector.detect_language(file_path)
        if not language:
            return False
        
        # 解析文件
        tags = self.parser.parse_file(file_path, content)
        
        # 分类标签
        definitions = [tag for tag in tags if tag.kind == 'def']
        references = [tag for tag in tags if tag.kind == 'ref']
        
        # 提取额外信息
        imports = self._extract_imports(content, language)
        classes = [tag.name for tag in definitions if self._is_class_definition(tag, content, language)]
        functions = [tag.name for tag in definitions if self._is_function_definition(tag, content, language)]
        
        # 创建分析结果
        result = FileAnalysisResult(
            file_path=rel_path,
            language=language,
            definitions=definitions,
            references=references,
            imports=imports,
            classes=classes,
            functions=functions,
            last_modified=mtime
        )
        
        # 缓存结果
        self.file_analyses[rel_path] = result
        self.cache.set(cache_key, {
            'file_path': result.file_path,
            'language': result.language,
            'definitions': [tag._asdict() for tag in result.definitions],
            'references': [tag._asdict() for tag in result.references],
            'imports': result.imports,
            'classes': result.classes,
            'functions': result.functions,
            'last_modified': result.last_modified
        })
        
        return True
    
    def _extract_imports(self, content: str, language: str) -> List[str]:
        """提取导入语句"""
        imports = []
        lines = content.split('\n')
        
        if language == 'python':
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
        
        elif language in ['javascript', 'typescript']:
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('const ') and 'require(' in line:
                    imports.append(line)
        
        return imports
    
    def _is_class_definition(self, tag: Tag, content: str, language: str) -> bool:
        """判断是否为类定义"""
        lines = content.split('\n')
        if tag.line < len(lines):
            line = lines[tag.line].strip()
            if language == 'python':
                return line.startswith('class ')
            elif language in ['javascript', 'typescript']:
                return 'class ' in line
        return False
    
    def _is_function_definition(self, tag: Tag, content: str, language: str) -> bool:
        """判断是否为函数定义"""
        lines = content.split('\n')
        if tag.line < len(lines):
            line = lines[tag.line].strip()
            if language == 'python':
                return line.startswith('def ')
            elif language in ['javascript', 'typescript']:
                return 'function' in line or '=>' in line
        return False
    
    def _build_dependency_graph(self):
        """构建依赖图"""
        self.dependency_graph = nx.DiGraph()
        
        # 收集所有定义和引用
        all_definitions = defaultdict(set)  # symbol -> set of files that define it
        all_references = defaultdict(list)  # symbol -> list of files that reference it
        
        for file_path, analysis in self.file_analyses.items():
            # 添加文件节点
            self.dependency_graph.add_node(file_path, type='file', language=analysis.language)
            
            # 收集定义
            for tag in analysis.definitions:
                all_definitions[tag.name].add(file_path)
            
            # 收集引用
            for tag in analysis.references:
                all_references[tag.name].append(file_path)
        
        # 构建依赖边
        for symbol, referencing_files in all_references.items():
            defining_files = all_definitions.get(symbol, set())
            
            for ref_file in referencing_files:
                for def_file in defining_files:
                    if ref_file != def_file:
                        # 计算权重
                        weight = self._calculate_dependency_weight(symbol, ref_file, def_file)
                        self.dependency_graph.add_edge(ref_file, def_file, weight=weight, symbol=symbol)
    
    def _calculate_dependency_weight(self, symbol: str, ref_file: str, def_file: str) -> float:
        """计算依赖权重"""
        weight = 1.0
        
        # 符号名称长度权重（长名称更重要）
        if len(symbol) >= 8:
            weight *= 2.0
        
        # 驼峰命名权重
        if any(c.isupper() for c in symbol) and any(c.islower() for c in symbol):
            weight *= 1.5
        
        # 私有符号权重降低
        if symbol.startswith('_'):
            weight *= 0.5
        
        return weight
    
    def _rank_files(self):
        """使用PageRank算法对文件进行排序"""
        if not self.dependency_graph:
            # 简单排序：按定义数量
            file_scores = []
            for file_path, analysis in self.file_analyses.items():
                score = len(analysis.definitions) * 2 + len(analysis.functions) + len(analysis.classes)
                file_scores.append((file_path, score))
            
            self.ranked_files = [file_path for file_path, _ in sorted(file_scores, key=lambda x: x[1], reverse=True)]
            return
        
        # 使用PageRank算法
        pagerank_scores = nx.pagerank(self.dependency_graph, weight='weight')
        
        # 按分数排序
        self.ranked_files = sorted(pagerank_scores.keys(), key=lambda x: pagerank_scores[x], reverse=True)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text.lower())
        
        # 过滤常见词汇
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
        
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # 返回去重后的关键词
        return list(set(keywords))
    
    def _find_relevant_items(self, keywords: List[str], mentioned_files: List[str] = None) -> List[Tuple[str, float]]:
        """查找相关的文件和符号"""
        file_scores = defaultdict(float)
        
        # 1. 处理明确提到的文件
        if mentioned_files:
            for file_path in mentioned_files:
                rel_path = os.path.relpath(file_path, self.workspace_path)
                if rel_path in self.file_analyses:
                    file_scores[rel_path] += 10.0
        
        # 2. 基于关键词匹配
        for file_path, analysis in self.file_analyses.items():
            score = 0.0
            
            # 文件名匹配
            file_name = os.path.basename(file_path).lower()
            for keyword in keywords:
                if keyword in file_name:
                    score += 5.0
            
            # 符号名匹配
            for tag in analysis.definitions + analysis.references:
                for keyword in keywords:
                    if keyword.lower() in tag.name.lower():
                        score += 2.0 if tag.kind == 'def' else 1.0
            
            # 导入语句匹配
            for import_stmt in analysis.imports:
                for keyword in keywords:
                    if keyword in import_stmt.lower():
                        score += 1.5
            
            if score > 0:
                file_scores[file_path] += score
        
        # 3. 添加排名靠前的文件
        for i, file_path in enumerate(self.ranked_files[:10]):
            if file_path not in file_scores:
                file_scores[file_path] += max(0.5, 2.0 - i * 0.2)
        
        # 按分数排序
        return sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    
    def _generate_context_string(self, relevant_items: List[Tuple[str, float]], max_tokens: int) -> str:
        """生成上下文字符串"""
        context_parts = []
        current_tokens = 0
        
        context_parts.append("# 代码库结构概览\n")
        current_tokens += 10
        
        for file_path, score in relevant_items:
            if current_tokens >= max_tokens:
                break
            
            if file_path not in self.file_analyses:
                continue
            
            analysis = self.file_analyses[file_path]
            
            # 文件头部信息
            file_info = f"\n## {file_path} ({analysis.language})\n"
            
            # 主要定义
            if analysis.classes:
                file_info += f"Classes: {', '.join(analysis.classes[:5])}\n"
            
            if analysis.functions:
                file_info += f"Functions: {', '.join(analysis.functions[:10])}\n"
            
            if analysis.imports:
                file_info += f"Imports: {len(analysis.imports)} items\n"
            
            # 估算token数量（粗略估计：1 token ≈ 4 字符）
            estimated_tokens = len(file_info) // 4
            
            if current_tokens + estimated_tokens <= max_tokens:
                context_parts.append(file_info)
                current_tokens += estimated_tokens
            else:
                break
        
        return "".join(context_parts)
    
    def _get_language_stats(self) -> Dict[str, int]:
        """获取语言统计信息"""
        stats = defaultdict(int)
        for analysis in self.file_analyses.values():
            stats[analysis.language] += 1
        return dict(stats)
    
    def get_file_analysis(self, file_path: str) -> Optional[FileAnalysisResult]:
        """获取单个文件的分析结果"""
        rel_path = os.path.relpath(file_path, self.workspace_path)
        return self.file_analyses.get(rel_path)
    
    def invalidate_file_cache(self, file_path: str):
        """使文件缓存失效"""
        rel_path = os.path.relpath(file_path, self.workspace_path)
        
        # 移除内存中的分析结果
        if rel_path in self.file_analyses:
            del self.file_analyses[rel_path]
        
        # 清除相关缓存
        cache_keys_to_remove = []
        for key in self.cache:
            if rel_path in str(key):
                cache_keys_to_remove.append(key)
        
        for key in cache_keys_to_remove:
            del self.cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        return {
            "total_files_analyzed": len(self.file_analyses),
            "total_definitions": sum(len(a.definitions) for a in self.file_analyses.values()),
            "total_references": sum(len(a.references) for a in self.file_analyses.values()),
            "languages": self._get_language_stats(),
            "cache_size": len(self.cache),
            "top_files": self.ranked_files[:10] if self.ranked_files else []
        }


    def build_enhanced_context(self, 
                              task_description: str, 
                              context_files: Optional[List[str]] = None,
                              max_context_tokens: int = 12000) -> Dict[str, Any]:
        """
        构建增强的上下文信息
        集成代码库映射和智能文件选择
        """
        print("[RepoAnalyzer] 开始构建增强上下文...")
        
        # 1. 分析项目结构（如果还没有分析过）
        if not self.file_analyses:
            self.analyze_codebase()
        
        # 2. 检测项目类型
        project_type = self._detect_project_type()
        
        # 3. 获取相关文件列表
        relevant_files = self._get_relevant_files_for_context(
            task_description, 
            context_files
        )
        
        # 4. 读取文件内容
        file_infos = self._read_context_files(relevant_files, max_context_tokens // 2)
        
        # 5. 生成代码库映射
        repo_map = self.get_relevant_context(
            task_description, 
            context_files,
            max_tokens=max_context_tokens // 2
        )
        
        # 6. 构建项目信息
        project_info = {
            "name": os.path.basename(self.workspace_path),
            "type": project_type,
            "structure": {
                "total_files": len(self.file_analyses),
                "analyzed_files": len(self.file_analyses),
                "top_files": self.ranked_files[:10] if self.ranked_files else []
            },
            "languages": self._get_language_stats()
        }
        
        # 7. 计算token使用量
        total_chars = sum(len(f["content"]) for f in file_infos)
        if repo_map:
            total_chars += len(repo_map)
        token_usage = total_chars // 4  # 粗略估算
        
        context = {
            "workspace_path": self.workspace_path,
            "task_description": task_description,
            "project_info": project_info,
            "files": file_infos,
            "repo_map": repo_map,
            "token_usage": token_usage
        }
        
        print(f"[RepoAnalyzer] 增强上下文构建完成，包含 {len(file_infos)} 个文件，预估 {token_usage} tokens")
        
        return context
    
    def _detect_project_type(self) -> str:
        """检测项目类型"""
        # 检查特征文件
        indicators = {
            "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "javascript": ["package.json", "yarn.lock", "package-lock.json"],
            "java": ["pom.xml", "build.gradle", "gradle.properties"],
            "csharp": ["*.csproj", "*.sln", "packages.config"],
            "go": ["go.mod", "go.sum"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "php": ["composer.json", "composer.lock"],
            "ruby": ["Gemfile", "Gemfile.lock"],
        }
        
        for project_type, files in indicators.items():
            for file_pattern in files:
                if "*" in file_pattern:
                    # 通配符匹配
                    import glob
                    matches = glob.glob(os.path.join(self.workspace_path, file_pattern))
                    if matches:
                        return project_type
                else:
                    # 精确匹配
                    if os.path.exists(os.path.join(self.workspace_path, file_pattern)):
                        return project_type
        
        return "unknown"
    
    def _get_relevant_files_for_context(self, 
                                       task_description: str, 
                                       context_files: Optional[List[str]]) -> List[str]:
        """获取用于上下文的相关文件列表"""
        relevant_files = []
        
        # 1. 添加明确指定的文件
        if context_files:
            for file_path in context_files:
                full_path = os.path.join(self.workspace_path, file_path) if not os.path.isabs(file_path) else file_path
                if os.path.exists(full_path):
                    relevant_files.append(full_path)
        
        # 2. 从排序后的文件中选择最相关的
        if self.ranked_files:
            for file_path in self.ranked_files[:10]:
                full_path = os.path.join(self.workspace_path, file_path)
                if os.path.exists(full_path) and full_path not in relevant_files:
                    relevant_files.append(full_path)
        
        # 3. 如果没有找到相关文件，添加一些默认的重要文件
        if not relevant_files:
            default_files = [
                "README.md", "README.txt", "readme.md",
                "main.py", "app.py", "index.js", "main.js",
                "package.json", "requirements.txt", "setup.py"
            ]
            
            for file_name in default_files:
                full_path = os.path.join(self.workspace_path, file_name)
                if os.path.exists(full_path):
                    relevant_files.append(full_path)
                    if len(relevant_files) >= 5:  # 限制默认文件数量
                        break
        
        return relevant_files[:15]  # 限制最大文件数量
    
    def _read_context_files(self, file_paths: List[str], max_tokens: int) -> List[Dict[str, Any]]:
        """读取上下文文件内容"""
        file_infos = []
        current_tokens = 0
        max_file_size = 50 * 1024  # 50KB限制
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                continue
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size > max_file_size:
                print(f"[RepoAnalyzer] 跳过大文件: {file_path} ({file_size} bytes)")
                continue
            
            # 读取文件内容
            content = ""
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 估算token数量
            estimated_tokens = len(content) // 4
            if current_tokens + estimated_tokens > max_tokens:
                print(f"[RepoAnalyzer] 达到token限制，停止读取更多文件")
                break
            
            # 获取相对路径
            rel_path = os.path.relpath(file_path, self.workspace_path)
            
            # 检测语言
            language = LanguageDetector.detect_language(file_path) or "text"
            
            file_info = {
                "path": rel_path,
                "content": content,
                "language": language,
                "size": file_size,
                "last_modified": os.path.getmtime(file_path)
            }
            
            file_infos.append(file_info)
            current_tokens += estimated_tokens
        
        return file_infos


# 使用示例
if __name__ == "__main__":
    analyzer = RepoAnalyzer(".")
    
    # 分析代码库
    result = analyzer.analyze_codebase()
    print("分析结果:", result)
    
    # 获取相关上下文
    context = analyzer.get_relevant_context("创建一个新的用户管理功能")
    print("相关上下文:", context)
    
    # 构建增强上下文
    enhanced_context = analyzer.build_enhanced_context(
        "创建一个新的用户管理功能",
        context_files=["main.py", "config.py"]
    )
    print("增强上下文:", enhanced_context["project_info"])
    
    # 获取统计信息
    stats = analyzer.get_stats()
    print("统计信息:", stats)
