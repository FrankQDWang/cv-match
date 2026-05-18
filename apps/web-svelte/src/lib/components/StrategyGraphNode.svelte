<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';

	import type { StrategyFlowNode } from '$lib/workbench/strategyGraphLayout';

	let { data }: NodeProps<StrategyFlowNode> = $props();

	const graphNode = $derived(data.graphNode);

	function selectNode() {
		data.onSelectNode?.(graphNode);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key !== 'Enter' && event.key !== ' ') {
			return;
		}
		event.preventDefault();
		selectNode();
	}
</script>

<div class="strategy-flow-node-shell">
	<Handle class="strategy-flow-handle" type="target" position={Position.Left} />
	<div
		class="strategy-flow-node"
		data-testid={`strategy-node-${graphNode.id}`}
		data-tone={graphNode.tone}
		data-kind={graphNode.kind}
		role="button"
		tabindex="0"
		aria-pressed={data.selected}
		onclick={selectNode}
		onkeydown={handleKeydown}
	>
		<span class="node-meta">
			{graphNode.kind}
			{#if graphNode.sourceLabel && graphNode.sourceKind !== 'all'}
				<em>{graphNode.sourceLabel}</em>
			{/if}
		</span>
		<strong>{graphNode.label}</strong>
		<small>{graphNode.detail}</small>
	</div>
	<Handle class="strategy-flow-handle" type="source" position={Position.Right} />
</div>

<style>
	.strategy-flow-node-shell {
		position: relative;
		width: 212px;
		height: 96px;
	}

	.strategy-flow-node {
		display: grid;
		width: 212px;
		height: 96px;
		grid-template-rows: auto auto 1fr;
		gap: 5px;
		padding: 11px 13px;
		border: 1px solid #cbd5e1;
		border-radius: 8px;
		background: #ffffff;
		color: #0f172a;
		text-align: left;
		box-shadow: 0 12px 24px rgb(15 23 42 / 8%);
		cursor: grab;
		user-select: none;
	}

	.strategy-flow-node:hover,
	.strategy-flow-node:focus-visible,
	.strategy-flow-node[aria-pressed='true'] {
		border-color: #0f766e;
		outline: 2px solid color-mix(in srgb, #0f766e 24%, transparent);
		outline-offset: 2px;
	}

	.strategy-flow-node[data-tone='blue'] {
		border-left: 4px solid #2563eb;
	}

	.strategy-flow-node[data-tone='teal'] {
		border-left: 4px solid #0f766e;
	}

	.strategy-flow-node[data-tone='violet'] {
		border-left: 4px solid #7c3aed;
	}

	.strategy-flow-node[data-tone='amber'] {
		border-left: 4px solid #d97706;
	}

	.strategy-flow-node[data-tone='green'] {
		border-left: 4px solid #16a34a;
	}

	.strategy-flow-node[data-tone='rose'] {
		border-left: 4px solid #e11d48;
	}

	.node-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		color: #64748b;
		font-size: 11px;
		font-weight: 700;
		line-height: 1.2;
	}

	.node-meta em {
		max-width: 72px;
		overflow: hidden;
		color: #0f766e;
		font-style: normal;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	strong {
		overflow: hidden;
		font-size: 14px;
		line-height: 1.25;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	small {
		display: -webkit-box;
		overflow: hidden;
		color: #475569;
		font-size: 12px;
		line-height: 1.35;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
	}

	:global(.strategy-flow-handle) {
		width: 8px;
		height: 8px;
		border: 1px solid #ffffff;
		background: #64748b;
	}
</style>
