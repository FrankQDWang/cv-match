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
	type RunControlSession = {
		requirementTriage: VisibleTriage;
		sourceRuns: Array<Pick<WorkbenchSession['sourceRuns'][number], 'status'>>;
	};
	type Props = {
		session: RunControlSession;
		preparing?: boolean;
		approving?: boolean;
		starting?: boolean;
		error?: string | null;
		onPrepare: () => void;
		onApprove: () => void;
		onStart: () => void;
	};

	let {
		session,
		preparing = false,
		approving = false,
		starting = false,
		error = null,
		onPrepare,
		onApprove,
		onStart
	}: Props = $props();

	const triageApproved = $derived(session.requirementTriage.status === 'approved');
	const hasVisibleCriteria = $derived(
		session.requirementTriage.mustHaves.length > 0 ||
			session.requirementTriage.niceToHaves.length > 0 ||
			session.requirementTriage.synonyms.length > 0 ||
			session.requirementTriage.seniorityFilters.length > 0 ||
			session.requirementTriage.exclusions.length > 0 ||
			session.requirementTriage.generatedQueryHints.length > 0
	);
	const hasActiveSource = $derived(session.sourceRuns.some((run) => run.status === 'running'));
</script>

<section class="run-control-panel" aria-labelledby="run-control-title">
	<div>
		<p class="eyebrow">运行控制</p>
		<h2 id="run-control-title">确认标准并启动检索</h2>
	</div>
	<div class="run-control-actions">
		<button class="button secondary" type="button" disabled={preparing} onclick={onPrepare}>
			{preparing ? '正在生成标准' : '生成标准'}
		</button>
		<button
			class="button secondary"
			type="button"
			disabled={approving || triageApproved || !hasVisibleCriteria}
			onclick={onApprove}
		>
			{triageApproved ? '标准已确认' : approving ? '正在确认' : '确认标准'}
		</button>
		<button
			class="button"
			type="button"
			disabled={starting || !triageApproved || !hasVisibleCriteria || hasActiveSource}
			onclick={onStart}
		>
			{starting ? '正在启动' : '启动双源检索'}
		</button>
	</div>
	{#if error}<p class="form-error">{error}</p>{/if}
</section>
