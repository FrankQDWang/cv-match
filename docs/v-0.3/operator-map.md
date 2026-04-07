# SeekTalent v0.3 交互式数据流导图

> 本页是 `Obsidian` 导航入口。
> 它只提供单次 expansion 的主链导航，不重复定义字段级 contract。
> payload 的字段定义以 `payloads/` 为准，operator 的 read/write set 以 `operators/` 为准。

## 0. 阅读约定

1. 蓝色节点是 stable payload。
2. 绿色节点是 operator。
3. 粉色节点是 LLM / draft，不作为 canonical owner。
4. 带 `internal-link` 的节点可在 `Obsidian` 中直接点开对应 note。

## 1. 单次 Expansion 数据依赖图

```mermaid
flowchart TD
    subgraph B["Bootstrap"]
        SIT["SearchInputTruth"] -->|extract| RELLM["RequirementExtractionLLM"]
        RELLM -->|draft| RED["RequirementExtractionDraft"]
        RED -->|normalize| ER["ExtractRequirements"]
        ER -->|truth| RS["RequirementSheet"]

        RS -->|freeze| FSP["FreezeScoringPolicy"]
        FSP -->|policy| SP["ScoringPolicy"]

        RS -->|ground| GLLM["GroundingGenerationLLM"]
        GLLM -->|draft| GD["GroundingDraft"]
        GD -->|normalize| GGO["GenerateGroundingOutput"]
        GGO -->|grounding| GO["GroundingOutput"]

        GO -->|grounding| IFS
        IFS -->|frontier| FS0["FrontierState_t"]
    end

    subgraph E["Single Expansion"]
        FS0 -->|select + pack| SAFN["SelectActiveFrontierNode"]
        RS -->|truth| SAFN
        SP -->|policy| SAFN
        SAFN -->|context| SCC["SearchControllerContext_t"]

        SCC -->|infer| SCDLLM["SearchControllerDecisionLLM"]
        SCDLLM -->|normalize| GSCD["GenerateSearchControllerDecision"]
        GSCD -->|decision| SCD["SearchControllerDecision_t"]

        FS0 -->|carry forward| CFFS["CarryForwardFrontierState"]
        CFFS -->|frontier'| FS1

        FS0 -->|active node| MSEP["MaterializeSearchExecutionPlan"]
        RS -->|constraints| MSEP
        SCD -->|patch| MSEP
        MSEP -->|plan| SEP["SearchExecutionPlan_t"]

        SEP -->|execute| ESP["ExecuteSearchPlan"]
        ESP -->|results| SER["SearchExecutionResult_t"]

        SER -->|judge| SSLLM["SearchScoringLLM"]
        SP -->|policy| SSR["ScoreSearchResults"]
        SSLLM -->|normalize| SSR
        SSR -->|scored| SSC["SearchScoringResult_t"]

        RS -->|requirements| BEVLLM["BranchOutcomeEvaluationLLM"]
        FS0 -->|branch| BEVLLM
        SEP -->|plan| BEVLLM
        SER -->|telemetry| BEVLLM
        SSC -->|scores| BEVLLM
        BEVLLM -->|normalize| EBO["EvaluateBranchOutcome"]
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
        UFS -->|frontier'| FS1["FrontierState_t1"]

        FS1 -->|guard| ESC["EvaluateStopCondition"]
        SCD -->|controller action| ESC
        BE -->|branch state| ESC
        NRB -->|reward| ESC
    end

    subgraph F["Search Run Finalization"]
        RS -->|truth| SRFLLM["SearchRunFinalizationLLM"]
        FS1 -->|frontier| SRFLLM
        ESC -->|stop_reason| SRFLLM
        SRFLLM -->|normalize| FSR["FinalizeSearchRun"]
        FSR -->|result| SRR["SearchRunResult"]
    end

    classDef payload fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1.5px;
    classDef operator fill:#dcfce7,stroke:#15803d,color:#14532d,stroke-width:1.5px;
    classDef llm fill:#fce7f3,stroke:#db2777,color:#4a044e,stroke-width:1.5px;

    class SIT,RED,RS,SP,GD,GO,FS0,SCC,SCD,SEP,SER,SSC,BE,NRB,FS1,SRR payload;
    class ER,FSP,GGO,IFS,SAFN,GSCD,CFFS,MSEP,ESP,SSR,EBO,CNRB,UFS,ESC,FSR operator;
    class RELLM,GLLM,SCDLLM,SSLLM,BEVLLM,SRFLLM llm;

    class SIT,RED,RS,SP,GD,GO,FS0,SCC,SCD,SEP,SER,SSC,BE,NRB,FS1,SRR internal-link;
    class ER,FSP,GGO,IFS,SAFN,GSCD,CFFS,MSEP,ESP,SSR,EBO,CNRB,UFS,ESC,FSR internal-link;
```

## 2. Payload 入口

公式与 trace 中使用的短记号映射如下：

```text
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
- [[ScoringPolicy]]
- [[GroundingDraft]]
- [[GroundingOutput]]
- [[GroundingEvidenceCard]]
- [[FrontierSeedSpecification]]
- [[FrontierState_t]]
- [[SearchControllerContext_t]]
- [[SearchControllerDecision_t]]
- [[SearchExecutionPlan_t]]
- [[SearchExecutionResult_t]]
- [[SearchScoringResult_t]]
- [[BranchEvaluation_t]]
- [[NodeRewardBreakdown_t]]
- [[FrontierState_t1]]
- [[SearchRunResult]]

## 3. Operator 入口

- 初始化链：[[ExtractRequirements]] -> [[FreezeScoringPolicy]] -> [[GenerateGroundingOutput]] -> [[InitializeFrontierState]]
- 单次扩展链：[[SelectActiveFrontierNode]] -> [[GenerateSearchControllerDecision]] -> [[MaterializeSearchExecutionPlan]] -> [[ExecuteSearchPlan]] -> [[ScoreSearchResults]]
- direct-stop 支路：[[CarryForwardFrontierState]] -> [[EvaluateStopCondition]]
- 闭环：[[EvaluateBranchOutcome]] -> [[ComputeNodeRewardBreakdown]] -> [[UpdateFrontierState]] -> [[EvaluateStopCondition]] -> [[FinalizeSearchRun]]
