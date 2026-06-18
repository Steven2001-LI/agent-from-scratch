"""
Day3 · 徒手 ReAct Agent（无框架，目标 <200 行）
=================================================
和 day2 的核心区别（面试必答）：
  - day2：用模型【原生 Function Calling】，模型返回结构化 tool_calls，API 帮你管循环。
  - day3：【不用】原生能力。我们用一段 prompt 教模型按 ReAct 格式输出纯文本：
            Thought:  （推理）
            Action:   工具名
            Action Input: 参数
        然后【我们自己】解析这段文本、执行工具、把结果作为
            Observation: ...
        拼回对话再问一次。如此循环，直到模型输出 Final Answer。
  一句话：ReAct = 把"思考-行动-观察"这个循环用 prompt + 字符串解析手动撑起来。
"""

import os, re, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.deepseek.com")

# ---------------------------------------------------------------------------
# 1) 工具：和 day2 一样是普通 Python 函数。注意这里【没有】JSON Schema，
#    因为模型不靠 schema 调用，而是靠下面 prompt 里的文字描述来"知道"有哪些工具。
# ---------------------------------------------------------------------------
def get_weather(city: str) -> str:
    return f"{city}天气晴朗，气温 25℃"

def calculator(expression: str) -> str:
    return str(eval(expression))          # 学习用，生产别直接 eval

# 工具注册表：名字 -> 函数
TOOLS = {
    "get_weather": get_weather,
    "calculator": calculator,
}

# 给模型看的工具说明（纯文本，会塞进 system prompt）
TOOLS_DESC = """
- get_weather(city): 查询某城市当前天气，参数 city 是城市名，如 北京
- calculator(expression): 计算数学表达式，Python 写法，次方用 **
""".strip()

# ---------------------------------------------------------------------------
# 2) ReAct 提示词模板：这是整个手写 ReAct 的灵魂。
#    它规定了模型【必须】按 Thought/Action/Action Input 的格式逐步输出。
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""你是一个会使用工具的助手。请严格按 ReAct 格式逐步解决问题。

可用工具：
{TOOLS_DESC}

每一步只能输出下面两种格式之一：

(A) 需要调用工具时：
Thought: 你的推理
Action: 工具名（必须是上面列出的之一）
Action Input: 传给工具的参数（get_weather 直接写城市名；calculator 直接写表达式）

(B) 已经能回答时：
Thought: 你的推理
Final Answer: 给用户的最终回答

规则：
- 一次只输出一个 Thought，且最多跟一个 Action 或一个 Final Answer，然后停下，等我把 Observation 给你。
- 不要自己编造 Observation。
"""

# ---------------------------------------------------------------------------
# 3) 解析器：从模型输出的纯文本里抠出 Action / Action Input / Final Answer。
#    这就是"框架替你做、手写要自己写"的那部分。
# ---------------------------------------------------------------------------
def parse(text: str):
    """返回 ('final', 答案) 或 ('action', 工具名, 参数) 或 ('unknown', 原文)"""
    final = re.search(r"Final Answer:\s*(.+)", text, re.S)
    if final:
        return ("final", final.group(1).strip())

    action = re.search(r"Action:\s*(.+)", text)
    action_input = re.search(r"Action Input:\s*(.+)", text)
    if action and action_input:
        return ("action", action.group(1).strip(), action_input.group(1).strip())

    return ("unknown", text.strip())

# ---------------------------------------------------------------------------
# 4) ReAct 主循环  ★★★ 这里是你明早要写的核心，已留好脚手架和提示 ★★★
# ---------------------------------------------------------------------------
def run(question: str, max_steps: int = 6):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for step in range(max_steps):
        # 1) 请求模型；stop=["Observation:"] 让它输出到 Action Input 就停，
        #    把"观察结果"的话语权留给我们的代码（不让它自己脑补 Observation）。
        response = client.chat.completions.create(
            model="deepseek-chat", messages=messages, stop=["Observation:"])
        text = response.choices[0].message.content
        print(f"\n----- Step {step+1} -----\n{text}")

        # 2) 解析模型输出
        result = parse(text)
        kind = result[0]

        # 3) 分支处理
        if kind == "final":
            print(f"\n✅ Final Answer: {result[1]}")
            return result[1]

        elif kind == "action":
            name, arg = result[1], result[2]
            if name not in TOOLS:                       # 校验：没这个工具就把错误当 Observation 喂回去，别崩
                observation = f"错误：没有名为 {name} 的工具，可用工具：{list(TOOLS)}"
            else:
                observation = TOOLS[name](arg)          # 执行工具
            print(f"Observation: {observation}")
            # 关键：把【模型这步输出】和【我们的 Observation】都追加回 messages，再 continue（这就是 ReAct 的"环"）
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user", "content": f"Observation: {observation}"})
            continue

        else:  # unknown：模型没按格式来，纠正一下喂回去
            messages.append({"role": "assistant", "content": text})
            messages.append({"role": "user",
                             "content": "Observation: 格式不对，请严格按 Thought/Action/Action Input 或 Final Answer 输出。"})
            continue

    print("⚠️ 达到最大步数仍未得到 Final Answer（注意死循环/截断边界，W4 会专门处理）")


if __name__ == "__main__":
    run("北京今天天气怎么样？另外帮我算一下 23 * 45 等于多少")

# =============================================================================
# 写完后自检（对应验收标准 "Thought→Action→Observation 可跑"）：
#   1. 能看到多步 Thought/Action，且工具真的被调用、Observation 被拼回。
#   2. 多工具问题（天气 + 计算）能在多步内逐个解决，最后给 Final Answer。
#   3. 思考题（写进对比笔记）：
#      - 为什么 stop=["Observation:"] 很关键？不加会发生什么？
#      - ReAct（纯 prompt 解析）相比 day2 原生 FunctionCalling，
#        优点（任何模型都能用/可解释）和缺点（解析脆弱/格式易崩/更费 token）各是什么？
#      - 这正是 W3 引入 LangGraph 想解决的问题——框架把"状态机+循环+解析"标准化了。
# =============================================================================
