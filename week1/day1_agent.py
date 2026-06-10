
import os                          # 标准库，用来读环境变量（os.getenv）
from dotenv import load_dotenv      # 第三方库，把 .env 文件里的变量加载进环境
from openai import OpenAI           # OpenAI 官方 SDK；它只是个"客户端库"，连哪家服务由 base_url 决定

# 读取当前目录（及上层）的 .env 文件，把里面的 OPENAI_API_KEY 注入到环境变量里。
# 这样 key 不写死在代码里，.env 又被 .gitignore 忽略，就不会泄露到 GitHub。
load_dotenv()

# 创建一个"客户端"对象，之后所有请求都通过它发出。
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),    # 从环境变量取出 key（这里其实填的是 DeepSeek 的 key）
    base_url="https://api.deepseek.com",    # 关键：把请求指向 DeepSeek 的服务器，而不是 OpenAI 官方
)

messages = [{"role": "system", "content": "你是一个简洁的助手"}]

while True:
    user_input = input("你: ")
    if user_input == "quit":
        break
    # TODO: append 用户输入 → 调 API → 取回复打印 → append 回复 → 打印 finish_reason 和 prompt_tokens

    messages.append({"role":"user", "content":user_input})
    
    response = client.chat.completions.create(
        model="deepseek-chat",                  # 用哪个模型；因为连的是 DeepSeek，所以写 DeepSeek 的模型名
        messages = messages
    )
    reply = response.choices[0].message.content
    print(reply)
    #这个列表就是记忆，跨轮累加
    messages.append({"role":"assistant","content":reply})
    # print(response.choices[0].finish_reason)
    # print(response.usage.prompt_tokens)
    print("========================")


# 解析返回结果，取出模型回复的文本：
#   response.choices    —— 模型可能返回多个候选回复，是个列表
#   [0]                 —— 取第一个（默认也只有一个）
#   .message.content    —— 这条回复的正文字符串
#print(response.choices[0].message.content)

'''
这是一个多轮对话的例子。
在每次循环中，我们都会把用户输入和模型的回复追加到 messages 列表中。
这样，模型就能记住之前的对话内容，实现多轮对话。
手写了多轮对话循环，理解 LLM 无状态本质，
通过客户端维护 messages 上下文实现记忆，
并观测到 prompt_tokens 随轮次单调增长，认识到上下文窗口与成本的权衡。
'''