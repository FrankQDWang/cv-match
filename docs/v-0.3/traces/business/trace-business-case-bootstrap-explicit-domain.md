# Business Trace: case-bootstrap-explicit-domain

## 场景背景

- 配对技术版本：[[trace-agent-case-bootstrap-explicit-domain]]
- 岗位目标：招聘一位偏 Agent / RAG 场景的高级后端工程师。
- 本 case 关注的问题：业务已经明确指定领域知识包时，系统是否会按指定路线启动，而不是自己再猜一遍。

## 系统路线选择

- 系统选择了“显式领域 bootstrap”。
- 原因很直接：业务包里已经明确给出 `llm_agent_rag_engineering`，所以系统不再做领域猜测，而是直接使用该领域知识启动第一轮搜索。

## 逐步处理记录

### 1. 需求抽取（ExtractRequirements）

- 系统拿到了什么：岗位描述和招聘备注，重点信号是 `Senior Agent Backend Engineer`。
- 调用了什么工具/服务：需求抽取模型（RequirementExtractionLLM）和运行时规范化逻辑。
- 产出了什么：标准化岗位需求，包括 `Python backend`、`LLM application`、`workflow orchestration` 等核心要求，以及 `Shanghai` 地点约束。
- 对业务意味着什么：从这一步开始，后续所有路由、评分和搜索都围绕同一份岗位真相展开。

### 2. 领域知识路由与检索（RetrieveGroundingKnowledge）

- 系统拿到了什么：业务指定的领域包、岗位标题和基础能力要求。
- 调用了什么工具/服务：本地知识库快照（local grounding knowledge base snapshot）、运行时路由逻辑和卡片匹配逻辑。
- 产出了什么：系统直接命中 `llm_agent_rag_engineering`，并取回与 `backend_agent_engineer`、`workflow_orchestration` 相关的领域卡片，同时带出需要避开的负面信号。
- 对业务意味着什么：第一轮启动不是“从零拼 query”，而是先借助已编译的领域知识把搜索空间收窄。

### 3. 评分口径冻结（FreezeScoringPolicy）

- 系统拿到了什么：岗位硬约束和业务评分偏好。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：本次 run 固定使用的评分口径，包括地点限制和 rerank / must-have / preferred / risk 的融合权重。
- 对业务意味着什么：后续每轮评分都按同一把尺子进行，不会在运行过程中漂移。

### 4. 启动线索生成（GenerateGroundingOutput）

- 系统拿到了什么：刚才检回的领域卡片和岗位需求。
- 调用了什么工具/服务：Grounding 生成模型（GroundingGenerationLLM draft）和运行时规范化逻辑。
- 产出了什么：3 条启动 branch，分别偏向 `must_have_alias`、`strict_core`、`domain_company`。
- 对业务意味着什么：系统不是只造一条长搜索词，而是同时铺开几条短而明确的起始路线，其中 `domain_company` 在显式领域场景下是允许的。

### 5. 初始前沿建立（InitializeFrontierState）

- 系统拿到了什么：3 条启动 branch 说明。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：3 个待展开的起始节点，预算为 5，`crossover_compose` 等操作的统计记录也被初始化。
- 对业务意味着什么：系统已经准备好从多个起点并行探索，而不是一次性押注单一路线。

### 6. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：当前 3 个起始节点和固定评分口径。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：当前先展开 `seed_must_have_alias_01`；本轮没有 donor 候选；允许的操作包括 `must_have_alias`、`strict_core`、`domain_company` 和 `crossover_compose`。
- 对业务意味着什么：第一轮仍然会先从最核心的岗位要求切入，但已经为后续交叉扩展保留了轨道。

## 最终结果

- 这一 case 的终点不是最终候选人，而是成功把系统送入控制器阶段。
- 结果是：显式领域路线被保留，`domain_company` 作为合法启动分支出现，第一轮没有 donor 候选。

## 业务解读与风险

- 这条路径最适合“业务已经知道岗位属于哪个成熟领域包”的场景。
- 风险点在于：如果业务指定了错误领域包，系统也会优先信它，所以领域包本身需要维护质量。
