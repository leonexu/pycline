import os  
from langchain_deepseek import ChatDeepSeek  
from langchain_core.tools import tool  
from langgraph.prebuilt import create_react_agent  
  
# 设置API密钥  
os.environ["DEEPSEEK_API_KEY"] = os.getenv("DEEPSEEK_API_KEY")
  
# 创建DeepSeek模型  
llm = ChatDeepSeek(  
    model="deepseek-chat",  
    temperature=0,  
    max_tokens=None  
)  
  
# 创建工具  
@tool  
def add(a: int, b: int) -> int:  
    """将两个整数相加"""  
    return a + b  
  
@tool  
def multiply(a: int, b: int) -> int:  
    """将两个整数相乘"""  
    return a * b  
  
tools = [add, multiply]  
  
# 创建Agent  
agent = create_react_agent(llm, tools, prompt="你是一个数学助手，可以进行加法和乘法运算。")  
  
# 测试Agent  
result = agent.invoke({"messages": [("user", "请计算15加上28，然后将结果乘以2")]})  
print(result['messages'][-1].content)
