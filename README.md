# PyCline

[中文版本](README_zh.md) | English Version

PyCline is a Python implementation of Cline (formerly Claude Dev), providing AI-powered code generation and task automation capabilities. It offers a standardized interface compatible with Cline while leveraging the Python ecosystem.

## 🌟 Features

- **AI-Driven Code Generation**: Automatically generate code based on natural language descriptions
- **Cline-Compatible Interface**: 100% interface compatibility with Cline's core APIs
- **Plan & Act Modes**: Support for both planning and execution modes
- **Tool System**: Comprehensive tool system for file operations, command execution, and more
- **Context Management**: Intelligent context optimization and file tracking
- **Multi-Model Support**: Support for various AI models including DeepSeek, Claude, etc.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Required dependencies (see `requirements.txt`)

### Installation

```bash
git clone https://github.com/leonexu/pycline.git
cd pycline
pip install -r requirements.txt
```

### Basic Usage

```python
import asyncio
from core.task_manager import TaskManager
from core.types import WebviewMessage

async def main():
    # Create task manager
    task_manager = TaskManager("./project")
    
    # Initialize task
    task_id = await task_manager.init_task(
        task="Create a Python sorting algorithm example"
    )
    
    # Process user message
    message = WebviewMessage(
        type="user_input",
        text="Generate bubble sort and quick sort algorithms"
    )
    await task_manager.handle_message(message)
    
    # Cleanup
    await task_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 Core Components

### TaskManager
The central component that manages tasks, integrates context management, and coordinates AI interactions.

**Key Methods:**
- `init_task()` - Initialize a new task
- `handle_message()` - Process user messages
- `say()` / `ask()` - Send messages to users
- `execute_tool()` - Execute tools

### ToolExecutor
Handles tool execution with support for:
- File operations (read, write, replace)
- Command execution
- Directory listing
- Auto-approval mechanisms

### Context Management
Intelligent context optimization including:
- File change tracking
- Context truncation
- Memory optimization
- Conversation history management

## 🛠️ Available Tools

- **read_file**: Read file contents
- **write_to_file**: Create or overwrite files
- **replace_in_file**: Replace content in files using SEARCH/REPLACE blocks
- **list_files**: List directory contents
- **execute_command**: Execute shell commands

## 🎯 Plan & Act Modes

### Plan Mode
- Analyze tasks and create execution plans
- Break down complex tasks into subtasks
- Estimate time and dependencies
- AI-driven complexity assessment

### Act Mode
- Execute tasks directly
- AI automatically decides which tools to use
- Real-time code generation and file operations

## 📊 Interface Compatibility

PyCline provides 100% interface compatibility with Cline:

| Cline Interface | PyCline Interface | Status |
|----------------|-------------------|---------|
| `Controller.initTask()` | `init_task()` | ✅ |
| `Controller.handleWebviewMessage()` | `handle_message()` | ✅ |
| `Task.say()` | `say()` | ✅ |
| `Task.ask()` | `ask()` | ✅ |
| `ToolExecutor.executeTool()` | `execute_tool()` | ✅ |

## 🔧 Configuration

Configure AI providers in `core/config.py`:

```python
ai_config = AIConfig(
    provider="deepseek",
    model="deepseek-chat",
    temperature=0.7,
    max_tokens=4000
)
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Architecture Overview](docs/04_pycline/01-overview.md)
- [Core Architecture](docs/04_pycline/02-core-architecture.md)
- [Context Management](docs/04_pycline/03-context-management.md)
- [Plan Mode](docs/04_pycline/04-plan-mode.md)
- [Tool System](docs/04_pycline/05-tool-system.md)
- [Cline Mapping](docs/04_pycline/06-cline-mapping.md)

## 🧪 Testing

Run the demo to test functionality:

```bash
python demo.py
```

Test AI code generation:

```bash
python test_ai_generation.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Cline](https://github.com/cline/cline) - The original inspiration and interface specification
- [LangChain](https://github.com/langchain-ai/langchain) - For AI integration capabilities
- [LangGraph](https://github.com/langchain-ai/langgraph) - For agent workflow management

## 📞 Support

If you encounter any issues or have questions:

1. Check the [documentation](docs/)
2. Search existing [issues](https://github.com/your-repo/pycline/issues)
3. Create a new issue if needed

---

**PyCline** - Bringing Cline's power to the Python ecosystem! 🐍✨
