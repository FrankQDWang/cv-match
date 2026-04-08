# SeekTalent v0.3 交互式数据流导图

> 本页是 `Obsidian` 导航入口。
> 它只提供 bootstrap 和单次 expansion 的主链导航，不重复定义字段级 contract。
> payload 的字段定义以 `payloads/` 为准，operator 的 read/write set 以 `operators/` 为准。
> runtime config / threshold / catalog 以 `runtime/` 为准，behavior-level helper 语义以 `semantics/` 为准。
> 图中只画 stable payload 主链，不画 `runtime/` 中 config / threshold / catalog 的读边。

## 0. 阅读约定

1. 蓝色节点是 stable payload。
2. 绿色节点是 operator。
3. 粉色节点是 LLM black box；draft payload 仍然是蓝色 payload node。
4. 橙色节点是离线 trace artifact，不属于 runtime 主流程。
5. 虚线表示离线渲染边，不表示 runtime read/write。
6. 带 `internal-link` 的节点可在 `Obsidian` 中直接点开对应 note。

## 1. Bootstrap + Single Expansion 数据依赖图

```mermaid
flowchart TD
    subgraph B["Bootstrap"]
        SIT["SearchInputTruth"] -->|extract| RELLM["RequirementExtractionLLM"]
        RELLM -->|draft| RED["RequirementExtractionDraft"]
        SIT -->|input truth| ER["ExtractRequirements"]
        RED -->|normalize| ER["ExtractRequirements"]
        ER -->|truth| RS["RequirementSheet"]

        BP["BusinessPolicyPack"] -->|policy| RGK["RetrieveGroundingKnowledge"]
        KBS["GroundingKnowledgeBaseSnapshot"] -->|snapshot| RGK
        RS -->|requirements| RGK
        RGK -->|routing + retrieval| KRR["KnowledgeRetrievalResult"]

        BP -->|policy| FSP["FreezeScoringPolicy"]
        RC["RerankerCalibration"] -->|calibration| FSP
        RS -->|requirements| FSP
        FSP -->|policy| SP["ScoringPolicy"]

        RS -->|requirements| GLLM["GroundingGenerationLLM"]
        KRR -->|knowledge| GLLM
        GLLM -->|draft| GD["GroundingDraft"]
        RS -->|requirements| GGO["GenerateGroundingOutput"]
        KRR -->|knowledge| GGO
        GD -->|normalize| GGO
        GGO -->|grounding| GO["GroundingOutput"]

        GO -->|grounding| IFS["InitializeFrontierState"]
        IFS -->|frontier| FS0["FrontierState_t"]
    end

    subgraph E["Single Expansion"]
        FS0 -->|select + pack| SAFN["SelectActiveFrontierNode"]
        RS -->|truth| SAFN
        SP -->|policy| SAFN
        SAFN -->|context| SCC["SearchControllerContext_t"]

        SCC -->|infer| SCDLLM["SearchControllerDecisionLLM"]
        SCDLLM -->|draft| SCDD["SearchControllerDecisionDraft_t"]
        SCDD -->|normalize| GSCD["GenerateSearchControllerDecision"]
        GSCD -->|decision| SCD["SearchControllerDecision_t"]

        FS0 -->|carry forward| CFFS["CarryForwardFrontierState"]
        CFFS -->|frontier'| FS1["FrontierState_t1"]

        FS0 -->|active node| MSEP["MaterializeSearchExecutionPlan"]
        RS -->|constraints| MSEP
        SCD -->|patch| MSEP
        MSEP -->|plan| SEP["SearchExecutionPlan_t"]

        SEP -->|execute| ESP["ExecuteSearchPlan"]
        ESP -->|results| SER["SearchExecutionResult_t"]

        SER -->|text convert + rerank + calibration + fuse| SSR["ScoreSearchResults"]
        SP -->|policy| SSR
        SSR -->|scored| SSC["SearchScoringResult_t"]

        RS -->|eval packet| BELLM["BranchOutcomeEvaluationLLM"]
        FS0 -->|eval packet| BELLM
        SEP -->|eval packet| BELLM
        SER -->|eval packet| BELLM
        SSC -->|eval packet| BELLM
        BELLM -->|draft| BED["BranchEvaluationDraft_t"]
        RS -->|requirements| EBO["EvaluateBranchOutcome"]
        FS0 -->|branch| EBO
        SEP -->|plan| EBO
        SER -->|telemetry| EBO
        SSC -->|scores| EBO
        BED -->|normalize| EBO
        EBO -->|critic| BE["BranchEvaluation_t"]

        FS0 -->|branch| CNRB["ComputeNodeRewardBreakdown"]
        SEP -->|plan| CNRB
        SER -->|telemetry| CNRB
        SSC -->|scores| CNRB
        BE -->|critic| CNRB
        CNRB -->|reward| NRB["NodeRewardBreakdown_t"]

        FS0 -->|merge| UFS["UpdateFrontierState"]
        SEP -->|plan| UFS
        SSC -->|shortlist| UFS
        BE -->|evaluation| UFS
        NRB -->|reward| UFS
        UFS -->|frontier'| FS1

        FS1 -->|guard| ESC["EvaluateStopCondition"]
        SCD -->|controller action| ESC
        BE -->|branch state| ESC
        NRB -->|reward| ESC
    end

    subgraph F["Search Run Finalization"]
        RS -->|truth| SRFLLM["SearchRunFinalizationLLM"]
        FS1 -->|frontier| SRFLLM
        ESC -->|stop_reason| SRFLLM
        SRFLLM -->|draft| SRSD["SearchRunSummaryDraft_t"]
        SRSD -->|normalize| FSR["FinalizeSearchRun"]
        FSR -->|result| SRR["SearchRunResult"]
    end

    subgraph T["Trace Artifacts (offline render)"]
        TAB["Trace Bundle"]
        AT["Agent Trace cases"]
        BT["Business Trace cases"]
        TAB -->|render| AT
        TAB -->|render| BT
    end

    RS -.->|truth snapshot| TAB
    KRR -.->|routing snapshot| TAB
    SP -.->|policy snapshot| TAB
    FS0 -.->|bootstrap frontier| TAB
    SCC -.->|controller context| TAB
    SCD -.->|controller decision| TAB
    SEP -.->|search plan| TAB
    SER -.->|search results| TAB
    SSC -.->|scored shortlist| TAB
    BE -.->|branch evaluation| TAB
    NRB -.->|reward breakdown| TAB
    FS1 -.->|frontier snapshot| TAB
    ESC -.->|stop outcome| TAB
    SRR -.->|final result| TAB

    classDef payload fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1.5px;
    classDef operator fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:1.5px;
    classDef llm fill:#fce7f3,stroke:#db2777,color:#4a044e,stroke-width:1.5px;
    classDef trace fill:#fed7aa,stroke:#ea580c,color:#431407,stroke-width:1.5px;

    class SIT,RED,RS,BP,KBS,KRR,RC,SP,GD,GO,FS0,SCC,SCDD,SCD,SEP,SER,SSC,BED,BE,NRB,FS1,SRSD,SRR payload;
    class ER,RGK,FSP,GGO,IFS,SAFN,GSCD,CFFS,MSEP,ESP,SSR,EBO,CNRB,UFS,ESC,FSR operator;
    class RELLM,GLLM,SCDLLM,BELLM,SRFLLM llm;
    class TAB,AT,BT trace;

    class SIT,RED,RS,BP,KBS,KRR,RC,SP,GD,GO,FS0,SCC,SCDD,SCD,SEP,SER,SSC,BED,BE,NRB,FS1,SRSD,SRR internal-link;
    class ER,RGK,FSP,GGO,IFS,SAFN,GSCD,CFFS,MSEP,ESP,SSR,EBO,CNRB,UFS,ESC,FSR internal-link;
```

图中的 `Trace Bundle -> Agent Trace / Business Trace` 只表示：稳定 run artifacts 可以被离线渲染成双轨 trace；它不是新 operator，不参与 runtime 状态推进，也不回写 payload。

## 2. Core Payload Entry Points

公式与 `Agent Trace` 中使用的短记号映射如下：

```text
B := BusinessPolicyPack
KB := GroundingKnowledgeBaseSnapshot
K := KnowledgeRetrievalResult
C := RerankerCalibration
R := RequirementSheet
P := ScoringPolicy
F_t := FrontierState_t
F_{t+1} := FrontierState_t1
n_t := active frontier node
d_t := SearchControllerDecision_t
p_t := SearchExecutionPlan_t
x_t := SearchExecutionResult_t
y_t := SearchScoringResult_t
a_t := BranchEvaluation_t
b_t := NodeRewardBreakdown_t
```

- [[SearchInputTruth]]
- [[RequirementExtractionDraft]]
- [[RequirementSheet]]
- [[BusinessPolicyPack]]
- [[GroundingKnowledgeBaseSnapshot]]
- [[KnowledgeRetrievalResult]]
- [[RerankerCalibration]]
- [[ScoringPolicy]]
- [[GroundingDraft]]
- [[GroundingOutput]]
- [[FrontierSeedSpecification]]
- [[FrontierNode_t]]
- [[FrontierState_t]]
- [[SearchControllerContext_t]]
- [[SearchControllerDecisionDraft_t]]
- [[SearchControllerDecision_t]]
- [[SearchExecutionPlan_t]]
- [[SearchExecutionResult_t]]
- [[SearchScoringResult_t]]
- [[BranchEvaluationDraft_t]]
- [[BranchEvaluation_t]]
- [[NodeRewardBreakdown_t]]
- [[FrontierState_t1]]
- [[SearchRunSummaryDraft_t]]
- [[SearchRunResult]]

## 3. Embedded / Child Payloads

- [[CareerStabilityProfile]]
- [[ChildFrontierNodeStub]]
- [[FitGateConstraints]]
- [[GroundingEvidenceCard]]
- [[GroundingKnowledgeCard]]
- [[HardConstraints]]
- [[OperatorStatistics]]
- [[RequirementPreferences]]
- [[RetrievedCandidate_t]]
- [[RuntimeOnlyConstraints]]
- [[ScoringCandidate_t]]
- [[ScoredCandidate_t]]
- [[SearchObservation]]
- [[SearchPageStatistics]]

## 4. Operator 入口

- bootstrap 链：[[ExtractRequirements]] -> [[RetrieveGroundingKnowledge]] -> [[FreezeScoringPolicy]] -> [[GenerateGroundingOutput]] -> [[InitializeFrontierState]]
- 单次扩展链：[[SelectActiveFrontierNode]] -> [[GenerateSearchControllerDecision]] -> [[MaterializeSearchExecutionPlan]] -> [[ExecuteSearchPlan]] -> [[ScoreSearchResults]]
- direct-stop 支路：[[CarryForwardFrontierState]] -> [[EvaluateStopCondition]]
- 闭环：[[EvaluateBranchOutcome]] -> [[ComputeNodeRewardBreakdown]] -> [[UpdateFrontierState]] -> [[EvaluateStopCondition]] -> [[FinalizeSearchRun]]

## 5. Runtime Owner 入口

- [[OperatorCatalog]]
- [[KnowledgeRetrievalBudget]]
- [[RuntimeSearchBudget]]
- [[RuntimeTermBudgetPolicy]]
- [[CrossoverGuardThresholds]]
- [[StopGuardThresholds]]
- [[GroundingCatalog]]
- [[RuntimeRoundState]]
- [[cts-projection-policy]]

## 6. Semantics Owner 入口

- [[requirement-semantics]]
- [[retrieval-semantics]]
- [[grounding-semantics]]
- [[selection-plan-semantics]]
- [[scoring-semantics]]
- [[reward-frontier-semantics]]

## 7. Trace Entry Points

- [[trace-index]]
- [[trace-spec]]
- `traces/agent/*`
- `traces/business/*`
