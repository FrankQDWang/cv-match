export const workbenchKeys = {
	me: ['auth', 'me'] as const,
	devModeStatus: ['workbench', 'dev-mode-status'] as const,
	sourceConnections: ['workbench', 'source-connections'] as const,
	sessions: ['workbench', 'sessions'] as const,
	session: (sessionId: string) => ['workbench', 'sessions', sessionId] as const,
	candidates: (sessionId: string) => ['workbench', 'sessions', sessionId, 'candidates'] as const,
	finalTop10: (sessionId: string) => ['workbench', 'sessions', sessionId, 'final-top10'] as const,
	liepinPolicy: (sessionId: string) =>
		['workbench', 'sessions', sessionId, 'liepin-policy'] as const,
	sessionEvents: (sessionId: string, afterSeq = 0) =>
		['workbench', 'sessions', sessionId, 'events', afterSeq] as const,
	graphCandidates: (sessionId: string, nodeId: string) =>
		['workbench', 'sessions', sessionId, 'graph-candidates', nodeId] as const,
	resumeSnapshot: (sessionId: string, graphCandidateId: string) =>
		['workbench', 'sessions', sessionId, 'resume-snapshot', graphCandidateId] as const
};
