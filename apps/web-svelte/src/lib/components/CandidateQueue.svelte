<script lang="ts">
	import type { WorkbenchFinalTopCandidate } from '$lib/workbench/types';

	type Props = {
		items: WorkbenchFinalTopCandidate[];
		loading?: boolean;
		error?: string | null;
	};

	let { items, loading = false, error = null }: Props = $props();
</script>

<section class="candidate-queue" aria-labelledby="candidate-queue-title">
	<div>
		<p class="eyebrow">Top 10</p>
		<h2 id="candidate-queue-title">候选人队列</h2>
	</div>
	{#if loading}
		<p>正在加载候选人。</p>
	{:else if error}
		<p class="form-error">{error}</p>
	{:else if items.length === 0}
		<p>检索完成后会在这里显示统一排序候选人。</p>
	{:else}
		<ol>
			{#each items as item (item.runtimeIdentityId)}
				<li>
					<span class="rank">{item.rank}</span>
					<div>
						<strong>{item.displayName || '候选人'}</strong>
						<p>
							{item.title || '暂无标题'} · {item.company || '公司未知'} · {item.location ||
								'地点未知'}
						</p>
						{#if item.summary}<small>{item.summary}</small>{/if}
						<div class="source-badges" aria-label="候选人来源">
							{#each item.sourceBadges as badge (badge)}
								<span>{badge}</span>
							{/each}
							<span>{item.evidenceLevel}</span>
						</div>
					</div>
					{#if item.aggregateScore !== null && item.aggregateScore !== undefined}
						<span class="score">{item.aggregateScore}</span>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</section>
