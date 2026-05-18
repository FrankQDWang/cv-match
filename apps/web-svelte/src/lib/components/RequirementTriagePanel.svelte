<script lang="ts">
	import type { WorkbenchSession } from '$lib/workbench/types';

	type VisibleTriage = Pick<
		WorkbenchSession['requirementTriage'],
		| 'status'
		| 'mustHaves'
		| 'niceToHaves'
		| 'synonyms'
		| 'seniorityFilters'
		| 'exclusions'
		| 'generatedQueryHints'
	>;
	type Props = {
		session: { requirementTriage: VisibleTriage };
	};

	let { session }: Props = $props();
	const triage = $derived(session.requirementTriage);
	const sections = $derived([
		['必须条件', triage.mustHaves],
		['加分项', triage.niceToHaves],
		['同义词', triage.synonyms],
		['年限/职级过滤', triage.seniorityFilters],
		['排除项', triage.exclusions],
		['检索提示', triage.generatedQueryHints]
	] as const);
	const hasCriteria = $derived(sections.some(([, values]) => values.length > 0));
</script>

<section class="triage-panel" aria-labelledby="triage-title">
	<div>
		<p class="eyebrow">需求确认</p>
		<h2 id="triage-title">检索标准</h2>
	</div>
	{#if !hasCriteria}
		<p class="empty-state">先生成标准，再确认并启动检索。</p>
	{:else}
		<div class="triage-grid">
			{#each sections as [label, values] (label)}
				<section>
					<h3>{label}</h3>
					{#if values.length > 0}
						<ul>
							{#each values as value (value)}
								<li>{value}</li>
							{/each}
						</ul>
					{:else}
						<p>暂无</p>
					{/if}
				</section>
			{/each}
		</div>
	{/if}
</section>
