# Agent From Scratch

从零徒手实现 Agent 核心机制的学习仓库，不依赖 LangChain/LangGraph 等框架，目标是彻底理解每一层原理。

时间线：2026-06-10 起，每日提交。

## 进度

### Week 1（6.10–6.16）：底层原理
- [x] `week1/day1_agent.py` 
    - 用 DeepSeek（OpenAI 兼容）跑通多轮对话
    - 客户端维护 messages 实现记忆
    - 观测 finish_reason 与 prompt_tokens
    - 截断实验：max_tokens 触发 finish_reason=length
- [x] `week1/day2_function_calling.py`
    - 徒手实现 Function Calling 完整循环（模型决策 → 代码执行 → 结果回传 → 再问）
    - 多工具下模型自动选对工具（天气 / 计算器）
    - 并行工具调用：一次返回多个 tool_calls，for 循环逐个执行
    - 加 print 打开黑箱，让「决策—执行」链路可观测
- [x] `week1/day3_react.py`
    - 无框架 ReAct Agent（<200 行）：Thought → Action → Observation 循环手写撑起
    - 不用原生 Function Calling，用 prompt 教模型按 ReAct 格式输出纯文本
    - 自写 parse() 正则解析 Action / Action Input / Final Answer
    - 关键技巧 stop=["Observation:"]：掐断模型自我脑补，把观察结果话语权留给代码
    - action 分支容错（工具名校验）+ 把模型输出与 Observation 都回拼 messages 形成"环"
- [x] `week1/day4_memory.py`
    - 多轮记忆三方案对比：完整历史 full / 滑动窗口 window / 摘要压缩 summary
    - 同一段 6 轮脚本对话分别跑三种方案，打印每轮 prompt_tokens 做对比
    - 设计"第5轮问名字"陷阱题：window 因名字被挤出窗口而答错，full/summary 答对
    - 亲眼看到 token 曲线：full 单调涨 / window 被 k 钉平 / summary 居中且压缩轮会缩短消息数

### Week 2（6.17–6.23）：RAG 全链路
- [ ] embedding + chunking 策略实验（3 种切分策略对比）
- [ ] Chroma 向量库 + 检索生成链路（任意 PDF 可问答）
- [ ] rerank + 混合检索（向量 + BM25），加 rerank 前后对比数据

## 学习日志

### 2026-06-10
- 仓库初始化。
- LLM 无状态，记忆是客户端累加 messages 造出来的
- 亲眼验证 prompt_tokens 单调增长 = 上下文的代价
- finish_reason 的 stop / length 含义，截断实验怎么触发的

### 2026-06-11
- Function Calling 本质是个循环：模型只「决策」（返回 tool_calls 说想调啥、传什么参数），真正「执行」函数是我的代码，结果以 role=tool 回传后再问一次，模型才给最终答案。
- 模型会把人话翻译成结构化参数：「3 的 5 次方加 10」→ `{"expression": "3**5+10"}`。
- 多工具时模型自主选对工具；一次能并行返回多个 tool_calls，靠 tool_call_id 把每个结果和对应调用对上号。
- 两个坑：arguments 是 JSON 字符串，要 json.loads 转字典；tool 结果的 content 必须是字符串，数字要 str() 包一下。
- 可观测性：答案对 ≠ 流程对。不打印中间过程，根本不知道模型有没有真用工具。

### 2026-06-18
- 手写 ReAct：day2 是 API 帮你管循环（结构化 tool_calls），day3 是自己用 prompt + 字符串解析把"思考-行动-观察"循环撑起来。
- 模型并不"真会"调工具，只是被 prompt 教会按 Thought/Action/Action Input 格式吐字；真正解析、执行、回拼全是我的代码。
- stop=["Observation:"] 是灵魂：不加，模型会自己脑补 Observation（幻觉），整个 ReAct 就废了。
- 本质循环和 day2 完全一样，只是把"结构化对象"换成了"纯文本 + 正则"：tool_calls→parse()，role=tool→role=user+Observation 文本。
- ReAct 优点：任何模型都能用、推理过程可解释；缺点：解析脆弱、格式易崩、更费 token——这正是 W3 引入 LangGraph 要标准化的部分。

### 2026-06-18（day4）
- 记忆管理是「记得住」和「不爆 token」之间的取舍，三种主流方案各有代价。
- full：每次发全部历史，记得全但 prompt_tokens 单调增长，迟早撞上下文窗口上限。
- window：只发 system + 最近 k 条，token 被 k 钉死，但会忘掉早期信息——实测第5轮问名字直接答错。
- summary：历史超阈值就让模型把旧消息压成摘要，再带 system + 摘要 + 最近几条；用一次额外调用换「省 token 又不丢关键事实」，实测第5轮靠摘要里的「小李」答对。
- 关键实现细节：摘要时保留最近 2 条不压缩（最近上下文最相关，全压会丢即时语境）；触发压缩那轮消息条数会明显变短。
- 场景选择：短对话用 full；固定轮次/客服用 window；超长多轮、需长期记住关键事实用 summary（或几种混合）。
