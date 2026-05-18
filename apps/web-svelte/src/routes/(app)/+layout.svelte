<script lang="ts">
	import { resolve } from '$app/paths';

	let { children } = $props();
</script>

<div class="app-shell">
	<header class="topbar">
		<a class="brand" href={resolve('/sessions')}>SeekTalent</a>
		<div class="topbar-meta">Svelte 5 Workbench Spike</div>
	</header>
	{@render children()}
</div>
