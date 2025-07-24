# PyCline

中文版本 | [English Version](README.md)

PyCline 是 Cline（原 Claude Dev）的 Python 实现，提供 AI 驱动的代码生成和任务自动化功能。它提供与 Cline 兼容的标准化接口，同时充分利用 Python 生态系统的优势。

## 🌟 特性

- **AI 驱动的代码生成**：基于自然语言描述自动生成代码
- **Cline 兼容接口**：与 Cline 核心 API 100% 接口兼容
- **Plan & Act 模式**：支持规划和执行两种模式
- **工具系统**：完整的工具系统，支持文件操作、命令执行等
- **上下文管理**：智能上下文优化和文件跟踪
- **多模型支持**：支持 DeepSeek、Claude 等多种 AI 模型

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 相关依赖（见 `requirements.txt`）

### 安装

```bash
git clone https://github.com/leonexu/pycline.git
cd pycline
pip install -r requirements.txt
```

### 基本使用

```python
import asyncio
from core.task_manager import TaskManager
from core.types import WebviewMessage

async def main():
    # 创建任务管理器
    task_manager = TaskManager("./project")
    
    # 初始化任务
    task_id = await task_manager.init_task(
        task="创建一个Python排序算法示例"
    )
    
    # 处理用户消息
    message = WebviewMessage(
        type="user_input",
        text="生成冒泡排序和快速排序算法"
    )
    await task_manager.handle_message(message)
    
    # 清理资源
    await task_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 核心组件

### TaskManager（任务管理器）
管理任务、集成上下文管理并协调 AI 交互的核心组件。

**主要方法：**
- `init_task()` - 初始化新任务
- `handle_message()` - 处理用户消息
- `say()` / `ask()` - 向用户发送消息
- `execute_tool()` - 执行工具

### ToolExecutor（工具执行器）
处理工具执行，支持：
- 文件操作（读取、写入、替换）
- 命令执行
- 目录列表
- 自动审批机制

### 上下文管理
智能上下文优化，包括：
- 文件变更跟踪
- 上下文截断
- 内存优化
- 对话历史管理

## 🛠️ 可用工具

- **read_file**：读取文件内容
- **write_to_file**：创建或覆盖文件
- **replace_in_file**：使用 SEARCH/REPLACE 块替换文件内容
- **list_files**：列出目录内容
- **execute_command**：执行 shell 命令

## 🎯 Plan & Act 模式

### Plan 模式（规划模式）
- 分析任务并创建执行计划
- 将复杂任务分解为子任务
- 估算时间和依赖关系
- AI 驱动的复杂度评估

### Act 模式（执行模式）
- 直接执行任务
- AI 自动决定使用哪些工具
- 实时代码生成和文件操作

## 📊 接口兼容性

PyCline 提供与 Cline 100% 的接口兼容性：

| Cline 接口 | PyCline 接口 | 状态 |
|-----------|-------------|------|
| `Controller.initTask()` | `init_task()` | ✅ |
| `Controller.handleWebviewMessage()` | `handle_message()` | ✅ |
| `Task.say()` | `say()` | ✅ |
| `Task.ask()` | `ask()` | ✅ |
| `ToolExecutor.executeTool()` | `execute_tool()` | ✅ |

## 🔧 配置

在 `core/config.py` 中配置 AI 提供者：

```python
ai_config = AIConfig(
    provider="deepseek",
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=4000
)
```

## 📚 文档

`docs/` 目录中提供了完整的文档：

- [架构概览](docs/04_pycline/01-overview.md)
- [核心架构](docs/04_pycline/02-core-architecture.md)
- [上下文管理](docs/04_pycline/03-context-management.md)
- [Plan 模式](docs/04_pycline/04-plan-mode.md)
- [工具系统](docs/04_pycline/05-tool-system.md)
- [Cline 映射关系](docs/04_pycline/06-cline-mapping.md)

## 🧪 测试

运行演示来测试功能：

```bash
python demo.py
```

测试 AI 代码生成：

```bash
python test_ai_generation.py
```

## 🎯 使用场景

### 代码生成
```bash
# 生成排序算法
python -c "
import asyncio
from core.task_manager import TaskManager
from core.types import WebviewMessage

async def generate_code():
    task_manager = TaskManager('./output')
    await task_manager.init_task(task='生成Python排序算法')
    message = WebviewMessage(type='user_input', text='请生成冒泡排序和快速排序')
    await task_manager.handle_message(message)
    await task_manager.cleanup()

asyncio.run(generate_code())
"
```

### 项目创建
```python
# 创建Web应用项目
task_manager = TaskManager("./my_web_app")
await task_manager.init_task(task="创建一个Flask Web应用")
await task_manager.handle_message(WebviewMessage(
    type="user_input", 
    text="创建包含用户认证和数据库的Flask应用"
))
```

### 代码重构
```python
# 代码重构
await task_manager.init_task(task="重构现有代码")
await task_manager.handle_message(WebviewMessage(
    type="user_input",
    text="将这个单体应用重构为微服务架构"
))
```

## 🔄 工作流程

1. **任务初始化**：使用 `init_task()` 创建新任务
2. **模式选择**：选择 Plan 模式进行规划或 Act 模式直接执行
3. **消息处理**：通过 `handle_message()` 处理用户输入
4. **AI 处理**：AI 分析需求并自动选择合适的工具
5. **工具执行**：自动执行文件操作、命令等
6. **结果反馈**：通过 `say()` 向用户反馈执行结果

## 🤝 贡献

1. Fork 仓库
2. 创建功能分支
3. 进行更改
4. 添加测试（如适用）
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [Cline](https://github.com/cline/cline) - 原始灵感和接口规范
- [LangChain](https://github.com/langchain-ai/langchain) - AI 集成能力
- [LangGraph](https://github.com/langchain-ai/langgraph) - 智能体工作流管理

## 📞 支持

如果遇到任何问题或有疑问：

1. 查看[文档](docs/)
2. 搜索现有[问题](https://github.com/your-repo/pycline/issues)
3. 如需要可创建新问题

## 🚀 路线图

### 已完成
- ✅ 核心架构设计
- ✅ Cline 接口兼容
- ✅ 基础工具系统
- ✅ 上下文管理
- ✅ Plan & Act 模式

### 进行中
- 🔄 MCP 服务器支持
- 🔄 浏览器自动化工具
- 🔄 更多 AI 模型集成

### 计划中
- 📋 图形用户界面
- 📋 插件系统
- 📋 云端部署支持
- 📋 团队协作功能

---

**PyCline** - 将 Cline 的强大功能带入 Python 生态系统！🐍✨
