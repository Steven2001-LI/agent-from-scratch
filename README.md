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
- [ ] `week1/day3_react.py` — 无框架 ReAct Agent（<200 行），Thought → Action → Observation
- [ ] `week1/day4_memory.py` — 多轮记忆三方案对比：完整历史 / 滑动窗口 / 摘要压缩

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
