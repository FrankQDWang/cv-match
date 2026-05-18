import { describe, expect, it } from 'vitest';

import { workbenchKeys } from './keys';

describe('workbenchKeys', () => {
	it('returns stable keys for the Svelte spike server-state surface', () => {
		expect(workbenchKeys.me).toEqual(['auth', 'me']);
		expect(workbenchKeys.sessions).toEqual(['workbench', 'sessions']);
		expect(workbenchKeys.session('session-1')).toEqual(['workbench', 'sessions', 'session-1']);
		expect(workbenchKeys.candidates('session-1')).toEqual([
			'workbench',
			'sessions',
			'session-1',
			'candidates'
		]);
		expect(workbenchKeys.sessionEvents('session-1')).toEqual([
			'workbench',
			'sessions',
			'session-1',
			'events',
			0
		]);
		expect(workbenchKeys.graphCandidates('session-1', 'node-1')).toEqual([
			'workbench',
			'sessions',
			'session-1',
			'graph-candidates',
			'node-1'
		]);
		expect(workbenchKeys.resumeSnapshot('session-1', 'candidate-1')).toEqual([
			'workbench',
			'sessions',
			'session-1',
			'resume-snapshot',
			'candidate-1'
		]);
	});
});
