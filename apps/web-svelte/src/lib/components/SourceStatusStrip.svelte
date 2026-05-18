<script lang="ts">
	import { sourceReasonLabel, sourceStatusLabel } from '$lib/workbench/sourceDisplay';
	import type { WorkbenchSession } from '$lib/workbench/types';

	type Props = {
		session: WorkbenchSession;
	};

	let { session }: Props = $props();
	const runtimeSources = $derived(
		new Map(
			(session.runtimeSourceState?.sources ?? []).map((source) => [source.sourceKind, source])
		)
	);
</script>

<section class="source-status-strip" aria-label="检索源状态">
	{#each session.sourceCards as source (source.sourceRunId)}
		{@const runtime = runtimeSources.get(source.sourceKind)}
		{@const displayStatus = runtime?.status ?? source.status}
		{@const reasonLabel = sourceReasonLabel(
			runtime?.reasonCode ?? source.warningCode ?? source.connectionWarningCode
		)}
		<article class={`source-status-card ${displayStatus}`}>
			<div>
				<p class="eyebrow">{source.label}</p>
				<h2>{sourceStatusLabel(displayStatus)}</h2>
			</div>
			<dl>
				<div>
					<dt>已扫描</dt>
					<dd>{runtime?.cardsSeenCount ?? source.cardsScannedCount}</dd>
				</div>
				<div>
					<dt>候选人</dt>
					<dd>{runtime?.candidatesCount ?? source.uniqueCandidatesCount}</dd>
				</div>
				<div>
					<dt>详情</dt>
					<dd>
						{runtime?.detailRecommendationsCount ??
							source.detailOpenUsedCount}/{source.detailOpenBlockedCount}
					</dd>
				</div>
			</dl>
			{#if source.connectionStatus}
				<p class="source-note">连接：{source.connectionStatus}</p>
			{/if}
			{#if reasonLabel}
				<p class="source-warning">{reasonLabel}</p>
			{/if}
		</article>
	{/each}
</section>
