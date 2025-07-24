"""
Test PyCline's AI code generation functionality
"""

import asyncio
import os
from core.task_manager import TaskManager
from core.types import WebviewMessage, ClineSay
from utils import setup_logger
logger = setup_logger()

async def test_ai_code_generation():
    """Test AI automatic code generation functionality"""
    
    # Create working directory
    work_dir = "./results/test_sorting"
    os.makedirs(work_dir, exist_ok=True)
    
    # Create task manager
    task_manager = TaskManager(work_dir)
    
    logger.info("=== Testing PyCline AI Code Generation ===\n")
    
    # 1. Initialize task
    logger.info("1. Initializing task...")
    task_id = await task_manager.init_task(
        task="Please generate a Python sorting example"
    )
    logger.info(f"   Task ID: {task_id}")
    
    # 2. Send detailed requirements to AI
    logger.info("\n2. Sending requirements to AI...")
    user_message = WebviewMessage(
        type="user_input",
        text="Please generate a Python sorting algorithm example, including bubble sort and quick sort, and create a file named sorting.py"
    )
    
    # Process message to let AI generate code
    await task_manager.handle_message(user_message)
    
    # 3. Check generated files
    logger.info("\n3. Checking generated files...")
    list_message = WebviewMessage(
        type="user_input",
        text="Please list all files in the current directory"
    )
    await task_manager.handle_message(list_message)
    
    # 4. If files are generated, read content
    sorting_file = os.path.join(work_dir, "sorting.py")
    if os.path.exists(sorting_file):
        logger.info(f"\n4. Successfully generated file: {sorting_file}")
        with open(sorting_file, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info("File content preview:")
        logger.info("=" * 50)
        logger.info(content[:500] + "..." if len(content) > 500 else content)
        logger.info("=" * 50)
    else:
        logger.info("\n4. Generated file not found, AI may not have called tools")
    
    # 5. Get conversation history
    logger.info("\n5. Conversation history:")
    messages = task_manager.get_cline_messages()
    for i, msg in enumerate(messages[-5:], 1):  # Only show last 5 messages
        logger.info(f"   {i}. [{msg.type}] {msg.text[:100]}...")
    
    logger.info(f"\nTotal {len(messages)} messages")
    
    await task_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_ai_code_generation())
