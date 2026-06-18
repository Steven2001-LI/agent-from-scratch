# =============================================================================
# Day2 · 徒手实现 Function Calling（原生工具调用）
# -----------------------------------------------------------------------------
# 一句话本质：
#   Function Calling 不是"模型会调函数"，而是一个由你的代码驱动的循环。
#   模型只负责"决策"（说想调哪个工具、传什么参数），
#   真正"执行"函数的永远是你的代码。
# =============================================================================

# ---- 第 1 段：导入工具 -------------------------------------------------------
import os, json                       # os: 读环境变量（取 API key 用）；json: 处理 JSON，第 ~60 行要用
from dotenv import load_dotenv        # 从 dotenv 库里拿 load_dotenv 这一个函数：读取 .env 文件
from openai import OpenAI             # 从 openai 库里拿 OpenAI 这个"类"（客户端的模具）

# ---- 第 2 段：连接模型 -------------------------------------------------------
load_dotenv()                         # 执行它：把 .env 里的 OPENAI_API_KEY=xxx 加载到环境变量，后面才读得到
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),   # 从环境变量取出密钥（这里其实是 DeepSeek 的 key）
    base_url="https://api.deepseek.com",   # 关键：改 base_url，就把请求发给 DeepSeek，而不是 OpenAI 官方
)

# ---- 第 3 段：定义两个工具函数 ----------------------------------------------
def get_weather(city):                # def=定义函数；city 是参数（输入）
    return f"{city}天气晴朗"          # f"..." 里 {city} 会被替换成传进来的值。假天气，永远晴朗，仅演示

def calculator(expression):
    return str(eval(expression))      # eval 把字符串当代码算（"23*45"→1035）；str() 转字符串
                                      # ★ 坑1：tool 结果回传时 content 必须是字符串，数字会报错，所以 str() 包一下
                                      # （eval 仅学习用，生产危险——能执行任意代码）

# ---- 第 4 段：写工具"说明书"给模型看（最重要）------------------------------
# 为什么要这段：模型【看不见】上面的 Python 函数！它只能看到这段 JSON 描述。
# 你得用 JSON 告诉它：我有哪些工具、每个叫啥、要什么参数。
tools = [                                     # 列表 []，可放多个工具
    {                                         # 工具一：get_weather
        "type": "function",                   # 固定写法：这是个函数工具
        "function": {
            "name": "get_weather",            # 工具名，必须和 Python 函数名对上（后面靠它找函数）
            "description": "查询指定城市的当前天气",  # ★ 模型靠这句话判断"该不该用这个工具"。写烂了就选错工具
            "parameters": {                   # 描述参数
                "type": "object",             # 固定：参数是一组键值
                "properties": {               # 具体有哪些参数
                    "city": {"type": "string", "description": "城市名,如 北京"}
                },
                "required": ["city"]          # city 是必填
            }
        }
    },                                        # ★ 这个逗号！分隔两个工具，漏了语法报错
    {                                         # 工具二：calculator，结构完全一样
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，用 Python 写法，次方用 **",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "计算数学表达式"}  # 参数名 expression，和函数对上
                },
                "required": ["expression"]
            }
        }
    }
]
# 小结：JSON Schema = 模型的"工具菜单"。模型靠 name+description+参数说明，决定调谁、传什么。

# ---- 第 5 段：名字→函数的映射表 --------------------------------------------
# 键是字符串（工具名），值是真正的函数对象。
# 为什么要它：模型只会返回字符串 "get_weather"，没法"运行一个字符串"，
# 用这张表 available["get_weather"] 就能拿到真函数去执行。
# 注意："get_weather"(带引号=字符串) 和 get_weather(不带引号=函数本身) 是两个东西。
available = {"get_weather": get_weather, "calculator": calculator}

# ---- 第 6 段：准备对话 ------------------------------------------------------
# messages = 对话历史列表，每条是字典：role（谁说的）+ content（说了啥）。
# 这题用户一句话需要【两个】工具：查天气 + 算 23*45。
messages = [{"role": "user", "content": "北京天气怎么样？顺便帮我算 23*45"}]

# ---- 第 7 段：核心循环 ------------------------------------------------------
# 为什么要循环：可能"问→调工具→再问→再调→…"，次数不定，靠后面的 break 跳出。
while True:
    # 发请求：带上 messages（历史）和 tools（工具菜单）
    response = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=tools)
    # choices 是候选列表，[0] 取第一个，.message 是回复主体
    msg = response.choices[0].message

    # === 第1圈会走这里 ===
    if msg.tool_calls:                    # 模型没直接回答，而是说"我想调工具"，决策装在 tool_calls 里
        print("tool_calls:", msg.tool_calls)
        messages.append(msg)              # ★ 坑3：必须先把这条"我要调工具"的 assistant 消息存回历史，
                                          #   再存工具结果。协议规定：tool 结果消息必须紧跟带 tool_calls 的 assistant 消息，
                                          #   漏了 API 直接报错。

        for tc in msg.tool_calls:         # tool_calls 可能有多个（这题有俩：天气+计算），逐个处理
            name = tc.function.name       # 模型想调的工具名，如 "get_weather"（字符串）
            args = json.loads(tc.function.arguments)  # ★ 坑1核心：arguments 是 JSON 字符串 '{"city":"北京"}'，
                                                       #   不是字典！json.loads 把它转成真字典 {"city":"北京"}
            print(f"模型调用函数：{name}，参数：{args}")
            result = available[name](**args)  # available[name] 用名字查出真函数；
                                              # **args 把字典拆开当参数传：available["get_weather"](**{"city":"北京"})
                                              #                            == get_weather(city="北京")
                                              # ★ 这一行才是"真正执行"，在你的代码里，跟模型无关
            print(f"执行结果：{result}")
            messages.append({"role": "tool",          # 角色是 tool（工具结果）
                             "tool_call_id": tc.id,   # ★ 坑2：并行调多个工具时，靠这个 id 把"结果"对回"哪次调用"
                             "content": result})       # 内容必须是字符串（呼应前面的 str()）
        continue                          # 工具都执行存好了，回到循环顶，带新历史【再问一次】模型

    # === 第2圈会走这里 ===
    else:                                 # 模型看到工具结果后不再调工具，tool_calls 为空
        print("【模型没调工具，直接回答】")
        print(msg.content)                # msg.content 是最终回答文字，如"北京晴朗，23×45=1035"
        break                             # 跳出 while，结束

# =============================================================================
# 整个流程：
#   你问("天气+计算")
#      ↓
#   [第1圈] 模型说：我要调 get_weather(北京) 和 calculator(23*45)   ← 模型只"决策"
#      ↓   你的代码真正执行这俩函数，拿到 "北京天气晴朗"、"1035"     ← 代码"执行"
#      ↓   把结果塞回 messages
#   [第2圈] 模型看到结果 → 说"北京晴朗，23×45=1035"               ← 模型"总结"
#      ↓
#   break 结束
#
# 三个必记的坑（面试细节分）：
#   坑1 json.loads：arguments 是 JSON 字符串，不是字典，必须 loads 转
#   坑2 tool_call_id：并行调多个工具时，靠它把每个结果对回对应调用
#   坑3 顺序：必须先 append(msg) 再 append tool 结果（tool 消息须紧跟 tool_calls 的 assistant 消息）
#
# 一句话总复习：模型负责"决策"（返回 JSON 说调谁传啥），代码负责"执行"（真正跑函数），
#              结果回传后再问一次，模型才给最终答案。
# =============================================================================
