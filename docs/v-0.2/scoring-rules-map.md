# v0.2 Scoring Rules Map

This document summarizes the current `v0.2` scoring semantics in a diagram-first form.

Source of truth:

- Prompt: [scoring.md](/Users/frankqdwang/Agents/cv-match/src/cv_match/prompts/scoring.md)
- Input and output models: [models.py](/Users/frankqdwang/Agents/cv-match/src/cv_match/models.py)

## 1. Decision Flow

```mermaid
flowchart TD
    A["Input: ScoringContext
    - ScoringPolicy
    - one NormalizedResume"] --> B["Read only this role-specific context"]
    B --> C{"Critical must-haves supported
    and no clear fatal conflict?"}
    C -- "No" --> D["fit_bucket = not_fit"]
    C -- "Yes" --> E["Provisional fit"]
    E --> F{"Evidence still too weak
    or conflict/exclusion remains?"}
    F -- "Yes" --> D
    F -- "No" --> G["fit_bucket = fit"]

    D --> H["Assign scores consistent with not_fit"]
    G --> I["Assign scores consistent with fit"]

    H --> J["Set must_have_match_score"]
    I --> J
    J --> K["Set preferred_match_score"]
    K --> L["Set risk_score
    - missing evidence raises risk
    - exclusions/conflicts raise risk"]
    L --> M["Set overall_score
    consistent with fit_bucket"]
    M --> N["Write concise reasoning_summary
    and evidence"]
    N --> O["Output: ScoredCandidate"]
```

## 2. Scoring Mind Map

```mermaid
mindmap
  root((Single Resume Scoring))
    Input
      ScoringPolicy
        role_title
        role_summary
        must_have_capabilities
        preferred_capabilities
        exclusion_signals
        hard_constraints
        preferences
        scoring_rationale
      NormalizedResume
        one resume only
    Core rules
      fit_bucket first
      no cross-candidate comparison
      no generic market standard
      no invented facts
      missing evidence increases risk
      strong background alone does not upgrade to fit
    fit
      enough must-have evidence
      no clear fatal conflict
      no clear exclusion hit
    not_fit
      critical must-have missing
      hard conflict is clear
      evidence too weak
    Scores
      must_have_match_score
      preferred_match_score
      risk_score
      overall_score
      confidence
    Evidence outputs
      matched_must_haves
      missing_must_haves
      matched_preferences
      negative_signals
      risk_flags
      strengths
      weaknesses
      reasoning_summary
```

## 3. Output Shape

```mermaid
flowchart LR
    A["ScoredCandidate"] --> B["fit_bucket
    fit | not_fit"]
    A --> C["overall_score
    0-100"]
    A --> D["must_have_match_score
    0-100"]
    A --> E["preferred_match_score
    0-100"]
    A --> F["risk_score
    0-100"]
    A --> G["confidence
    high | medium | low"]
    A --> H["reasoning_summary
    short"]
    A --> I["evidence
    grounded in resume"]
    A --> J["matched_must_haves"]
    A --> K["missing_must_haves"]
    A --> L["matched_preferences"]
    A --> M["negative_signals"]
    A --> N["risk_flags"]
    A --> O["strengths / weaknesses"]
```

## 4. Score Bands

Current prompt guidance:

- `90-100`: highly aligned
- `75-89`: strong
- `60-74`: mixed
- `40-59`: borderline
- `<40`: weak

These bands are guidance for consistency, not a replacement for `fit_bucket`.

## 5. Non-Rules

These are explicitly *not* part of scoring:

- No comparison against other candidates
- No use of generic market benchmarks
- No promotion to `fit` just because the resume looks broadly strong
- No assumptions beyond the provided resume evidence
