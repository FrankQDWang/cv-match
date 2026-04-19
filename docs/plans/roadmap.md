# SeekTalent Roadmap

## 结论

SeekTalent 下一阶段不应该改成完全开放式 agent。当前正确方向是继续保持受控、可审计 workflow，把搜索表示、失败归因、预算纪律和 eval 做硬，再逐步释放局部 agent 自主性。

当前主线：

1. 先保证搜索失败可诊断。
2. 再让搜索词经过 deterministic compiler 准入。
3. 再做 controller 的预算和停止策略。
4. 再做 benchmark 扩展、schema 精简和 reasoning model A/B。
5. 最后再进入 bounded reflection discovery、独立 verifier、session memory 和网页/app action harness。

不要先做的事：

- 不把整个 runtime 改成 open-ended agent。
- 不先抽一批 `CatalogBuilder` / `RewritePolicy` / `ReflectionDiscovery` / `Verifier` / `RetrievalAdapter` 抽象接口。
- 不用 prompt-only 修搜索表示。
- 不恢复“每个 query 必须包含 exact title anchor”的旧合同。

外部方向依据只作为设计 rationale：Anthropic 的 [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)、[Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)、[Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)、[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) 都支持同一个判断：简单可组合 workflow 优先，agent 自主性要被 harness、context、tool 和 eval 约束。

## 当前状态

Repo 当前 public shape 是 deterministic Python Agent。`docs/architecture.md` 明确写到设计目标是 controlled behavior 和 auditability，而不是 open-ended agent autonomy。主链路是 requirement extraction -> controlled CTS retrieval -> scoring -> reflection -> finalization。

Phase 1 已完成：`search_diagnostics.json` 已成为 run artifact。它把每轮 query、filter、CTS recall、dedup、scoring、reflection、controller response 和 LLM schema pressure 汇总到一个跨 round 诊断账本里。对应归档计划是 `docs/plans/completed/phase-1-search-diagnostics.md`，artifact 说明在 `docs/outputs.md`。

Phase 2 已完成：lexical compiler 和 query-plan admission 已落地。当前 `QueryTermCandidate` 已有 `retrieval_role`、`queryability`、`family`；`src/seektalent/retrieval/query_compiler.py` 负责编译 term pool；`src/seektalent/retrieval/query_plan.py` 负责拒绝非 admitted term、family 重复和缺少 compiler-admitted anchor 的 query。对应归档计划是 `docs/plans/completed/phase-2-search-lexical-compiler.md`。

Phase 2.1 已完成：controller context 现在包含预算状态和 deterministic stop guidance；runtime 会拒绝不符合 guidance 的 stop decision；query planner 会优先 `core_skill` / `framework_tool` 这类 high-signal non-anchor families；controller prompt 已要求遵守 stop guidance 和 near-budget exploit/narrowing。对应归档计划是 `docs/plans/completed/phase-2-1-search-budget-precision-tuning.md`。

Phase 2 replay 结果：

| 指标 | Phase 1 | Phase 2 | 变化 |
| --- | ---: | ---: | --- |
| 6 个样本 final candidates 总数 | 41 | 60 | 明显提升 |
| final candidate count 为 0 的样本 | 1 | 0 | 修复 |
| `agent_jd_002` | 0 candidates / 0.0 precision | 10 candidates / 0.2 precision | 关键修复 |
| `agent_jd_006` | 1 candidate / 0.0 precision | 10 candidates / 0.9 precision | 关键修复 |
| 平均 final precision@10 | 约 0.42 | 约 0.55 | 整体提升 |
| `agent_jd_001` | 0.9 precision | 0.5 precision | recall 放宽后的 precision tradeoff |
| `agent_jd_003` | 1.0 precision | 0.8 precision | recall 放宽后的 precision tradeoff |

当前判断：Phase 2 达成主要目标。它把系统从“会被脏词和 exact title anchor 卡死”推进到“稳定有召回、可审计、可调参”的状态。后续要处理 precision tradeoff，但不能通过回滚 compiler 或恢复 exact title anchor 来处理。

Phase 2.1 replay 结果：

| 指标 | 0.4.4 |
| --- | ---: |
| 样本数 | 6 |
| 平均 rounds | 3.00 |
| 平均 final total | 0.6334 |
| 平均 final precision@10 | 0.6333 |
| 平均 final ndcg@10 | 0.6337 |
| 平均 round1 total | 0.2999 |
| 平均 round1 precision@10 | 0.2833 |
| 平均 round1 ndcg@10 | 0.3385 |

W&B report 已验证 `0.4.4` run count 为 6，`0.4.3` run count 回到 6。Phase 2.1 的 replay summary 在 `runs/phase_2_1_budget_precision_replay_0_4_4_20260419_151845/benchmark_summary_20260419_160948.json`。

## What We Learned

LLM 抽词不能直接进入 CTS search。LLM 很容易抽出语义相关但检索很脏的词，例如 `任务拆解`、`长链路业务问题`、`AgentLoop调优`、`211`。这些词适合 scoring、filter 或 explanation，不适合早期 keyword search。

职位名不是天然好 anchor。`AI Agent工程师`、`Agent算法工程师` 这类 title 对 JD 很自然，但候选人简历里不一定这么写。早期检索更应该使用简历侧常见表达，例如 `AI Agent`、`Agent`、`大模型`、`RAG`、`LangChain`。

Compiler/family/queryability 是正确边界。controller 不应该自由拼任意 LLM term，而应该只能从 compiler-admitted term 和合法 family 组合里选择。

真实 CTS replay 比单测更重要。单测证明合同正确，但只有真实 replay 能暴露 precision/recall tradeoff。Phase 2 的结果说明：zero/low recall 大幅改善，同时 broad anchor 会让部分原高精度样本回退。

后续 precision tuning 不能恢复 mandatory exact title anchor。正确方向是优化 budget context、stop policy、family coverage 和 query ordering，让系统先保证召回，再有纪律地收紧。

## Priority Roadmap

### Phase 2.1: Search Budget and Precision Tuning

状态：已完成，见 `docs/plans/completed/phase-2-1-search-budget-precision-tuning.md`。

目标：解决“有召回后停得太早”和 broad anchor 带来的 precision tradeoff。

要做：

- 给 controller context 增加预算状态：current round、min/max rounds、remaining rounds、budget-used ratio。
- 由 runtime 提供 stop guidance：当前是否允许停止、为什么、哪些 high-priority admitted families 还没试。
- 调整 query ordering：优先 broad anchor + high-signal framework/core skill，降低 broad anchor + 泛 domain phrase 的优先级。
- 保持 compiler 和 admitted-anchor 合同，不恢复 exact title anchor。

验收：

- zero-final 保持为 0。
- `agent_jd_002` / `agent_jd_006` 的修复不回退。
- `agent_jd_001` / `agent_jd_003` precision 有恢复或至少不继续明显恶化。
- replay 中能解释每次 stop 的预算和 coverage 原因。

### Phase 2.2: Benchmark Expansion and Attribution

目标：避免在 6 条 Agent JD 上过拟合，让策略对真实岗位变化更稳。

要做：

- 从 6 条 Agent JD 扩到 15-20 条混合 JD。
- 覆盖强约束、弱约束、术语噪声、JD 词和简历词不一致、多城市/学历/经验硬条件。
- 每条增加人工备注：理想搜索概念、可接受候选信号、不可接受候选信号。
- 指标增加 productive rate、zero/shortage rounds、family coverage、query explainability。

验收：

- 每次 feature 只能单独开关或单独对比，避免多 feature 混跑。
- replay 报告能说明变化来自 compiler、query planner、stop policy、CTS filter 还是 scorer。

### Phase 2.3: Controller/Reflection Schema Slimming

目标：降低 structured-output 压力，但不改变搜索策略行为。

顺序：

- 先动 controller/reflection schema。
- 暂不动 scorer/finalizer 大 schema。
- 在 Phase 2.1 稳定后再做，避免把策略变化和 schema 变化混在一起。

验收：

- validator retry 不上升。
- controller/reflection artifact 仍能支持 diagnostics 和 replay attribution。
- 行为变化必须可解释；否则回退 schema 改动。

### Phase 2.4: Reasoning Model A/B

目标：验证 controller/reflection 是否从 reasoning model 中获益。

顺序：

- 先试 reflection，再试 controller。
- 保持 structured output 小，不因为换 reasoning model 就扩 JSON schema。
- 如果结构化输出不稳定，先记录失败，不立刻做多模型 fallback 链。

验收：

- 与 deepseek-chat v3.2 非推理模型对比。
- 看困难 JD recall lift、precision、stop quality、token 成本、validator retry。
- 只有 context 和 stop policy 已经清楚时，reasoning model 的结果才有解释价值。

### Phase 3: Bounded Reflection Discovery

目标：把 reflection 从受限 critic 升级为有提案权的 discovery agent，但不让它直接执行。

边界：

- Reflection 只能输出小的 hypothesis proposal。
- Proposal 类型控制在 alias、family swap、bundle shift、stop hypothesis。
- Compiler 保留准入权，controller 保留选择权，verifier 保留否决/复核权。

验收：

- 提案被 compiler 接受的比例可衡量。
- 困难 JD 的 recall/precision 有 lift。
- 每单位 token 成本换来的 qualified candidate 数量可解释。

### Phase 4: Independent Verifier

目标：把最终 shortlist 的复核从 sourcing/scoring 主链路中分离出来，减少自我背书。

要做：

- verifier 不负责找人，只负责挑错。
- 检查 false positives、解释漏洞、硬约束一致性和候选排序风险。

验收：

- 人工 reviewer accept rate 提升。
- 明显 false positive 能被抓出。
- final explanation 更一致、更可信。

### Phase 5: Recruiter Session Memory

目标：支持招聘搜索中的 seeking + refinding，而不是只做单次检索。

要做：

- 保存历史 query path。
- 支持 backoff、重复搜索复用、候选人回看路径、保存搜索和订阅更新。
- 记录哪些 family/bundle 在相似 JD 上成功过。

验收：

- time-to-first-acceptable-candidate 下降。
- 重复搜索复用率上升。
- 人工重写次数下降。

### Phase 6: Web/App Action Harness

目标：在 CTS 策略稳定后，把同一个 harness 接到猎聘网页和 Boss app 的动作层。

顺序：

- 先猎聘网页，后 Boss app。
- Boss app 放最后，因为 app 自动化的不确定性和调试成本更高。

边界：

- 用户授权、动作受控、日志可回放、失败可恢复。
- 动作集保持窄：输入关键词、点筛选、翻页、抽取结果、保存证据。
- 不给泛浏览器 agent 到处乱逛。

验收：

- DOM/action 成功率、回放一致性、失败恢复率、账号风险事件、单次任务完成时长可衡量。

## Explicit Non-Goals

- 不把整个 SeekTalent runtime 改成开放式 agent。
- 不在第二个实现出现前创建大型抽象接口层。
- 不用 prompt-only patch 替代 compiler/query-plan 合同。
- 不恢复 mandatory exact title anchor。
- 不把 schema slimming 或 reasoning model A/B 排在 stop policy 和 precision tuning 前面。
- 不在 CTS 阶段混入网页/app 自动化的不确定性。
- 不用 6 条 Agent JD 的局部结果直接宣称生产稳定。

## Decision Gates

每个阶段开始前必须有独立计划，至少写清：

- 要改的模块。
- 不改的模块。
- replay 命令。
- acceptance metrics。
- stop rules。

每个阶段完成后必须记录：

- 测试结果。
- 真实 CTS replay summary 路径。
- 关键指标变化。
- regressions 和取舍判断。

任何 feature 都应尽量单独验证。不要再一次性混入多个 feature 后再用总指标判断成败。

如果指标冲突，优先级如下：

1. 避免 zero-final / zero-recall 硬失败。
2. 保持可审计和可归因。
3. 提升 precision。
4. 降低 token/CTS 成本。
5. 增加 agent 自主性。

当前下一步建议：新建 active plan 做 `Phase 2.1 Search Budget and Precision Tuning`，不要先做 schema slimming 或 reasoning model A/B。
