from langchain_core.tools import StructuredTool  
# 假设有一个类定义在其他文件中  
class Calculator:  
    def __init__(self):  
        self.history = []  
      
    def add(self, a: int, b: int) -> int:  
        """将两个数相加"""  
        result = a + b  
        self.history.append(f"{a} + {b} = {result}")  
        return result  
      
    def multiply(self, a: int, b: int) -> int:  
        """将两个数相乘"""  
        result = a * b  
        self.history.append(f"{a} * {b} = {result}")  
        return result  
  
calc = Calculator()  

# 直接将类方法转换为工具  
add_tool = StructuredTool.from_function(  
    func=calc.add,  
    name="calculator_add",  
    description="使用计算器进行加法运算"  
)  
  
multiply_tool = StructuredTool.from_function(  
    func=calc.multiply,  
    name="calculator_multiply",   
    description="使用计算器进行乘法运算"  
)


from langchain_deepseek import ChatDeepSeek  
  
llm = ChatDeepSeek(model="deepseek-chat", temperature=0)  
tools = [add_tool, multiply_tool]  
llm_with_tools = llm.bind_tools(tools)  
  
# 测试工具调用  
result = llm_with_tools.invoke("计算15加上28等于多少？")  
print(result.tool_calls)
