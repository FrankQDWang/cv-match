<script lang="ts">
	import { readinessStatusLabel, readinessTone } from '$lib/workbench/sourceDisplay';
	import type { WorkbenchDevModeStatus } from '$lib/workbench/types';

	type Props = {
		status: WorkbenchDevModeStatus | null;
		loading?: boolean;
		error?: string | null;
	};

	let { status, loading = false, error = null }: Props = $props();
	const items = $derived(status?.components ?? []);
</script>

<section class="readiness-panel" aria-labelledby="readiness-title">
	<div>
		<p class="eyebrow">Dev mode BYOK</p>
		<h2 id="readiness-title">本地运行准备</h2>
	</div>
	{#if loading}
		<p>正在检查本地配置。</p>
	{:else if error}
		<p class="form-error">{error}</p>
	{:else if !status}
		<p>暂未读取准备状态。</p>
	{:else}
		<div class="readiness-grid">
			{#each items as item (item.name)}
				<article class={`readiness-item ${readinessTone(item.status)}`}>
					<div>
						<strong>{item.label}</strong>
						{#if item.authNote ?? item.reasonCode}
							<p>{item.authNote ?? item.reasonCode}</p>
						{/if}
					</div>
					<span>{readinessStatusLabel(item.status)}</span>
				</article>
			{/each}
		</div>
	{/if}
</section>
