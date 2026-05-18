<script lang="ts">
	import type { WorkbenchSession } from '$lib/workbench/types';

	type Props = {
		session: WorkbenchSession;
	};

	let { session }: Props = $props();
	const liepinSource = $derived(
		session.runtimeSourceState?.sources.find((source) => source.sourceKind === 'liepin')
	);
</script>

<section class="detail-recommendation-panel" aria-labelledby="detail-recommendation-title">
	<p class="eyebrow">Liepin detail budget</p>
	<h2 id="detail-recommendation-title">详情推荐</h2>
	{#if liepinSource}
		<dl>
			<div>
				<dt>推荐</dt>
				<dd>{liepinSource.detailRecommendationsCount}</dd>
			</div>
			<div>
				<dt>状态</dt>
				<dd>{liepinSource.detailState ?? '无详情推荐'}</dd>
			</div>
			<div>
				<dt>已扫描</dt>
				<dd>{liepinSource.cardsSeenCount}</dd>
			</div>
			<div>
				<dt>已过滤</dt>
				<dd>{liepinSource.cardsFilteredCount}</dd>
			</div>
		</dl>
	{:else}
		<p>当前会话未选择 Liepin。</p>
	{/if}
</section>
