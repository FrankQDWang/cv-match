# Business Trace: case-bootstrap-inferred-dual-domain

## 场景背景

- 配对技术版本：[[trace-agent-case-bootstrap-inferred-dual-domain]]
- 岗位目标：招聘一位同时具备 Python / LLM 和 retrieval / ranking 经验的高级工程师。
- 本 case 关注的问题：当岗位天然横跨两个能力簇时，系统能否一次性启用两个互补领域。

## 系统路线选择

- 系统选择了“双领域推断 bootstrap”。
- 原因是：一个领域包覆盖 `Agent / LLM`，另一个领域包覆盖 `retrieval / ranking`，两者分别补到不同的 must-have，单包不足以完整解释岗位。

## 逐步处理记录

### 1. 需求抽取（ExtractRequirements）

- 系统拿到了什么：岗位描述 `Senior Python / LLM Engineer`。
- 调用了什么工具/服务：需求抽取模型（RequirementExtractionLLM）和运行时规范化逻辑。
- 产出了什么：标准化岗位需求，must-have 同时包含 `Python backend`、`LLM application` 和 `retrieval or ranking experience`。
- 对业务意味着什么：系统明确识别出这是一个跨两类能力的岗位，而不是单一画像。

### 2. 领域知识路由与检索（RetrieveGroundingKnowledge）

- 系统拿到了什么：岗位 must-have 列表和空的显式领域配置。
- 调用了什么工具/服务：本地知识库快照、运行时路由逻辑和卡片匹配逻辑。
- 产出了什么：系统同时选中 `llm_agent_rag_engineering` 和 `search_ranking_retrieval_engineering` 两个领域包，并取回双方的代表性卡片。
- 对业务意味着什么：系统承认这是“混合型岗位”，不强行压成单一路线。

### 3. 评分口径冻结（FreezeScoringPolicy）

- 系统拿到了什么：岗位限制、业务偏好和双领域检索结果。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：一套统一评分口径，而不是一份领域一套规则。
- 对业务意味着什么：即便是双领域启动，最终 shortlist 仍在同一个评分框架里比较。

### 4. 启动线索生成（GenerateGroundingOutput）

- 系统拿到了什么：两个领域的知识卡片和岗位需求。
- 调用了什么工具/服务：Grounding 生成模型（GroundingGenerationLLM draft）和运行时规范化逻辑。
- 产出了什么：3 条启动 branch，分别抓住 Agent 核心、retrieval 核心和平台/场景线索。
- 对业务意味着什么：系统在 bootstrap 阶段就把两个能力方向都布进前沿，而不是指望后面临时补。

### 5. 初始前沿建立（InitializeFrontierState）

- 系统拿到了什么：3 条跨双领域的启动 branch。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：`seed_agent_core`、`seed_search_domain`、`seed_platform` 三个初始节点。
- 对业务意味着什么：后续搜索一开始就有两条能力主线可供展开。

### 6. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：3 个初始节点。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：先选中 `seed_agent_core`；donor 仍为空；允许的操作包括 `crossover_compose`，但现在还没有可用 donor。
- 对业务意味着什么：系统先从主线之一切入，等后续产生有效 child 节点后，再考虑交叉融合。

## 最终结果

- 系统成功以两个互补领域包完成 bootstrap，并进入控制器阶段。
- round-0 里没有 donor 候选，但双主线已经被种下，后续更容易出现合法 crossover。

## 业务解读与风险

- 这条路径适合“岗位明确跨两个成熟知识域”的场景。
- 风险点在于：双领域会提高前几轮探索面，若领域包质量不稳，可能带来更多无效分支。
