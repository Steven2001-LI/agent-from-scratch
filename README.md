# Agent From Scratch

从零徒手实现 Agent 核心机制的学习仓库，不依赖 LangChain/LangGraph 等框架，目标是彻底理解每一层原理。

时间线：2026-06-10 起，每日提交。

## 进度

### Week 1（6.10–6.16）：底层原理
- [ ] `week1/day1_agent.py` — Claude API 跑通多轮对话，理解 messages / role / stop_reason
- [ ] `week1/day2_function_calling.py` — 徒手实现 Function Calling 完整循环
- [ ] `week1/day3_react.py` — 无框架 ReAct Agent（<200 行），Thought → Action → Observation
- [ ] `week1/day4_memory.py` — 多轮记忆三方案对比：完整历史 / 滑动窗口 / 摘要压缩

### Week 2（6.17–6.23）：RAG 全链路
- [ ] embedding + chunking 策略实验（3 种切分策略对比）
- [ ] Chroma 向量库 + 检索生成链路（任意 PDF 可问答）
- [ ] rerank + 混合检索（向量 + BM25），加 rerank 前后对比数据

## 学习日志

### 2026-06-10
仓库初始化。
