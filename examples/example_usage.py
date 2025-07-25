"""
PyCline包使用示例
演示如何使用pycline生成Python排序算法代码
"""

import asyncio
import os
from pycline.task_manager import TaskManager, WebviewMessage


async def generate_sorting_code():
    """使用PyCline生成Python排序示例代码"""
    
    # 创建输出目录
    output_dir = "./generated_code"
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化TaskManager
    task_manager = TaskManager(output_dir)
    
    print("🚀 开始使用PyCline生成代码...")
    
    # 1. 初始化任务
    task_description = "生成python排序示例代码"
    task_id = await task_manager.init_task(task=task_description)
    print(f"✅ 任务已创建: {task_id}")
    
    # 2. 发送具体需求
    detailed_request = """
请生成Python排序算法示例代码，包括：
1. 冒泡排序 (bubble_sort)
2. 快速排序 (quick_sort)  
3. 归并排序 (merge_sort)
4. 一个测试函数来验证这些排序算法

每个函数都要有详细的注释说明算法原理和时间复杂度。
请将代码保存到sorting_algorithms.py文件中。
"""
    
    message = WebviewMessage(
        type="user_input",
        text=detailed_request
    )
    
    print("🤖 AI正在生成代码...")
    await task_manager.handle_message(message)
    
    # 3. 获取任务状态
    status = await task_manager.get_task_status()
    print(f"📊 任务状态: {status['status']}")
    print(f"💬 对话轮数: {status['conversation_length']}")
    
    # 4. 检查生成的文件
    generated_file = os.path.join(output_dir, "sorting_algorithms.py")
    if os.path.exists(generated_file):
        print(f"✅ 代码已生成: {generated_file}")
        
        # 读取并显示生成的代码
        with open(generated_file, 'r', encoding='utf-8') as f:
            code_content = f.read()
        
        print("\n" + "="*60)
        print("📝 生成的代码内容:")
        print("="*60)
        print(code_content)
        print("="*60)
        
        return code_content
    else:
        print("❌ 未找到生成的代码文件")
        return None

    await task_manager.cleanup()
    print("🧹 资源清理完成")


async def main():
    """主函数"""
    print("🐍 PyCline - Python排序算法代码生成示例")
    print("-" * 50)
    
    # 生成代码
    generated_code = await generate_sorting_code()
    
    print("\n🎉 代码生成成功！")
    print("💡 提示：生成的代码已保存到 ./generated_code/sorting_algorithms.py")
    print("🔧 您可以运行以下命令测试生成的代码：")
    print("   cd generated_code && python sorting_algorithms.py")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
