import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { WorkbenchSession } from '$lib/workbench/types';
import RequirementTriagePanel from './RequirementTriagePanel.svelte';
import SourceRunControlPanel from './SourceRunControlPanel.svelte';

type RunControlSession = {
	requirementTriage: Pick<
		WorkbenchSession['requirementTriage'],
		| 'status'
		| 'mustHaves'
		| 'niceToHaves'
		| 'synonyms'
		| 'seniorityFilters'
		| 'exclusions'
		| 'generatedQueryHints'
	>;
	sourceRuns: Array<Pick<WorkbenchSession['sourceRuns'][number], 'status'>>;
};

const session = {
	requirementTriage: {
		status: 'draft',
		mustHaves: [],
		niceToHaves: [],
		synonyms: [],
		seniorityFilters: [],
		exclusions: [],
		generatedQueryHints: []
	},
	sourceRuns: [{ status: 'queued' }]
} satisfies RunControlSession;

describe('SourceRunControlPanel', () => {
	it('blocks source start until triage is approved', () => {
		render(SourceRunControlPanel, {
			props: {
				session,
				onPrepare: vi.fn(),
				onApprove: vi.fn(),
				onStart: vi.fn()
			}
		});

		expect(screen.getByRole('button', { name: '启动双源检索' })).toBeDisabled();
	});

	it('emits start when triage is approved', async () => {
		const user = userEvent.setup();
		const onStart = vi.fn();
		render(SourceRunControlPanel, {
			props: {
				session: {
					...session,
					requirementTriage: {
						...session.requirementTriage,
						status: 'approved',
						mustHaves: ['5 年以上 Python']
					}
				},
				onPrepare: vi.fn(),
				onApprove: vi.fn(),
				onStart
			}
		});

		await user.click(screen.getByRole('button', { name: '启动双源检索' }));

		expect(onStart).toHaveBeenCalledTimes(1);
	});

	it('renders generated triage criteria before approval', () => {
		render(RequirementTriagePanel, {
			props: {
				session: {
					...session,
					requirementTriage: {
						...session.requirementTriage,
						mustHaves: ['Svelte Workbench'],
						generatedQueryHints: ['recruiting agent']
					}
				}
			}
		});

		expect(screen.getByText('Svelte Workbench')).toBeInTheDocument();
		expect(screen.getByText('recruiting agent')).toBeInTheDocument();
	});
});
