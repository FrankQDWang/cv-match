<script lang="ts">
	import { resolve } from '$app/paths';
	import { createQuery } from '@tanstack/svelte-query';
	import { safeErrorMessage } from '$lib/api/errors';
	import { listSessions } from '$lib/api/workbench';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import LoadingState from '$lib/components/LoadingState.svelte';
	import { workbenchKeys } from '$lib/query/keys';

	const sessionsQuery = createQuery(() => ({
		queryKey: workbenchKeys.sessions,
		queryFn: listSessions
	}));
</script>

<main class="sessions-page">
	<section class="page-head">
		<p class="eyebrow">会话</p>
		<h1>招聘工作台</h1>
	</section>

	{#if sessionsQuery.isPending}
		<LoadingState label="正在加载会话" />
	{:else if sessionsQuery.error}
		<ErrorState message={safeErrorMessage(sessionsQuery.error, '会话加载失败')} />
	{:else if !sessionsQuery.data?.sessions.length}
		<section class="state-panel">
			<p class="eyebrow">空状态</p>
			<h2>还没有会话</h2>
			<p>请先在现有 Workbench 中创建测试会话，再回来验证 Svelte spike。</p>
		</section>
	{:else}
		<div class="session-grid">
			{#each sessionsQuery.data.sessions as session (session.sessionId)}
				<a class="session-card" href={resolve(`/sessions/${session.sessionId}`)}>
					<span class="status-dot" aria-hidden="true"></span>
					<div>
						<h2>{session.jobTitle || '未命名职位'}</h2>
						<p>{session.notes || session.jdText}</p>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</main>
