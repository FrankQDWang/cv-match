import { afterEach, describe, expect, it } from 'vitest';

import {
  disposeStrategyGraphLayoutRunner,
  fallbackLayout,
  layoutStrategyGraph,
  setStrategyGraphLayoutRunnerForTests,
  stackLanePositions,
  toElkGraph,
} from './strategyGraphLayout';
import type { RecruiterGraphEdge, RecruiterGraphNode, RecruiterLane } from './recruiterAnimation';

const bounds = { width: 900, height: 500 };

function graphNode(id: string, lane: RecruiterLane, x: number, y: number): RecruiterGraphNode {
  return {
    id,
    at: 1,
    kind: '检索',
    label: id,
    detail: id,
    x,
    y,
    tone: 'blue',
    lane,
  };
}

describe('strategy graph layout', () => {
  afterEach(() => {
    disposeStrategyGraphLayoutRunner();
  });

  it('builds an ELK layered LTR graph without lane partitions', () => {
    const nodes = [
      graphNode('job', 'shared', 0.08, 0.42),
      graphNode('requirements', 'shared', 0.24, 0.42),
      graphNode('cts-query', 'cts', 0.4, 0.22),
    ];
    const edges: RecruiterGraphEdge[] = [
      { from: 'job', to: 'requirements', tone: 'neutral' },
      { from: 'requirements', to: 'cts-query', tone: 'blue' },
    ];

    const graph = toElkGraph(nodes, edges);
    const ctsQuery = graph.children?.find((child) => child.id === 'cts-query');

    expect(graph.layoutOptions?.['elk.algorithm']).toBe('layered');
    expect(graph.layoutOptions?.['elk.direction']).toBe('RIGHT');
    expect(ctsQuery).toBeDefined();
    expect(ctsQuery?.layoutOptions).toBeUndefined();
    expect(graph.edges?.[0]).toEqual({
      id: 'job->requirements',
      sources: ['job'],
      targets: ['requirements'],
    });
  });

  it('stacks CTS and Liepin lanes vertically after preserving ELK x positions', () => {
    const nodes = [
      graphNode('cts-query', 'cts', 0.42, 0.22),
      graphNode('liepin-search', 'liepin', 0.42, 0.62),
      graphNode('final-shortlist', 'shared', 0.8, 0.42),
    ];
    const positions = stackLanePositions(
      new Map([
        ['cts-query', { x: 120, y: 100 }],
        ['liepin-search', { x: 120, y: 100 }],
        ['final-shortlist', { x: 300, y: 100 }],
      ]),
      nodes,
      bounds,
    );
    const cts = positions.get('cts-query');
    const liepin = positions.get('liepin-search');
    const final = positions.get('final-shortlist');

    expect(cts).toBeDefined();
    expect(liepin).toBeDefined();
    expect(final).toBeDefined();
    expect(cts?.y).toBeLessThan(liepin?.y ?? 0);
    expect(cts?.x).toBe(liepin?.x);
    expect(final?.x).toBeGreaterThan(cts?.x ?? 0);
    expect(final?.x).toBeGreaterThan(liepin?.x ?? 0);
  });

  it('uses the injected ELK runner and then stacks source lanes', async () => {
    const nodes = [
      graphNode('cts-query', 'cts', 0.42, 0.22),
      graphNode('liepin-search', 'liepin', 0.42, 0.62),
      graphNode('final-shortlist', 'shared', 0.8, 0.42),
    ];
    const edges: RecruiterGraphEdge[] = [
      { from: 'cts-query', to: 'final-shortlist', tone: 'blue' },
      { from: 'liepin-search', to: 'final-shortlist', tone: 'green' },
    ];
    setStrategyGraphLayoutRunnerForTests(async (graph) => ({
      ...graph,
      children: [
        { id: 'cts-query', x: 120, y: 100, width: 168, height: 74 },
        { id: 'liepin-search', x: 120, y: 100, width: 168, height: 74 },
        { id: 'final-shortlist', x: 360, y: 100, width: 168, height: 74 },
      ],
    }));

    const layout = await layoutStrategyGraph(nodes, edges, bounds);
    const cts = layout.nodes.find((node) => node.id === 'cts-query');
    const liepin = layout.nodes.find((node) => node.id === 'liepin-search');

    expect(cts?.position.y).toBeLessThan(liepin?.position.y ?? 0);
    expect(cts?.position.x).toBe(liepin?.position.x);
  });

  it('falls back when ELK rejects or returns no child positions', async () => {
    const nodes = [graphNode('cts-query', 'cts', 0.42, 0.22)];
    const edges: RecruiterGraphEdge[] = [];
    setStrategyGraphLayoutRunnerForTests(async () => {
      throw new Error('layout failed');
    });

    const rejectedLayout = await layoutStrategyGraph(nodes, edges, bounds);
    expect(rejectedLayout.nodes[0]?.position.y).toBe(0.22 * (bounds.height - 74));

    setStrategyGraphLayoutRunnerForTests(async (graph) => ({ ...graph, children: [] }));
    const emptyLayout = await layoutStrategyGraph(nodes, edges, bounds);
    expect(emptyLayout.nodes[0]?.position.y).toBe(0.22 * (bounds.height - 74));
  });

  it('preserves raw y positions when only one source lane is visible', () => {
    const nodes = [graphNode('cts-query', 'cts', 0.42, 0.22)];
    const positions = stackLanePositions(new Map([['cts-query', { x: 120, y: 123 }]]), nodes, bounds);

    expect(positions.get('cts-query')?.y).toBe(123);
  });

  it('uses lane-stacked positions in fallback layout', () => {
    const nodes = [
      graphNode('cts-query', 'cts', 0.42, 0.22),
      graphNode('liepin-search', 'liepin', 0.42, 0.62),
      graphNode('final-shortlist', 'shared', 0.8, 0.42),
    ];
    const edges: RecruiterGraphEdge[] = [{ from: 'cts-query', to: 'final-shortlist', tone: 'blue' }];

    const layout = fallbackLayout(nodes, edges, bounds);
    const cts = layout.nodes.find((node) => node.id === 'cts-query');
    const liepin = layout.nodes.find((node) => node.id === 'liepin-search');
    const final = layout.nodes.find((node) => node.id === 'final-shortlist');

    expect(cts).toBeDefined();
    expect(liepin).toBeDefined();
    expect(final).toBeDefined();
    expect(cts?.width).toBe(168);
    expect(cts?.height).toBe(74);
    expect(cts?.position.y).toBeLessThan(liepin?.position.y ?? 0);
    expect(cts?.position.x).toBe(liepin?.position.x);
    expect(cts?.selected).toBe(false);
    expect(cts?.data.selected).toBe(false);
    expect(cts?.draggable).toBe(true);
    expect(final?.position.x).toBe(bounds.width - 168 - 34);
  });

  it('lays out CTS rounds as repeating workflow rows that can extend beyond the viewport', () => {
    const compactBounds = { width: 520, height: 360 };
    const nodes = [
      graphNode('cts-round-1-query', 'cts', 0.42, 0.22),
      graphNode('cts-round-1-result', 'cts', 0.52, 0.22),
      graphNode('cts-round-1-score', 'cts', 0.62, 0.22),
      graphNode('cts-round-1-reflect', 'cts', 0.72, 0.22),
      graphNode('cts-round-2-query', 'cts', 0.42, 0.32),
      graphNode('cts-round-2-result', 'cts', 0.52, 0.32),
      graphNode('cts-round-6-query', 'cts', 0.42, 0.72),
    ];

    const layout = fallbackLayout(nodes, [], compactBounds);
    const round1Query = layout.nodes.find((node) => node.id === 'cts-round-1-query');
    const round1Result = layout.nodes.find((node) => node.id === 'cts-round-1-result');
    const round1Reflect = layout.nodes.find((node) => node.id === 'cts-round-1-reflect');
    const round2Query = layout.nodes.find((node) => node.id === 'cts-round-2-query');
    const round2Result = layout.nodes.find((node) => node.id === 'cts-round-2-result');
    const round6Query = layout.nodes.find((node) => node.id === 'cts-round-6-query');

    expect(round1Query?.position.x).toBe(round2Query?.position.x);
    expect(round1Result?.position.x).toBe(round2Result?.position.x);
    expect(round1Result?.position.x).toBeGreaterThan(round1Query?.position.x ?? 0);
    expect(round1Reflect?.position.x).toBeGreaterThan(round1Result?.position.x ?? 0);
    expect(round2Query?.position.y).toBeGreaterThan(round1Query?.position.y ?? 0);
    expect(round6Query?.position.y).toBeGreaterThan(compactBounds.height);
  });

  it('keeps fallback nodes inside a narrow responsive canvas', () => {
    const narrowBounds = { width: 371, height: 560 };
    const nodes = [
      graphNode('job', 'shared', 0.08, 0.42),
      graphNode('requirements', 'shared', 0.24, 0.42),
      graphNode('cts-query', 'cts', 0.42, 0.22),
      graphNode('liepin-search', 'liepin', 0.42, 0.62),
      graphNode('final-shortlist', 'shared', 0.8, 0.42),
    ];
    const edges: RecruiterGraphEdge[] = [
      { from: 'job', to: 'requirements', tone: 'neutral' },
      { from: 'requirements', to: 'cts-query', tone: 'blue' },
      { from: 'requirements', to: 'liepin-search', tone: 'green' },
      { from: 'cts-query', to: 'final-shortlist', tone: 'blue' },
      { from: 'liepin-search', to: 'final-shortlist', tone: 'green' },
    ];

    const layout = fallbackLayout(nodes, edges, narrowBounds);

    for (const node of layout.nodes) {
      expect(node.position.x).toBeGreaterThanOrEqual(0);
      expect(node.position.x + 168).toBeLessThanOrEqual(narrowBounds.width);
      expect(node.position.y).toBeGreaterThanOrEqual(0);
      expect(node.position.y + 74).toBeLessThanOrEqual(narrowBounds.height);
    }
  });
});
