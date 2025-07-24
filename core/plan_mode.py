"""Plan模式实现 - 任务规划和分解"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from common_base import setup_logger
logger = setup_logger()

class TaskComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class SubTaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubTask:
    id: str
    name: str
    description: str
    dependencies: List[str]  # 依赖的其他子任务ID
    estimated_time: int      # 预估时间（分钟）
    priority: int           # 优先级 1-5
    tools_needed: List[str] # 需要的工具
    success_criteria: str   # 成功标准
    status: SubTaskStatus = SubTaskStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'dependencies': self.dependencies,
            'estimated_time': self.estimated_time,
            'priority': self.priority,
            'tools_needed': self.tools_needed,
            'success_criteria': self.success_criteria,
            'status': self.status.value
        }


@dataclass
class ExecutionPlan:
    task_id: str
    original_task: str
    subtasks: List[SubTask]
    execution_order: List[str]  # 子任务执行顺序
    estimated_total_time: int
    complexity: TaskComplexity
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'original_task': self.original_task,
            'subtasks': [task.to_dict() for task in self.subtasks],
            'execution_order': self.execution_order,
            'estimated_total_time': self.estimated_total_time,
            'complexity': self.complexity.value,
            'created_at': self.created_at.isoformat()
        }


class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, ai_provider):
        self.ai_provider = ai_provider
        
    def create_plan(self, task_description: str, workspace_path: str = ".") -> ExecutionPlan:
        """创建执行计划"""
        
        # 1. 分析任务复杂度
        complexity = self._assess_complexity(task_description)
        
        # 2. 分解任务
        subtasks = self._decompose_task(task_description, complexity)
        
        # 3. 分析依赖关系
        self._analyze_dependencies(subtasks)
        
        # 4. 确定执行顺序
        execution_order = self._determine_execution_order(subtasks)
        
        # 5. 计算总时间
        total_time = sum(task.estimated_time for task in subtasks)
        
        plan = ExecutionPlan(
            task_id=str(uuid.uuid4()),
            original_task=task_description,
            subtasks=subtasks,
            execution_order=execution_order,
            estimated_total_time=total_time,
            complexity=complexity,
            created_at=datetime.now()
        )
        
        return plan
    
    def _assess_complexity(self, task_description: str) -> TaskComplexity:
        """评估任务复杂度"""
        description_lower = task_description.lower()
        
        # 复杂任务指标
        complex_indicators = [
            '重构', 'refactor', '架构', 'architecture', '系统', 'system', 
            '框架', 'framework', '多个', 'multiple', '整个', 'entire'
        ]
        
        # 中等复杂度指标
        moderate_indicators = [
            '修改', 'modify', '更新', 'update', '添加', 'add', 
            '实现', 'implement', '集成', 'integrate'
        ]
        
        # 简单任务指标
        simple_indicators = [
            '创建', 'create', '写', 'write', '生成', 'generate',
            '一个', 'single', '简单', 'simple'
        ]
        
        if any(indicator in description_lower for indicator in complex_indicators):
            return TaskComplexity.COMPLEX
        elif any(indicator in description_lower for indicator in moderate_indicators):
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.SIMPLE
    
    def _decompose_task(self, task_description: str, complexity: TaskComplexity) -> List[SubTask]:
        """分解任务为子任务"""
        
        # 使用AI进行任务分解
        decomposition_prompt = f"""
请将以下任务分解为具体的子任务：

任务描述: {task_description}
任务复杂度: {complexity.value}

请按照以下格式返回子任务列表，每个子任务一行：
子任务名称 | 详细描述 | 预估时间(分钟) | 优先级(1-5) | 需要的工具 | 成功标准

例如：
创建项目结构 | 创建基本的目录和文件结构 | 10 | 5 | write_file,list_directory | 目录结构创建完成
编写核心代码 | 实现主要功能逻辑 | 30 | 4 | write_file,str_replace_editor | 核心功能可以正常运行

请确保子任务：
1. 具体可执行
2. 有明确的成功标准
3. 时间估算合理
4. 优先级合理
"""
        
        # 调用AI获取分解结果
        ai_response = self.ai_provider.generate(decomposition_prompt)
        
        # 解析AI响应
        subtasks = self._parse_subtasks_response(ai_response)
        
        # 如果AI解析失败，使用默认分解策略
        if not subtasks:
            subtasks = self._default_decomposition(task_description, complexity)
        
        return subtasks
    
    def _parse_subtasks_response(self, ai_response: str) -> List[SubTask]:
        """解析AI响应中的子任务"""
        subtasks = []
        lines = ai_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if '|' in line and not line.startswith('#') and not line.startswith('子任务名称'):
                parts = [part.strip() for part in line.split('|')]
                if len(parts) >= 6:
                    name = parts[0]
                    description = parts[1]
                    estimated_time = int(parts[2]) if parts[2].isdigit() else 15
                    priority = int(parts[3]) if parts[3].isdigit() else 3
                    tools_needed = [tool.strip() for tool in parts[4].split(',') if tool.strip()]
                    success_criteria = parts[5]
                    
                    subtask = SubTask(
                        id=str(uuid.uuid4()),
                        name=name,
                        description=description,
                        dependencies=[],
                        estimated_time=estimated_time,
                        priority=priority,
                        tools_needed=tools_needed,
                        success_criteria=success_criteria
                    )
                    subtasks.append(subtask)
        
        return subtasks
    
    def _default_decomposition(self, task_description: str, complexity: TaskComplexity) -> List[SubTask]:
        """默认任务分解策略"""
        subtasks = []
        
        if complexity == TaskComplexity.SIMPLE:
            # 简单任务：分析 -> 实现 -> 验证
            subtasks = [
                SubTask(
                    id=str(uuid.uuid4()),
                    name="分析需求",
                    description=f"分析任务需求: {task_description}",
                    dependencies=[],
                    estimated_time=5,
                    priority=5,
                    tools_needed=["read_file", "list_directory"],
                    success_criteria="需求分析完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="实现功能",
                    description="根据需求实现具体功能",
                    dependencies=[],
                    estimated_time=20,
                    priority=4,
                    tools_needed=["write_file", "str_replace_editor"],
                    success_criteria="功能实现完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="测试验证",
                    description="测试实现的功能是否正确",
                    dependencies=[],
                    estimated_time=10,
                    priority=3,
                    tools_needed=["execute_command", "read_file"],
                    success_criteria="功能测试通过"
                )
            ]
        elif complexity == TaskComplexity.MODERATE:
            # 中等复杂度：规划 -> 准备 -> 实现 -> 集成 -> 测试
            subtasks = [
                SubTask(
                    id=str(uuid.uuid4()),
                    name="制定详细计划",
                    description="制定详细的实现计划",
                    dependencies=[],
                    estimated_time=10,
                    priority=5,
                    tools_needed=["read_file", "grep_search"],
                    success_criteria="实现计划制定完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="准备环境",
                    description="准备开发环境和依赖",
                    dependencies=[],
                    estimated_time=15,
                    priority=4,
                    tools_needed=["execute_command", "write_file"],
                    success_criteria="开发环境准备就绪"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="核心功能实现",
                    description="实现核心功能模块",
                    dependencies=[],
                    estimated_time=40,
                    priority=5,
                    tools_needed=["write_file", "str_replace_editor", "replace_in_file"],
                    success_criteria="核心功能实现完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="功能集成",
                    description="集成各个功能模块",
                    dependencies=[],
                    estimated_time=20,
                    priority=4,
                    tools_needed=["str_replace_editor", "replace_in_file"],
                    success_criteria="功能集成完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="测试和优化",
                    description="全面测试并优化性能",
                    dependencies=[],
                    estimated_time=25,
                    priority=3,
                    tools_needed=["execute_command", "read_file", "grep_search"],
                    success_criteria="测试通过，性能满足要求"
                )
            ]
        else:  # COMPLEX
            # 复杂任务：调研 -> 设计 -> 分模块实现 -> 集成 -> 测试 -> 文档
            subtasks = [
                SubTask(
                    id=str(uuid.uuid4()),
                    name="需求调研",
                    description="深入调研需求和技术方案",
                    dependencies=[],
                    estimated_time=20,
                    priority=5,
                    tools_needed=["read_file", "grep_search", "list_directory"],
                    success_criteria="需求调研报告完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="架构设计",
                    description="设计系统架构和模块划分",
                    dependencies=[],
                    estimated_time=30,
                    priority=5,
                    tools_needed=["write_file"],
                    success_criteria="架构设计文档完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="核心模块实现",
                    description="实现核心业务模块",
                    dependencies=[],
                    estimated_time=60,
                    priority=5,
                    tools_needed=["write_file", "str_replace_editor", "replace_in_file"],
                    success_criteria="核心模块实现完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="辅助模块实现",
                    description="实现辅助功能模块",
                    dependencies=[],
                    estimated_time=40,
                    priority=4,
                    tools_needed=["write_file", "str_replace_editor"],
                    success_criteria="辅助模块实现完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="系统集成",
                    description="集成所有模块形成完整系统",
                    dependencies=[],
                    estimated_time=30,
                    priority=4,
                    tools_needed=["str_replace_editor", "replace_in_file"],
                    success_criteria="系统集成完成"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="全面测试",
                    description="进行全面的功能和性能测试",
                    dependencies=[],
                    estimated_time=40,
                    priority=3,
                    tools_needed=["execute_command", "read_file", "grep_search"],
                    success_criteria="所有测试通过"
                ),
                SubTask(
                    id=str(uuid.uuid4()),
                    name="文档编写",
                    description="编写用户文档和技术文档",
                    dependencies=[],
                    estimated_time=20,
                    priority=2,
                    tools_needed=["write_file"],
                    success_criteria="文档编写完成"
                )
            ]
        
        # 设置依赖关系
        for i in range(1, len(subtasks)):
            subtasks[i].dependencies = [subtasks[i-1].id]
        
        return subtasks
    
    def _analyze_dependencies(self, subtasks: List[SubTask]):
        """分析子任务之间的依赖关系"""
        # 基于任务名称和描述分析依赖关系
        for i, task in enumerate(subtasks):
            task_name_lower = task.name.lower()
            task_desc_lower = task.description.lower()
            
            # 检查是否依赖前面的任务
            for j in range(i):
                prev_task = subtasks[j]
                prev_name_lower = prev_task.name.lower()
                
                # 如果当前任务提到了前面任务的关键词，则可能存在依赖
                if any(keyword in task_desc_lower for keyword in prev_name_lower.split()):
                    if prev_task.id not in task.dependencies:
                        task.dependencies.append(prev_task.id)
    
    def _determine_execution_order(self, subtasks: List[SubTask]) -> List[str]:
        """确定执行顺序（拓扑排序）"""
        # 简单的拓扑排序实现
        task_dict = {task.id: task for task in subtasks}
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(task_id: str):
            if task_id in temp_visited:
                # 检测到循环依赖，忽略
                return
            if task_id in visited:
                return
                
            temp_visited.add(task_id)
            
            task = task_dict[task_id]
            for dep_id in task.dependencies:
                if dep_id in task_dict:
                    visit(dep_id)
            
            temp_visited.remove(task_id)
            visited.add(task_id)
            order.append(task_id)
        
        for task in subtasks:
            if task.id not in visited:
                visit(task.id)
        
        return order


from providers.langgraph_provider import LangGraphProvider

class PlanModeManager:
    """Plan模式管理器"""
    
    def __init__(self, ai_provider: LangGraphProvider):
        self.ai_provider = ai_provider
        self.task_planner = TaskPlanner(ai_provider)
        self.current_plan: Optional[ExecutionPlan] = None
    
    def create_plan(self, task_description: str, workspace_path: str = ".") -> ExecutionPlan:
        """创建执行计划"""
        plan = self.task_planner.create_plan(task_description, workspace_path)
        self.current_plan = plan
        return plan
    
    def get_plan_summary(self, plan: ExecutionPlan) -> str:
        """获取计划摘要"""
        summary = f"""
📋 任务执行计划

🎯 原始任务: {plan.original_task}
📊 复杂度: {plan.complexity.value}
⏱️  预估总时间: {plan.estimated_total_time} 分钟
📅 创建时间: {plan.created_at.strftime('%Y-%m-%d %H:%M:%S')}

📝 子任务列表 ({len(plan.subtasks)} 个):
"""
        
        for i, task_id in enumerate(plan.execution_order, 1):
            task = next(t for t in plan.subtasks if t.id == task_id)
            summary += f"""
{i}. {task.name}
   📖 描述: {task.description}
   ⏰ 预估时间: {task.estimated_time} 分钟
   🔧 需要工具: {', '.join(task.tools_needed)}
   ✅ 成功标准: {task.success_criteria}
"""
            
            if task.dependencies:
                dep_names = []
                for dep_id in task.dependencies:
                    dep_task = next((t for t in plan.subtasks if t.id == dep_id), None)
                    if dep_task:
                        dep_names.append(dep_task.name)
                if dep_names:
                    summary += f"   🔗 依赖: {', '.join(dep_names)}\n"
        
        return summary
    
    def approve_plan(self) -> bool:
        """用户确认计划"""
        if not self.current_plan:
            return False
            
        logger.info(self.get_plan_summary(self.current_plan))
        logger.info("\n" + "="*50)
        
        while True:
            response = input("是否批准此执行计划? (y/n/m=修改): ").lower().strip()
            
            if response in ['y', 'yes', '是', '批准']:
                return True
            elif response in ['n', 'no', '否', '拒绝']:
                return False
            elif response in ['m', 'modify', '修改']:
                self._modify_plan()
                logger.info("\n修改后的计划:")
                logger.info(self.get_plan_summary(self.current_plan))
                logger.info("\n" + "="*50)
            else:
                logger.info("请输入 y(批准), n(拒绝), 或 m(修改)")
    
    def _modify_plan(self):
        """修改计划"""
        logger.info("\n可修改的内容:")
        logger.info("1. 调整子任务优先级")
        logger.info("2. 修改时间估算")
        logger.info("3. 添加/删除子任务")
        
        choice = input("请选择要修改的内容 (1-3): ").strip()
        
        if choice == "1":
            self._adjust_priorities()
        elif choice == "2":
            self._adjust_time_estimates()
        elif choice == "3":
            self._modify_subtasks()
        else:
            logger.info("无效选择")
    
    def _adjust_priorities(self):
        """调整优先级"""
        logger.info("\n当前子任务:")
        for i, task in enumerate(self.current_plan.subtasks):
            logger.info(f"{i+1}. {task.name} (优先级: {task.priority})")
        
        task_index = input("请选择要调整的任务编号: ").strip()
        if task_index.isdigit() and 1 <= int(task_index) <= len(self.current_plan.subtasks):
            new_priority = input("请输入新的优先级 (1-5): ").strip()
            if new_priority.isdigit() and 1 <= int(new_priority) <= 5:
                self.current_plan.subtasks[int(task_index)-1].priority = int(new_priority)
                logger.info("优先级已更新")
    
    def _adjust_time_estimates(self):
        """调整时间估算"""
        logger.info("\n当前子任务:")
        for i, task in enumerate(self.current_plan.subtasks):
            logger.info(f"{i+1}. {task.name} (预估时间: {task.estimated_time}分钟)")
        
        task_index = input("请选择要调整的任务编号: ").strip()
        if task_index.isdigit() and 1 <= int(task_index) <= len(self.current_plan.subtasks):
            new_time = input("请输入新的预估时间(分钟): ").strip()
            if new_time.isdigit():
                self.current_plan.subtasks[int(task_index)-1].estimated_time = int(new_time)
                # 重新计算总时间
                self.current_plan.estimated_total_time = sum(task.estimated_time for task in self.current_plan.subtasks)
                logger.info("时间估算已更新")
    
    def _modify_subtasks(self):
        """修改子任务"""
        logger.info("\n1. 添加子任务")
        logger.info("2. 删除子任务")
        
        choice = input("请选择操作 (1-2): ").strip()
        
        if choice == "1":
            name = input("子任务名称: ").strip()
            description = input("详细描述: ").strip()
            estimated_time = input("预估时间(分钟): ").strip()
            priority = input("优先级(1-5): ").strip()
            tools = input("需要的工具(用逗号分隔): ").strip()
            criteria = input("成功标准: ").strip()
            
            if name and description:
                new_task = SubTask(
                    id=str(uuid.uuid4()),
                    name=name,
                    description=description,
                    dependencies=[],
                    estimated_time=int(estimated_time) if estimated_time.isdigit() else 15,
                    priority=int(priority) if priority.isdigit() and 1 <= int(priority) <= 5 else 3,
                    tools_needed=[tool.strip() for tool in tools.split(',') if tool.strip()],
                    success_criteria=criteria or "任务完成"
                )
                self.current_plan.subtasks.append(new_task)
                self.current_plan.execution_order.append(new_task.id)
                self.current_plan.estimated_total_time += new_task.estimated_time
                logger.info("子任务已添加")
        
        elif choice == "2":
            logger.info("\n当前子任务:")
            for i, task in enumerate(self.current_plan.subtasks):
                logger.info(f"{i+1}. {task.name}")
            
            task_index = input("请选择要删除的任务编号: ").strip()
            if task_index.isdigit() and 1 <= int(task_index) <= len(self.current_plan.subtasks):
                task_to_remove = self.current_plan.subtasks[int(task_index)-1]
                self.current_plan.subtasks.remove(task_to_remove)
                if task_to_remove.id in self.current_plan.execution_order:
                    self.current_plan.execution_order.remove(task_to_remove.id)
                self.current_plan.estimated_total_time -= task_to_remove.estimated_time
                logger.info("子任务已删除")
