import asyncio
from core.task_manager import TaskManager
from core.types import WebviewMessage

# 创建任务管理器
work_dir = "./results/project"
task_manager = TaskManager(work_dir)

async def main():
    # 使用Cline标准接口初始化任务
    task_id = await task_manager.init_task(
        task="创建一个Web应用",
        images=None,
        files=None
    )

    # 处理用户消息
    message = WebviewMessage(
        type="user_input",
        text="请开始开发"
    )
    await task_manager.handle_message(message)


# 使用示例 - 标准化接口
async def example_usage():
    """使用标准化Cline接口的示例"""
    from core.types import WebviewMessage, ChatSettings, ClineSay, ClineAsk, ToolUse
    
    # 创建任务管理器
    task_manager = TaskManager(work_dir)
    
    print("=== PyCline标准化接口演示 ===\n")
    
    # 1. 使用标准化接口初始化任务
    print("1. 初始化任务...")
    task_id = await task_manager.init_task(
        task="创建一个简单的Web应用，包含前端和后端"
    )
    print(f"   任务ID: {task_id}")
    
    # 2. 获取当前模式
    current_mode = await task_manager.get_current_mode()
    print(f"   当前模式: {current_mode}")
    
    # 3. 切换到Plan模式
    print("\n2. 切换到Plan模式...")
    await task_manager.toggle_plan_act_mode(ChatSettings(mode="plan"))
    current_mode = await task_manager.get_current_mode()
    print(f"   当前模式: {current_mode}")
    
    # 4. 使用Say消息
    print("\n3. 发送Say消息...")
    await task_manager.say(
        ClineSay.TEXT,
        "开始分析项目需求并制定开发计划"
    )
    
    # 5. 处理用户消息
    print("\n4. 处理用户消息...")
    message1 = WebviewMessage(
        type="user_input",
        text="请详细分析Web应用的技术栈选择"
    )
    await task_manager.handle_message(message1)
    
    # 6. 使用Ask消息
    print("\n5. 发送Ask消息...")
    response = await task_manager.ask(
        ClineAsk.FOLLOWUP,
        "是否需要添加数据库支持？"
    )
    print(f"   用户响应: {response.response}")
    
    # 7. 切换到Act模式
    print("\n6. 切换到Act模式...")
    await task_manager.toggle_plan_act_mode(ChatSettings(mode="act"))
    current_mode = await task_manager.get_current_mode()
    print(f"   当前模式: {current_mode}")
    
    # 8. 执行工具
    print("\n7. 执行工具...")
    tool_use = ToolUse(
        name="write_to_file",
        params={
            "path": "index.html",
            "content": """<!DOCTYPE html>
<html>
<head>
    <title>My Web App</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>这是一个简单的Web应用</p>
</body>
</html>"""
        }
    )
    await task_manager.execute_tool(tool_use)
    
    # 9. 获取Cline消息
    print("\n8. 获取消息历史...")
    cline_messages = task_manager.get_cline_messages()
    print(f"   消息数量: {len(cline_messages)}")
    
    # 10. 获取API对话历史
    api_history = task_manager.get_api_conversation_history()
    print(f"   API对话历史: {len(api_history)}条")
    
    # 11. 获取任务状态
    print("\n9. 获取任务状态...")
    status = await task_manager.get_task_status()
    print(f"   任务状态: {status['status']}")
    print(f"   对话长度: {status['conversation_length']}")
    print(f"   创建时间: {status['created_at']}")
    
    # 12. 清理任务
    print("\n10. 清理任务...")
    await task_manager.clear_task()
    await task_manager.cleanup()
    
    print("\n=== 演示完成 ===")


# 工具执行器演示
async def tool_executor_demo():
    """工具执行器演示"""
    from core.tool_executor import ToolExecutor
    from core.types import ToolUse
    
    print("\n=== 工具执行器演示 ===\n")
    
    # 创建工具执行器
    tool_executor = ToolExecutor(work_dir)
    
    # 1. 获取可用工具
    print("1. 可用工具:")
    tools = tool_executor.get_available_tools()
    for tool in tools:
        description = tool_executor.get_tool_description(tool)
        print(f"   - {tool}: {description}")
    
    # 2. 执行读取文件工具
    print("\n2. 执行读取文件工具...")
    read_tool = ToolUse(
        name="read_file",
        params={"path": "../../demo.py"}  # 相对于test_project目录
    )
    await tool_executor.execute_tool(read_tool)
    
    # 3. 执行列出文件工具
    print("\n3. 执行列出文件工具...")
    list_tool = ToolUse(
        name="list_files",
        params={"path": ".", "recursive": "false"}
    )
    await tool_executor.execute_tool(list_tool)
    
    print("\n=== 工具执行器演示完成 ===")


# 完整功能演示
async def full_feature_demo():
    """完整功能演示 - 展示所有标准化接口"""
    from core.types import WebviewMessage, ChatSettings, ClineSay, ClineAsk, ToolUse
    
    print("\n=== 完整功能演示 ===\n")
    
    task_manager = TaskManager(work_dir)
    
    # 1. 创建任务
    print("1. 创建任务...")
    task_id = await task_manager.init_task(task="完整功能测试任务")
    print(f"   任务ID: {task_id}")
    
    # 2. 发送消息
    print("2. 发送Say消息...")
    await task_manager.say(ClineSay.TEXT, "任务已创建，开始处理")
    
    # 3. 处理用户输入
    print("3. 处理用户输入...")
    message = WebviewMessage(type="user_input", text="请创建一个简单的Python脚本")
    await task_manager.handle_message(message)
    
    # 4. 执行工具
    print("4. 执行工具...")
    tool_use = ToolUse(
        name="write_to_file",
        params={
            "path": "hello.py",
            "content": "print('Hello, PyCline!')\nprint('标准化接口测试成功')"
        }
    )
    await task_manager.execute_tool(tool_use)
    
    # 5. 获取消息历史
    print("5. 获取消息历史...")
    messages = task_manager.get_cline_messages()
    print(f"   消息数量: {len(messages)}")
    
    # 6. 获取任务状态
    print("6. 获取任务状态...")
    status = await task_manager.get_task_status()
    print(f"   任务状态: {status['status']}")
    print(f"   对话长度: {status['conversation_length']}")
    
    # 7. 清理
    print("7. 清理任务...")
    await task_manager.clear_task()
    await task_manager.cleanup()
    
    print("\n=== 完整功能演示完成 ===")


if __name__ == "__main__":
    asyncio.run(example_usage())
    asyncio.run(full_feature_demo())
    asyncio.run(tool_executor_demo())
    # asyncio.run(main())
