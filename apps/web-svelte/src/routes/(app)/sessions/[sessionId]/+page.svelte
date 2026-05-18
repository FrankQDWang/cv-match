<script lang="ts">
	import { resolve } from '$app/paths';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { safeErrorMessage } from '$lib/api/errors';
	import {
		approveRequirementTriage,
		getGraphCandidateResumeSnapshot,
		getSession,
		listFinalTopCandidates,
		listCandidateReviewItems,
		listGraphCandidates,
		listSessionEvents,
		prepareRequirementTriage,
		startSessionSourceRuns
	} from '$lib/api/workbench';
	import CandidateQueue from '$lib/components/CandidateQueue.svelte';
	import DetailRecommendationPanel from '$lib/components/DetailRecommendationPanel.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import LoadingState from '$lib/components/LoadingState.svelte';
	import NodeDetailPanel from '$lib/components/NodeDetailPanel.svelte';
	import RequirementTriagePanel from '$lib/components/RequirementTriagePanel.svelte';
	import SourceRunControlPanel from '$lib/components/SourceRunControlPanel.svelte';
	import SourceStatusStrip from '$lib/components/SourceStatusStrip.svelte';
	import StrategyGraph from '$lib/components/StrategyGraph.svelte';
	import { workbenchKeys } from '$lib/query/keys';
	import { buildRunStory } from '$lib/workbench/runStory';
	import type { RecruiterGraphNode } from '$lib/workbench/recruiterAnimation';
	import type { WorkbenchGraphCandidateSummary } from '$lib/workbench/types';

	let { data } = $props<{ data: { sessionId: string } }>();
	let selectedNode = $state<RecruiterGraphNode | null>(null);
	let selectedGraphCandidate = $state<WorkbenchGraphCandidateSummary | null>(null);
	const queryClient = useQueryClient();

	const sessionQuery = createQuery(() => ({
		queryKey: workbenchKeys.session(data.sessionId),
		queryFn: () => getSession(data.sessionId),
		refetchInterval: 3000
	}));

	const candidatesQuery = createQuery(() => ({
		queryKey: workbenchKeys.candidates(data.sessionId),
		queryFn: () => listCandidateReviewItems(data.sessionId),
		enabled: Boolean(sessionQuery.data)
	}));

	const finalTopQuery = createQuery(() => ({
		queryKey: workbenchKeys.finalTop10(data.sessionId),
		queryFn: () => listFinalTopCandidates(data.sessionId),
		enabled: Boolean(sessionQuery.data),
		refetchInterval: 3000
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

	const refreshSession = async () => {
		await Promise.all([
			queryClient.invalidateQueries({ queryKey: workbenchKeys.session(data.sessionId) }),
			queryClient.invalidateQueries({ queryKey: workbenchKeys.candidates(data.sessionId) }),
			queryClient.invalidateQueries({ queryKey: workbenchKeys.finalTop10(data.sessionId) }),
			queryClient.invalidateQueries({ queryKey: workbenchKeys.sessionEvents(data.sessionId, 0) })
		]);
	};

	const prepareMutation = createMutation(() => ({
		mutationFn: () => prepareRequirementTriage(data.sessionId),
		onSuccess: refreshSession
	}));
	const approveMutation = createMutation(() => ({
		mutationFn: () => approveRequirementTriage(data.sessionId),
		onSuccess: refreshSession
	}));
	const startMutation = createMutation(() => ({
		mutationFn: () => startSessionSourceRuns(data.sessionId),
		onSuccess: refreshSession
	}));
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
		<SourceStatusStrip session={sessionQuery.data} />
		<section class="session-control-grid">
			<RequirementTriagePanel session={sessionQuery.data} />
			<SourceRunControlPanel
				session={sessionQuery.data}
				preparing={prepareMutation.isPending}
				approving={approveMutation.isPending}
				starting={startMutation.isPending}
				error={prepareMutation.error
					? safeErrorMessage(prepareMutation.error, '标准生成失败')
					: approveMutation.error
						? safeErrorMessage(approveMutation.error, '标准确认失败')
						: startMutation.error
							? safeErrorMessage(startMutation.error, '检索启动失败')
							: null}
				onPrepare={() => prepareMutation.mutate()}
				onApprove={() => approveMutation.mutate()}
				onStart={() => startMutation.mutate()}
			/>
			<DetailRecommendationPanel session={sessionQuery.data} />
		</section>
		<CandidateQueue
			items={finalTopQuery.data?.items ?? []}
			loading={finalTopQuery.isPending}
			error={finalTopQuery.error
				? safeErrorMessage(finalTopQuery.error, '候选人队列加载失败')
				: null}
		/>
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
