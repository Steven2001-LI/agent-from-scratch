import os, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.deepseek.com")

def get_weather(city):
    return f"{city}天气晴朗"

def calculator(expression):
    return str(eval(expression))

tools = [
    {                                    # ← 工具一：get_weather，完整独立
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名,如 北京"}
                },
                "required": ["city"]
            }
        }
    },                                   # ← 这个逗号！分隔两个工具
    {                                    # ← 工具二：calculator，又是完整的一整套
        "type": "function",
        "function": {
            "name": "calculator",              # 填 calculator
            "description": "计算数学表达式，用 Python 写法，次方用 **",        # 填：计算数学表达式，用 Python 写法，次方用 **
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "计算数学表达式"}   # 参数名填 expression
                },
                "required": ["expression"]      # 填 expression
            }
        }
    }
]

available = {"get_weather": get_weather, "calculator": calculator}

messages = [{"role": "user", "content": "北京天气怎么样？顺便帮我算 23*45"}]

while True:
    response = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=tools)
    msg = response.choices[0].message
    
    if msg.tool_calls:
        print("tool_calls:", msg.tool_calls)
        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"模型调用函数：{name}，参数：{args}")
            result = available[name](**args)
            print(f"执行结果：{result}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        continue
    else:
        print("【模型没调工具，直接回答】")
        print(msg.content)
        break

# "Function Calling 是一个循环。第一次请求带上工具定义,模型不直接回答,而是返回 tool_calls,告诉我要调哪个工具、传什么参数——但它自己不执行。我的代码解析出来,真正执行函数,把结果以 role=tool 
#的消息追加回 messages,再请求一次。这次模型看到了工具结果,就能给出最终回答,finish_reason 变回 stop,循环结束。核心是:模型负责决策,我的代码负责执行。"
# Tool Calls：不是模型“会”了这个工具，而是模型能识别“应该”用这个工具。
# 它的能力不是“理解代码”，而是根据工具的“名称” + “描述” + “参数 Schema” ，
# 匹配用户意图（如“查天气”），然后生成一个结构化的 JSON，告诉你：“我觉得应该用 get_weather(city='北京')”。
# 代码真正调用 Python 函数执行，这块纯粹是客户端的逻辑，和模型没半毛钱关系。
# 总结：模型只负责“输出 JSON 格式的工具调用指令”；实际执行靠咱们代码来写。