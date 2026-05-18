<script lang="ts">
	import { resolve } from '$app/paths';
	import { createQuery } from '@tanstack/svelte-query';
	import { safeErrorMessage } from '$lib/api/errors';
	import {
		getGraphCandidateResumeSnapshot,
		getSession,
		listCandidateReviewItems,
		listGraphCandidates,
		listSessionEvents
	} from '$lib/api/workbench';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import LoadingState from '$lib/components/LoadingState.svelte';
	import NodeDetailPanel from '$lib/components/NodeDetailPanel.svelte';
	import StrategyGraph from '$lib/components/StrategyGraph.svelte';
	import { workbenchKeys } from '$lib/query/keys';
	import { buildRunStory } from '$lib/workbench/runStory';
	import type { RecruiterGraphNode } from '$lib/workbench/recruiterAnimation';
	import type { WorkbenchGraphCandidateSummary } from '$lib/workbench/types';

	let { data } = $props<{ data: { sessionId: string } }>();
	let selectedNode = $state<RecruiterGraphNode | null>(null);
	let selectedGraphCandidate = $state<WorkbenchGraphCandidateSummary | null>(null);

	const sessionQuery = createQuery(() => ({
		queryKey: workbenchKeys.session(data.sessionId),
		queryFn: () => getSession(data.sessionId)
	}));

	const candidatesQuery = createQuery(() => ({
		queryKey: workbenchKeys.candidates(data.sessionId),
		queryFn: () => listCandidateReviewItems(data.sessionId),
		enabled: Boolean(sessionQuery.data)
	}));

	const eventsQuery = createQuery(() => ({
		queryKey: workbenchKeys.sessionEvents(data.sessionId, 0),
		queryFn: () => listSessionEvents(data.sessionId, 0),
		enabled: Boolean(sessionQuery.data),
		refetchInterval: 3000
	}));

	const graphCandidatesQuery = createQuery(() => ({
		queryKey: workbenchKeys.graphCandidates(data.sessionId, selectedNode?.id ?? ''),
		queryFn: () => listGraphCandidates(data.sessionId, selectedNode?.id ?? ''),
		enabled: Boolean(sessionQuery.data && selectedNode)
	}));

	const resumeSnapshotQuery = createQuery(() => ({
		queryKey: workbenchKeys.resumeSnapshot(
			data.sessionId,
			selectedGraphCandidate?.graphCandidateId ?? ''
		),
		queryFn: () =>
			getGraphCandidateResumeSnapshot(
				data.sessionId,
				selectedGraphCandidate?.graphCandidateId ?? ''
			),
		enabled: Boolean(
			selectedGraphCandidate?.canExpandResume && selectedGraphCandidate.graphCandidateId
		)
	}));

	const story = $derived(
		sessionQuery.data
			? buildRunStory({
					session: sessionQuery.data,
					candidateReviewItems: candidatesQuery.data?.items ?? [],
					events: eventsQuery.data?.events ?? []
				})
			: null
	);
</script>

<main class="session-detail-page">
	{#if sessionQuery.isPending}
		<LoadingState label="正在加载会话" />
	{:else if sessionQuery.error}
		<ErrorState message={safeErrorMessage(sessionQuery.error, '会话加载失败')} />
	{:else if story && sessionQuery.data}
		<section class="job-brief">
			<a class="back-link" href={resolve('/sessions')}>返回会话</a>
			<p class="eyebrow">职位需求</p>
			<h1>{sessionQuery.data.jobTitle || '未命名职位'}</h1>
			<p>{sessionQuery.data.notes || sessionQuery.data.jdText}</p>
		</section>
		<section class="workbench-grid">
			<div class="graph-panel" aria-label="策略图">
				<StrategyGraph
					{story}
					selectedNodeId={selectedNode?.id ?? null}
					onSelectNode={(node) => {
						selectedNode = node;
						selectedGraphCandidate = null;
					}}
				/>
			</div>
			<NodeDetailPanel
				node={selectedNode}
				graphCandidates={graphCandidatesQuery.data?.items ?? []}
				graphCandidatesLoading={graphCandidatesQuery.isPending && Boolean(selectedNode)}
				graphCandidatesError={graphCandidatesQuery.error
					? safeErrorMessage(graphCandidatesQuery.error, '候选人加载失败')
					: null}
				selectedGraphCandidateId={selectedGraphCandidate?.graphCandidateId ?? null}
				resumeSnapshot={resumeSnapshotQuery.data ?? null}
				resumeSnapshotLoading={resumeSnapshotQuery.isPending && Boolean(selectedGraphCandidate)}
				resumeSnapshotError={resumeSnapshotQuery.error
					? safeErrorMessage(resumeSnapshotQuery.error, '简历摘要加载失败')
					: null}
				onSelectGraphCandidate={(candidate) => {
					selectedGraphCandidate = candidate;
				}}
			/>
		</section>
	{:else}
		<ErrorState message="会话暂无可展示内容" />
	{/if}
</main>
