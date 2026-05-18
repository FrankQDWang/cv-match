<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { createQuery } from '@tanstack/svelte-query';
	import { safeErrorMessage } from '$lib/api/errors';
	import { createSession, getDevModeStatus, listSessions } from '$lib/api/workbench';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import LoadingState from '$lib/components/LoadingState.svelte';
	import ReadinessPanel from '$lib/components/ReadinessPanel.svelte';
	import SessionCreatePanel from '$lib/components/SessionCreatePanel.svelte';
	import { workbenchKeys } from '$lib/query/keys';
	import type { WorkbenchSessionCreateInput } from '$lib/workbench/types';

	let creating = $state(false);
	let createError = $state<string | null>(null);

	const sessionsQuery = createQuery(() => ({
		queryKey: workbenchKeys.sessions,
		queryFn: listSessions
	}));

	const devModeQuery = createQuery(() => ({
		queryKey: workbenchKeys.devModeStatus,
		queryFn: getDevModeStatus
	}));

	async function handleCreate(input: WorkbenchSessionCreateInput) {
		creating = true;
		createError = null;
		try {
			const session = await createSession(input);
			await goto(resolve(`/sessions/${session.sessionId}`));
		} catch (error) {
			createError = safeErrorMessage(error, '会话创建失败');
		} finally {
			creating = false;
		}
	}
</script>

<main class="sessions-page">
	<section class="page-head">
		<p class="eyebrow">会话</p>
		<h1>招聘工作台</h1>
	</section>

	<section class="sessions-workbench-layout">
		<ReadinessPanel
			status={devModeQuery.data ?? null}
			loading={devModeQuery.isPending}
			error={devModeQuery.error ? safeErrorMessage(devModeQuery.error, '准备状态加载失败') : null}
		/>
		<SessionCreatePanel {creating} error={createError} onCreate={handleCreate} />
	</section>

	{#if sessionsQuery.isPending}
		<LoadingState label="正在加载会话" />
	{:else if sessionsQuery.error}
		<ErrorState message={safeErrorMessage(sessionsQuery.error, '会话加载失败')} />
	{:else if !sessionsQuery.data?.sessions.length}
		<section class="state-panel">
			<p class="eyebrow">空状态</p>
			<h2>还没有会话</h2>
			<p>创建一个本地 BYOK 检索会话后，候选人队列会在这里出现。</p>
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
