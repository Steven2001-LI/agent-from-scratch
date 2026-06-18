"""
Day4 · 多轮记忆三方案对比（完整历史 / 滑动窗口 / 摘要压缩）
=================================================================
承接 day1 的核心结论：LLM 无状态，记忆 = 客户端把 messages 累加出来的。
代价你也亲眼见过：messages 越长 → prompt_tokens 单调增长 → 越贵，且迟早撞上
模型的上下文窗口上限（超了直接报错或被截断）。

day4 要解决的就是这个矛盾：怎么在「记得住」和「不爆 token」之间取舍。三种主流方案：

  1) 完整历史 full   ：每次把全部历史发过去。最简单、记得最全，但 token 无上限增长。
  2) 滑动窗口 window ：只发 system + 最近 k 条。token 恒定可控，但会「忘掉」早期信息。
  3) 摘要压缩 summary：历史一长，就让模型把旧消息压成一段摘要，再带摘要 + 最近几条。
                       折中：旧信息以「概要」形式留住，token 也不爆。

本文件用同一段【脚本化多轮对话】分别跑三种方案，打印每轮 prompt_tokens 做对比，
让你亲眼看到三者的 token 曲线差异。★ 核心 TODO 已留好脚手架。
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.deepseek.com")


def chat(messages):
    """发一次请求，返回 (回复文本, prompt_tokens)。三种方案都复用它。"""
    resp = client.chat.completions.create(model="deepseek-chat", messages=messages)
    return resp.choices[0].message.content, resp.usage.prompt_tokens


# ---------------------------------------------------------------------------
# 方案 1：完整历史 —— 基准线，最简单
# ---------------------------------------------------------------------------
def build_full(history):
    """原样返回全部历史。"""
    return history


# ---------------------------------------------------------------------------
# 方案 2：滑动窗口 —— 只留 system + 最近 k 条
# ---------------------------------------------------------------------------
def build_window(history, k=4):
    """保留第一条 system，再接最近 k 条对话消息。"""
    # history[0] 是 system，永远保留；history[1:] 是真正的对话，取最后 k 条
    return [history[0]] + history[1:][-k:]


# ---------------------------------------------------------------------------
# 方案 3：摘要压缩 —— 历史超阈值就把旧消息压成一段摘要
# ---------------------------------------------------------------------------
def build_summary(history, summary, threshold=6):
    """
    返回 (要发送的 messages, 新的 summary)。
    思路：
      - 历史不长（<= threshold 条）：还不值得压缩，原样发，summary 不变。
      - 历史太长：把「较早的那批消息」交给模型，让它压成一段话当 summary，
        然后只发 [system] + [一条带 summary 的消息] + [最近几条]。
    """
    # a) 历史还不长，不值得压缩，原样发
    if len(history) <= threshold:
        return build_full(history), summary

    # b) 太长：把较早的消息压成摘要（跳过 system，保留最近 2 条不压）
    old = history[1:-2]
    text = "\n".join(f"{m['role']}: {m['content']}" for m in old)
    prompt = "请把下面这段对话压成一段简短摘要，保留关键事实（如人名、目标、已确认的结论）：\n" + text
    new_summary, _ = chat([{"role": "user", "content": prompt}])

    to_send = (
        [history[0]]
        + [{"role": "system", "content": f"前情摘要：{new_summary}"}]
        + history[-2:]
    )
    return to_send, new_summary


# ---------------------------------------------------------------------------
# 驱动：用同一段对话分别跑三种方案，对比每轮 prompt_tokens
# ---------------------------------------------------------------------------
# 脚本化的用户提问（模拟多轮，故意让对话变长）
SCRIPT = [
    "你好，我叫小李，今年在准备秋招，目标是做 AI 应用开发。",
    "我比较擅长 Python，最近在手写 Agent。",
    "帮我用一句话总结什么是 Function Calling。",
    "那 ReAct 和它的区别是什么？",
    "我刚才说我叫什么名字来着？",   # ← 考点：滑动窗口可能已经忘了
    "再帮我推荐两个秋招要准备的项目方向。",
]


def run(strategy: str):
    print(f"\n========== 方案：{strategy} ==========")
    history = [{"role": "system", "content": "你是一个简洁的助手，回答尽量短。"}]
    summary = ""

    for turn, user_msg in enumerate(SCRIPT, 1):
        history.append({"role": "user", "content": user_msg})

        # 根据策略决定「这次实际发给模型的 messages」
        if strategy == "full":
            to_send = build_full(history)
        elif strategy == "window":
            to_send = build_window(history, k=4)
        elif strategy == "summary":
            to_send, summary = build_summary(history, summary, threshold=6)
        else:
            raise ValueError(strategy)

        reply, ptokens = chat(to_send)
        history.append({"role": "assistant", "content": reply})

        print(f"\n[第{turn}轮] 用户：{user_msg}")
        print(f"助手：{reply}")
        print(f"  ↳ prompt_tokens={ptokens}  | 本次实际发送 {len(to_send)} 条消息")


if __name__ == "__main__":
    # 三种方案各跑一遍，重点看「第5轮（问名字）」答得对不对，以及 prompt_tokens 的增长曲线
    run("full")
    run("window")
    run("summary")

# =============================================================================
# 写完后自检 / 思考题（写进对比笔记，面试考点）：
#   1. full 的 prompt_tokens 是怎么增长的？window 的呢？画出趋势对比。
#   2. 第5轮「我叫什么名字」——三种方案分别答对了吗？为什么 window 容易答错？
#   3. summary 方案里，为什么要「保留最近 2 条不压缩」？全压成摘要会丢什么？
#   4. 三者各自适合什么场景？（短对话/长对话/超长客服会话）
# =============================================================================
