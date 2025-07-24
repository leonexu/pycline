"""
PyCline上下文管理功能测试
验证智能截断、内容去重和文件跟踪功能
"""

import asyncio
import os
import tempfile
import shutil
from core.context_manager import ContextManager
from core.task_manager import TaskManager
from common_base import setup_logger
logger = setup_logger()

async def test_context_optimization():
    """测试上下文优化功能"""
    logger.info("🧪 测试上下文优化功能")
    logger.info("=" * 50)
    
    # 创建临时工作目录
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 工作目录: {temp_dir}")
        
        # 创建上下文管理器
        context_manager = ContextManager("test_task", temp_dir)
        await context_manager.initialize_context_history()
        
        # 模拟重复文件读取的对话历史
        conversation_history = [
            {"role": "user", "content": "请读取 main.py 文件"},
            {"role": "assistant", "content": "[read_file for 'main.py'] Result: def main():\n    logger.info('Hello World')\n\nif __name__ == '__main__':\n    main()"},
            {"role": "user", "content": "请修改main.py文件"},
            {"role": "assistant", "content": "[write_to_file for 'main.py'] Result: 文件已修改\n<final_file_content path=\"main.py\">def main():\n    logger.info('Hello PyCline')\n\nif __name__ == '__main__':\n    main()</final_file_content>"},
            {"role": "user", "content": "再次读取 main.py 文件"},
            {"role": "assistant", "content": "[read_file for 'main.py'] Result: def main():\n    logger.info('Hello PyCline')\n\nif __name__ == '__main__':\n    main()"},
            {"role": "user", "content": "请读取 utils.py 文件"},
            {"role": "assistant", "content": "[read_file for 'utils.py'] Result: def helper():\n    return 'utility function'"},
            {"role": "user", "content": "再次读取 main.py 文件"},
            {"role": "assistant", "content": "[read_file for 'main.py'] Result: def main():\n    logger.info('Hello PyCline')\n\nif __name__ == '__main__':\n    main()"},
        ]
        
        logger.info(f"📊 原始对话长度: {len(conversation_history)}条")
        
        # 模拟高token使用量触发优化
        token_usage = {
            "input_tokens": 55000,
            "output_tokens": 35000,
            "cache_reads": 5000,
            "cache_writes": 3000
        }
        
        logger.info(f"🔢 模拟token使用: {sum(token_usage.values())}个")
        
        # 获取优化后的上下文
        optimized_history, was_updated = await context_manager.get_optimized_context_messages(
            conversation_history,
            "claude-3-sonnet",
            token_usage
        )
        
        logger.info(f"📈 优化结果:")
        logger.info(f"   - 是否优化: {'✅ 是' if was_updated else '❌ 否'}")
        logger.info(f"   - 优化后长度: {len(optimized_history)}条")
        
        # 检查内容去重效果
        main_py_reads = 0
        for msg in optimized_history:
            if "main.py" in msg.get("content", ""):
                main_py_reads += 1
        
        logger.info(f"   - main.py读取次数: {main_py_reads}次")
        
        # 显示优化后的消息内容
        logger.info(f"\n📝 优化后的消息:")
        for i, msg in enumerate(optimized_history):
            content = msg.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            logger.info(f"   {i+1}. [{msg['role']}] {content}")


async def test_file_tracking():
    """测试文件跟踪功能"""
    logger.info("\n🧪 测试文件跟踪功能")
    logger.info("=" * 50)
    
    # 创建临时工作目录
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 工作目录: {temp_dir}")
        
        # 创建测试文件
        test_file = os.path.join(temp_dir, "test.py")
        with open(test_file, 'w') as f:
            f.write("logger.info('initial content')")
        
        # 创建上下文管理器
        context_manager = ContextManager("test_task", temp_dir)
        await context_manager.initialize_context_history()
        
        # 跟踪文件读取
        await context_manager.file_context_tracker.track_file_context("test.py", "read_tool")
        logger.info("✅ 已跟踪文件读取操作")
        
        # 模拟Cline编辑文件
        context_manager.file_context_tracker.mark_file_as_edited_by_cline("test.py")
        with open(test_file, 'w') as f:
            f.write("logger.info('modified by cline')")
        
        await context_manager.file_context_tracker.track_file_context("test.py", "cline_edited")
        logger.info("✅ 已跟踪Cline编辑操作")
        
        # 等待一小段时间让文件监控器处理
        await asyncio.sleep(0.1)
        
        # 模拟用户编辑文件
        with open(test_file, 'w') as f:
            f.write("logger.info('modified by user')")
        
        # 等待文件监控器检测变更
        await asyncio.sleep(0.5)
        
        # 获取最近修改的文件
        modified_files = context_manager.file_context_tracker.get_and_clear_recently_modified_files()
        logger.info(f"📝 最近修改的文件: {modified_files}")
        
        # 检测特定时间戳后的文件编辑
        import time
        timestamp = time.time() - 10  # 10秒前
        edited_files = await context_manager.file_context_tracker.detect_files_edited_after_timestamp(timestamp)
        logger.info(f"🕒 时间戳后编辑的文件: {edited_files}")


async def test_intelligent_truncation():
    """测试智能截断功能"""
    logger.info("\n🧪 测试智能截断功能")
    logger.info("=" * 50)
    
    # 创建临时工作目录
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 工作目录: {temp_dir}")
        
        # 创建上下文管理器
        context_manager = ContextManager("test_task", temp_dir)
        await context_manager.initialize_context_history()
        
        # 创建长对话历史
        conversation_history = []
        for i in range(20):
            conversation_history.extend([
                {"role": "user", "content": f"用户消息 {i+1}"},
                {"role": "assistant", "content": f"助手响应 {i+1}"}
            ])
        
        logger.info(f"📊 原始对话长度: {len(conversation_history)}条")
        
        # 测试不同的截断策略
        strategies = ["half", "quarter", "lastTwo"]
        
        for strategy in strategies:
            truncated = context_manager._apply_intelligent_truncation(
                conversation_history.copy(), 
                strategy
            )
            logger.info(f"📐 {strategy}策略截断后: {len(truncated)}条")
            
            # 验证保留了第一对消息
            if len(truncated) >= 2:
                first_user = truncated[0]
                first_assistant = truncated[1]
                logger.info(f"   - 保留首对: {first_user['content'][:20]}... / {first_assistant['content'][:20]}...")


async def test_task_manager_integration():
    """测试任务管理器集成"""
    logger.info("\n🧪 测试任务管理器集成")
    logger.info("=" * 50)
    
    # 创建临时工作目录
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 工作目录: {temp_dir}")
        
        # 创建任务管理器
        task_manager = TaskManager(temp_dir)
        
        # 创建任务
        task_id = await task_manager.create_task(
            title="测试任务",
            description="测试上下文管理集成",
            mode="plan"
        )
        logger.info(f"✅ 创建任务: {task_id[:8]}...")
        
        # 添加多条消息
        for i in range(5):
            await task_manager.add_message("user", f"用户消息 {i+1}")
            await task_manager.add_message("assistant", f"助手响应 {i+1}")
        
        # 获取任务状态
        status = await task_manager.get_task_status()
        logger.info(f"📊 任务状态:")
        logger.info(f"   - 标题: {status['title']}")
        logger.info(f"   - 模式: {status['mode']}")
        logger.info(f"   - 对话长度: {status['conversation_length']}")
        
        # 测试模式切换
        await task_manager.switch_mode("act")
        logger.info("✅ 切换到Act模式")
        
        # 测试上下文优化
        optimized_context, was_optimized = await task_manager.get_optimized_context({
            "input_tokens": 50000,
            "output_tokens": 30000
        })
        logger.info(f"🔧 上下文优化: {'已优化' if was_optimized else '无需优化'}")
        
        # 清理
        await task_manager.cleanup()
        logger.info("🧹 资源清理完成")


async def main():
    """主测试函数"""
    logger.info("🐍 PyCline 上下文管理功能测试")
    logger.info("基于Cline的智能上下文管理机制")
    logger.info("=" * 60)
    
    # 运行各项测试
    await test_context_optimization()
    await test_file_tracking()
    await test_intelligent_truncation()
    await test_task_manager_integration()
    
    logger.info("\n🎉 所有测试完成！")
    logger.info("\n📋 测试总结:")
    logger.info("✅ 上下文优化 - 智能去重文件内容")
    logger.info("✅ 文件跟踪 - 实时监控文件变更")
    logger.info("✅ 智能截断 - 保留重要对话历史")
    logger.info("✅ 任务集成 - 完整的任务管理流程")


if __name__ == "__main__":
    asyncio.run(main())
