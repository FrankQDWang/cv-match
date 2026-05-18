<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
</script>

<main class="center-shell">
	<section class="state-panel" aria-labelledby="error-title">
		<p class="eyebrow">SeekTalent Workbench</p>
		<h1 id="error-title">页面暂时不可用</h1>
		<p>{page.status} · 请返回会话列表后重试。</p>
		<a class="button" href={resolve('/sessions')}>返回会话列表</a>
	</section>
</main>
