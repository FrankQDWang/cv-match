import '@testing-library/jest-dom/vitest';

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { NodeDetailPanel } from './NodeDetailPanel';
import type { RecruiterGraphNode } from './recruiterAnimation';

describe('NodeDetailPanel', () => {
  it('renders runtime source state with business labels instead of raw enum values', () => {
    const node: RecruiterGraphNode = {
      id: 'final-shortlist',
      at: 1,
      kind: '排序',
      label: '最终短名单',
      detail: '最高 91 分',
      x: 0,
      y: 0,
      tone: 'green',
      sourceKind: 'all',
      sourceLabel: 'All sources',
      lane: 'shared',
      detailKind: 'aggregation',
      detailPayload: {
        kind: 'aggregation',
        candidateCount: 10,
        bestScore: 91,
        finalReport: null,
        stopReason: null,
        coverageStatus: 'degraded',
        finalizationRevision: 1,
        finalizationReasonCode: 'source_lanes_degraded',
        identityMergeCount: 2,
        ambiguousDuplicateCount: 1,
        canonicalResumeSelectedCount: 9,
        sourceStates: [
          {
            sourceKind: 'liepin',
            status: 'partial',
            eventType: 'detail_recommended',
            eventSeq: 4,
            cardsSeenCount: 30,
            cardsFilteredCount: 8,
            candidatesCount: 5,
            detailRecommendationsCount: 4,
            detailState: 'detail_recommended',
          },
        ],
      },
    };

    render(<NodeDetailPanel node={node} />);

    expect(screen.getByText('覆盖不完整')).toBeInTheDocument();
    expect(screen.getByText('部分渠道不可用')).toBeInTheDocument();
    expect(screen.getByText(/Liepin · 部分完成 · 已扫描 30 · 已过滤 8 · 候选人 5 · 详情推荐 4 · 已推荐详情/)).toBeInTheDocument();
    expect(screen.queryByText('degraded')).not.toBeInTheDocument();
    expect(screen.queryByText('source_lanes_degraded')).not.toBeInTheDocument();
    expect(screen.queryByText('detail_recommended')).not.toBeInTheDocument();
  });
});
