import { createApiClient, requireData } from './client';
import type { components } from './schema';

type BootstrapAdminInput = components['schemas']['WorkbenchBootstrapRequest'];
type LoginInput = components['schemas']['WorkbenchLoginRequest'];
type WorkbenchEvent = components['schemas']['WorkbenchEventResponse'];
type GraphCandidateQuery = {
	node_id: string;
	limit: number;
	cursor?: string | null;
};

const EVENT_PAGE_LIMIT = 200;
const EVENT_MAX_PAGES = 25;

export const api = createApiClient().client;

export async function bootstrapAdmin(input: BootstrapAdminInput) {
	return requireData(await api.POST('/api/auth/bootstrap', { body: input }));
}

export async function getMe() {
	return requireData(await api.GET('/api/auth/me'));
}

export async function login(input: LoginInput) {
	const result = await api.POST('/api/auth/login', { body: input });
	if (!result.response.ok) {
		requireData(result);
	}
}

export async function logout() {
	const result = await api.POST('/api/auth/logout');
	if (!result.response.ok) {
		requireData(result);
	}
}

export async function listSessions() {
	return requireData(await api.GET('/api/workbench/sessions'));
}

export async function getSession(sessionId: string) {
	return requireData(
		await api.GET('/api/workbench/sessions/{session_id}', {
			params: { path: { session_id: sessionId } }
		})
	);
}

export async function listCandidateReviewItems(sessionId: string) {
	return requireData(
		await api.GET('/api/workbench/sessions/{session_id}/candidates', {
			params: { path: { session_id: sessionId } }
		})
	);
}

export async function listGraphCandidates(
	sessionId: string,
	nodeId: string,
	cursor?: string,
	limit = 50
) {
	const query: GraphCandidateQuery = { node_id: nodeId, limit };
	if (cursor !== undefined) {
		query.cursor = cursor;
	}

	return requireData(
		await api.GET('/api/workbench/sessions/{session_id}/graph-candidates', {
			params: {
				path: { session_id: sessionId },
				query
			}
		})
	);
}

export async function getGraphCandidateResumeSnapshot(sessionId: string, graphCandidateId: string) {
	return requireData(
		await api.GET(
			'/api/workbench/sessions/{session_id}/graph-candidates/{graph_candidate_id}/resume-snapshot',
			{
				params: {
					path: {
						session_id: sessionId,
						graph_candidate_id: graphCandidateId
					}
				}
			}
		)
	);
}

export async function listSessionEvents(sessionId: string, afterSeq = 0) {
	const events: WorkbenchEvent[] = [];
	let cursor = afterSeq;

	for (let pageIndex = 0; pageIndex < EVENT_MAX_PAGES; pageIndex += 1) {
		const page = requireData(
			await api.GET('/api/workbench/sessions/{session_id}/events', {
				params: {
					path: { session_id: sessionId },
					query: { after_seq: cursor, limit: EVENT_PAGE_LIMIT }
				}
			})
		);
		events.push(...page.events);
		if (page.events.length < EVENT_PAGE_LIMIT) {
			break;
		}
		const lastEvent = page.events.at(-1);
		if (!lastEvent) {
			break;
		}
		cursor = lastEvent.globalSeq;
	}

	return { events };
}
