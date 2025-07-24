"""
测试PyCline的AI代码生成功能
"""

import asyncio
import os
from core.task_manager import TaskManager
from core.types import WebviewMessage, ClineSay
from utils import setup_logger
logger = setup_logger()

async def test_ai_code_generation():
    """测试AI自动生成代码功能"""
    
    # 创建工作目录
    work_dir = "./results/test_sorting"
    os.makedirs(work_dir, exist_ok=True)
    
    # 创建任务管理器
    task_manager = TaskManager(work_dir)
    
    logger.info("=== 测试PyCline AI代码生成 ===\n")
    
    # 1. 初始化任务
    logger.info("1. 初始化任务...")
    task_id = await task_manager.init_task(
        task="请生成一个python排序示例"
    )
    logger.info(f"   任务ID: {task_id}")
    
    # 2. 发送详细需求给AI
    logger.info("\n2. 发送需求给AI...")
    user_message = WebviewMessage(
        type="user_input",
        text="请生成一个Python排序算法示例，包含冒泡排序和快速排序，并创建一个名为sorting.py的文件"
    )
    
    # 处理消息，让AI生成代码
    await task_manager.handle_message(user_message)
    
    # 3. 检查生成的文件
    logger.info("\n3. 检查生成的文件...")
    list_message = WebviewMessage(
        type="user_input",
        text="请列出当前目录的所有文件"
    )
    await task_manager.handle_message(list_message)
    
    # 4. 如果有生成的文件，读取内容
    sorting_file = os.path.join(work_dir, "sorting.py")
    if os.path.exists(sorting_file):
        logger.info(f"\n4. 成功生成文件: {sorting_file}")
        with open(sorting_file, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info("文件内容预览:")
        logger.info("=" * 50)
        logger.info(content[:500] + "..." if len(content) > 500 else content)
        logger.info("=" * 50)
    else:
        logger.info("\n4. 未找到生成的文件，可能AI没有调用工具")
    
    # 5. 获取对话历史
    logger.info("\n5. 对话历史:")
    messages = task_manager.get_cline_messages()
    for i, msg in enumerate(messages[-5:], 1):  # 只显示最后5条消息
        logger.info(f"   {i}. [{msg.type}] {msg.text[:100]}...")
    
    logger.info(f"\n总共 {len(messages)} 条消息")
    
    await task_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_ai_code_generation())
