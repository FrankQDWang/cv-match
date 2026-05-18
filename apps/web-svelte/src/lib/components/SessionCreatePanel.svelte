<script lang="ts">
	import { selectedSourceKinds } from '$lib/workbench/sourceDisplay';
	import type { WorkbenchSessionCreateInput } from '$lib/workbench/types';

	type Props = {
		creating?: boolean;
		error?: string | null;
		onCreate: (input: WorkbenchSessionCreateInput) => void;
	};

	let { creating = false, error = null, onCreate }: Props = $props();
	let jobTitle = $state('');
	let jdText = $state('');
	let notes = $state('');
	let ctsSelected = $state(true);
	let liepinSelected = $state(true);
	const canCreate = $derived(
		jobTitle.trim().length > 0 && jdText.trim().length > 0 && (ctsSelected || liepinSelected)
	);

	function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!canCreate || creating) {
			return;
		}
		onCreate({
			jobTitle: jobTitle.trim(),
			jdText: jdText.trim(),
			notes: notes.trim(),
			sourceKinds: selectedSourceKinds({ cts: ctsSelected, liepin: liepinSelected })
		});
	}
</script>

<section class="session-create-panel" aria-labelledby="session-create-title">
	<div>
		<p class="eyebrow">New search</p>
		<h2 id="session-create-title">创建双源检索</h2>
	</div>
	<form class="session-create-form" onsubmit={submit}>
		<label>
			<span>职位名称</span>
			<input bind:value={jobTitle} name="jobTitle" autocomplete="off" />
		</label>
		<label>
			<span>JD</span>
			<textarea bind:value={jdText} name="jdText" rows="6"></textarea>
		</label>
		<label>
			<span>补充说明</span>
			<textarea bind:value={notes} name="notes" rows="3"></textarea>
		</label>
		<div class="source-selector" aria-label="检索源">
			<label><input type="checkbox" bind:checked={ctsSelected} /> CTS</label>
			<label><input type="checkbox" bind:checked={liepinSelected} /> Liepin</label>
		</div>
		<button class="button" type="submit" disabled={!canCreate || creating}>
			{creating ? '正在创建' : '创建会话'}
		</button>
		{#if error}
			<p class="form-error">{error}</p>
		{/if}
	</form>
</section>
