# Business Trace: case-bootstrap-inferred-single-domain

## 场景背景

- 配对技术版本：[[trace-agent-case-bootstrap-inferred-single-domain]]
- 岗位目标：招聘一位高级 Agent 后端工程师。
- 本 case 关注的问题：业务没有显式指定领域包时，系统是否能只选出一个最合适的领域来启动。

## 系统路线选择

- 系统选择了“单领域推断 bootstrap”。
- 原因是：岗位信号足够集中，`llm_agent_rag_engineering` 明显比其他领域更贴近当前要求，不需要双领域补位，也不需要退回通用模式。

## 逐步处理记录

### 1. 需求抽取（ExtractRequirements）

- 系统拿到了什么：岗位描述里的核心标题信号 `Senior Agent Backend Engineer`。
- 调用了什么工具/服务：需求抽取模型（RequirementExtractionLLM）和运行时规范化逻辑。
- 产出了什么：标准化岗位需求，核心能力是 `Python backend`、`LLM application`、`workflow orchestration`。
- 对业务意味着什么：系统先把岗位说清楚，再决定走哪个领域。

### 2. 领域知识路由与检索（RetrieveGroundingKnowledge）

- 系统拿到了什么：空的显式领域配置和岗位真相。
- 调用了什么工具/服务：本地知识库快照、运行时路由逻辑和卡片匹配逻辑。
- 产出了什么：系统推断只选 `llm_agent_rag_engineering` 一个领域包，并取回与 Agent 后端、工作流编排有关的领域卡片。
- 对业务意味着什么：系统不是机械地多拿几个领域，而是只拿当前最稳的那个。

### 3. 评分口径冻结（FreezeScoringPolicy）

- 系统拿到了什么：岗位限制和业务评分偏好。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：与显式领域场景相同的一套固定评分口径。
- 对业务意味着什么：选一个领域还是两个领域，不会改变评分规则本身。

### 4. 启动线索生成（GenerateGroundingOutput）

- 系统拿到了什么：单个推断领域的卡片和岗位需求。
- 调用了什么工具/服务：Grounding 生成模型（GroundingGenerationLLM draft）和运行时规范化逻辑。
- 产出了什么：3 条启动 branch，其中仍然包括 `domain_company`。
- 对业务意味着什么：只要有足够可信的领域来源，系统就允许用该领域里的公司/场景线索启动搜索。

### 5. 初始前沿建立（InitializeFrontierState）

- 系统拿到了什么：3 条启动 branch。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：3 个初始待展开节点。
- 对业务意味着什么：虽然只选了一个领域包，但搜索仍然保留多路线启动，而不是单 query。

### 6. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：3 个初始节点。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：当前先展开 `seed_must_have_alias_01`；donor 仍为空；允许操作里包含 `domain_company` 和 `crossover_compose`。
- 对业务意味着什么：单领域推断只影响“从哪里启动”，不影响 round-0 的基本控制逻辑。

## 最终结果

- 系统成功以一个推断出的领域包完成 bootstrap，并进入控制器阶段。
- 本轮没有 donor 候选，说明交叉扩展还要等后续有 reward 的 child 节点出现。

## 业务解读与风险

- 这条路径适合岗位画像比较集中、一个领域包就能解释主要要求的场景。
- 风险点在于：如果岗位其实横跨两个能力簇，而系统只选了一个领域，后续搜索可能需要靠 repair/crossover 再补回来。
