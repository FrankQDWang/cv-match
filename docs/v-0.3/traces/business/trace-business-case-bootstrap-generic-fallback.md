# Business Trace: case-bootstrap-generic-fallback

## 场景背景

- 配对技术版本：[[trace-agent-case-bootstrap-generic-fallback]]
- 岗位目标：招聘一位偏企业级 SaaS 数据治理 / 交付的负责人。
- 本 case 关注的问题：当知识库里没有合适领域包时，系统能否安全回退，而不是硬套错领域。

## 系统路线选择

- 系统选择了“通用回退 bootstrap”。
- 原因是：现有领域包都不足以可信解释这个岗位，所以系统不用错误的领域知识，而是直接按岗位真相做通用启动。

## 逐步处理记录

### 1. 需求抽取（ExtractRequirements）

- 系统拿到了什么：岗位描述 `Enterprise SaaS Data Governance Lead`。
- 调用了什么工具/服务：需求抽取模型（RequirementExtractionLLM）和运行时规范化逻辑。
- 产出了什么：标准化岗位需求，核心能力包括 `data governance`、`stakeholder management`、`enterprise delivery`、`cross-functional program leadership`、`policy design`。
- 对业务意味着什么：即便没有现成领域包，岗位真相仍然先被结构化下来。

### 2. 领域知识路由与检索（RetrieveGroundingKnowledge）

- 系统拿到了什么：空的显式领域配置和岗位真相。
- 调用了什么工具/服务：本地知识库快照和运行时路由逻辑。
- 产出了什么：系统明确选择 `generic_fallback`，不选任何领域包，也不返回领域卡片，只保留一些需要规避的误导性信号。
- 对业务意味着什么：系统承认“这题知识库暂时不会”，比强行套错领域更安全。

### 3. 评分口径冻结（FreezeScoringPolicy）

- 系统拿到了什么：岗位要求和业务偏好。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：没有领域卡片也照样冻结了一套评分口径。
- 对业务意味着什么：通用回退并不意味着评分失控，只是启动证据变成岗位自身。

### 4. 启动线索生成（GenerateGroundingOutput）

- 系统拿到了什么：岗位真相和空的领域检索结果。
- 调用了什么工具/服务：Grounding 生成模型（GroundingGenerationLLM draft）和运行时规范化逻辑。
- 产出了什么：系统用虚拟证据卡代替领域卡片，并生成 5 条启动 branch，其中 3 条是基础启动线，另外 2 条是为了补足还没覆盖到的 must-have。
- 对业务意味着什么：没有领域包时，系统会更保守地从岗位标题和 must-have 本身启动，并主动补修“还没搜到的重点能力”。

### 5. 初始前沿建立（InitializeFrontierState）

- 系统拿到了什么：5 条通用启动 branch。
- 调用了什么工具/服务：运行时确定性逻辑。
- 产出了什么：5 个初始待展开节点。
- 对业务意味着什么：通用回退不是弱化搜索，而是改成更明确的“岗位真相驱动多路启动”。

### 6. 当前分支选择（SelectActiveFrontierNode）

- 系统拿到了什么：5 个初始节点。
- 调用了什么工具/服务：运行时优先级打分和 donor 打包逻辑。
- 产出了什么：当前先展开 `seed_must_have_core`；允许操作只有 `must_have_alias`、`strict_core`、`crossover_compose`，不包含 `domain_company`。
- 对业务意味着什么：因为没有可信领域来源，系统不会使用依赖领域来源的 `domain_company` 路线。

## 最终结果

- 系统成功在没有合适领域包的情况下完成 bootstrap，并进入控制器阶段。
- 关键结果是：保留了可审计的通用证据来源，同时阻止了不该出现的 `domain_company` 分支。

## 业务解读与风险

- 这条路径适合新岗位、冷门岗位、知识库尚未覆盖的岗位。
- 风险点在于：通用回退通常会比成熟领域路线更依赖后续多轮 repair 和 crossover，早期效率可能偏低。
