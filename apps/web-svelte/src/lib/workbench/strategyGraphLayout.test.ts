import { afterEach, describe, expect, it } from 'vitest';

import type { RecruiterGraphEdge, RecruiterGraphNode } from './recruiterAnimation';
import {
	disposeStrategyGraphLayoutRunner,
	fallbackLayout,
	layoutStrategyGraph,
	mergeManualNodePositions,
	setStrategyGraphLayoutRunnerForTests
} from './strategyGraphLayout';

const bounds = { width: 900, height: 520 };

const nodes: RecruiterGraphNode[] = [
	baseNode({ id: 'job', label: '岗位需求', lane: 'shared', x: 10, y: 50 }),
	baseNode({ id: 'requirements', label: '需求拆解', lane: 'shared', x: 24, y: 50 }),
	baseNode({ id: 'cts-round-1-query', label: '第 1 轮关键词', lane: 'cts', x: 42, y: 24 }),
	baseNode({ id: 'final-shortlist', label: '最终短名单', lane: 'shared', x: 94, y: 50 })
];

const edges: RecruiterGraphEdge[] = [
	{ from: 'job', to: 'requirements', tone: 'blue', label: '提取约束' },
	{ from: 'requirements', to: 'cts-round-1-query', tone: 'teal', label: '生成关键词' },
	{ from: 'cts-round-1-query', to: 'final-shortlist', tone: 'green', label: '聚合排序' }
];

afterEach(() => {
	disposeStrategyGraphLayoutRunner();
});

describe('strategy graph layout', () => {
	it('uses the injected ELK runner and returns business-facing Svelte Flow nodes', async () => {
		expect.assertions(5);
		let callCount = 0;
		setStrategyGraphLayoutRunnerForTests(async (graph) => {
			callCount += 1;
			return {
				...graph,
				children: (graph.children ?? []).map((child, index) => ({
					...child,
					x: index * 180,
					y: index * 40
				}))
			};
		});

		const graph = await layoutStrategyGraph(nodes, edges, bounds);

		expect(callCount).toBe(1);
		expect(graph.nodes).toHaveLength(nodes.length);
		expect(graph.nodes[0]?.type).toBe('strategy');
		expect(graph.nodes[0]?.data.graphNode.label).toBe('岗位需求');
		expect(graph.edges.map((edge) => edge.id)).toEqual([
			'job->requirements',
			'requirements->cts-round-1-query',
			'cts-round-1-query->final-shortlist'
		]);
	});

	it('falls back to deterministic business workflow positions', () => {
		expect.assertions(3);

		const graph = fallbackLayout(nodes, edges, bounds);
		const job = graph.nodes.find((node) => node.id === 'job');
		const requirements = graph.nodes.find((node) => node.id === 'requirements');
		const final = graph.nodes.find((node) => node.id === 'final-shortlist');

		expect(job?.position.x).toBeLessThan(requirements?.position.x ?? 0);
		expect(requirements?.position.x).toBeLessThan(final?.position.x ?? 0);
		expect(new Set(graph.nodes.map((node) => `${node.position.x}:${node.position.y}`)).size).toBe(
			graph.nodes.length
		);
	});

	it('keeps manual node positions only while graph identity stays stable', () => {
		expect.assertions(4);
		const current = new Map([
			['job', { x: 10, y: 20 }],
			['requirements', { x: 30, y: 40 }]
		]);
		const manual = new Map([['requirements', { x: 200, y: 210 }]]);

		const stable = mergeManualNodePositions({
			current,
			manual,
			currentGraphIdentity: 'session:a',
			nextGraphIdentity: 'session:a',
			nextNodeIds: ['job', 'requirements']
		});
		const changed = mergeManualNodePositions({
			current,
			manual,
			currentGraphIdentity: 'session:a',
			nextGraphIdentity: 'session:b',
			nextNodeIds: ['job', 'requirements']
		});

		expect(stable.positions.get('requirements')).toEqual({ x: 200, y: 210 });
		expect(stable.manualPositions.size).toBe(1);
		expect(changed.positions.get('requirements')).toEqual({ x: 30, y: 40 });
		expect(changed.manualPositions.size).toBe(0);
	});
});

function baseNode(input: {
	id: string;
	label: string;
	lane: NonNullable<RecruiterGraphNode['lane']>;
	x: number;
	y: number;
}): RecruiterGraphNode {
	return {
		id: input.id,
		at: 0,
		kind: input.id === 'final-shortlist' ? '排序' : input.id === 'requirements' ? '拆解' : '岗位',
		label: input.label,
		detail: input.label,
		x: input.x,
		y: input.y,
		tone: 'blue',
		sourceKind: input.lane === 'cts' || input.lane === 'liepin' ? input.lane : 'all',
		sourceLabel: input.lane === 'cts' ? 'CTS' : 'All sources',
		lane: input.lane,
		eventIds: [],
		sourceRunId: null,
		candidateReviewItemIds: [],
		candidateEvidenceRefs: [],
		detailOpenRequestIds: []
	};
}
