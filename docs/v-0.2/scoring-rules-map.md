# v0.2 评分规则总览

这份文档只回答三个问题：

1. `ScoringPolicy` 是什么
2. 一次评分是怎么来的
3. 四个分数分别表示什么

事实来源：

- Prompt: [scoring.md](/Users/frankqdwang/Agents/cv-match/src/cv_match/prompts/scoring.md)
- 输入/输出模型: [models.py](/Users/frankqdwang/Agents/cv-match/src/cv_match/models.py)

## 1. `ScoringPolicy` 是什么

`ScoringPolicy` 可以理解成“这次岗位的固定评分尺子”。

它来自岗位需求，不来自候选人，也不随着每轮检索变化。里面主要包含：

- 这个岗位是什么
- 哪些能力是 `must-have`
- 哪些能力是 `preferred`
- 哪些情况属于排除信号
- 有哪些硬约束和偏好
- 这次评分的重点是什么

一句话：

`ScoringPolicy` 负责定义“用什么标准打分”。

### 它和 `RequirementSheet` 是什么关系

可以把两者理解成：

- `RequirementSheet`: 更完整的岗位需求真相
- `ScoringPolicy`: 从 `RequirementSheet` 里提炼出来的评分版摘要

也就是说：

- `RequirementSheet` 更大，服务整个运行流程
- `ScoringPolicy` 更窄，只服务评分

一个简单记法：

先有 `RequirementSheet`，再从里面生成 `ScoringPolicy`。

## 2. 一次评分怎么来

一次评分可以直接理解成下面 5 步。

### 第 1 步：读输入

评分器只看两样东西：

- `ScoringPolicy`
- 一份 `NormalizedResume`

也就是：一把固定尺子，加一份候选人简历。

### 第 2 步：先盘点证据

先不打分，先看简历事实能落到哪里：

- 哪些内容支持 `must-have`
- 哪些内容支持 `preferred`
- 哪些关键要求没有证据
- 哪些地方存在负面信号或风险

这一步本质是在回答：

“这份简历到底提供了什么证据？”

### 第 3 步：先判 `fit_bucket`

先做顶层判断，不先算总分。

- `fit`: 关键要求基本有证据，而且没有明显致命冲突
- `not_fit`: 关键要求缺失，或有明显冲突，或证据太弱

这一步最重要，因为后面的分数都必须服从它。

### 第 4 步：再填三个局部分数

先有顶层判断，再写局部分数：

- `must_have_match_score`: 关键要求匹配得怎么样
- `preferred_match_score`: 加分项匹配得怎么样
- `risk_score`: 当前判断还有多大风险，越高风险越大

这里没有固定公式，但顺序很清楚：

先判断，再分别描述“硬要求匹配度”“加分项匹配度”“风险大小”。

### 第 5 步：最后收束成 `overall_score`

`overall_score` 不是自由发挥，也不是单独算出来的。

它是对前面判断的收束，必须和前面的故事一致：

- 如果已经是 `not_fit`，总分就不能高得像通过了一样
- 如果关键项很强、风险也低，总分通常就应该更高

一句话：

分数不是先算出来再判断，而是先判断，再把这个判断展开成几项分数。

## 3. 四个分数怎么理解

### `must_have_match_score`

看硬要求。

它回答的是：

“岗位最关键的要求，这份简历到底支持了多少？”

### `preferred_match_score`

看加分项。

它回答的是：

“在硬门槛之外，这个人还有多少额外亮点？”

### `risk_score`

看风险。

它回答的是：

“即使现在有一些正向信号，这个判断还剩下多大不确定性或风险？”

注意：越高风险越大。

### `overall_score`

看整体匹配度。

它回答的是：

“综合硬要求、加分项和风险之后，这个人整体有多匹配这个岗位？”

## 4. 一个最短例子

假设岗位要求：

- 必须有 Python
- 必须有 LLM 落地经验
- 最好有招聘行业背景

某份简历：

- 明确写了 Python
- 明确写了 RAG/LLM 项目
- 没写招聘行业背景
- 项目写得比较短，证据不算很厚

那么一个自然的评分过程就是：

1. 先看证据。Python 和 LLM 都有支持，招聘行业背景没有支持。
2. 先判 `fit_bucket`。关键要求基本满足，所以有机会进 `fit`。
3. 写 `must_have_match_score`。通常会比较高。
4. 写 `preferred_match_score`。通常不会太高。
5. 写 `risk_score`。因为证据厚度一般，风险不会特别低。
6. 写 `overall_score`。大概率是偏高，但不是顶格。

## 5. 记住这三句话就够了

- `ScoringPolicy` 是固定评分尺子。
- 评分顺序是：先看证据，先判 `fit_bucket`，再写分数。
- `overall_score` 不是公式结果，而是对前面判断的收束。
