import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';

import HarnessSmoke from './HarnessSmoke.svelte';

describe('Svelte component test harness', () => {
	it('renders components with jest-dom matchers', () => {
		render(HarnessSmoke);

		expect(screen.getByText('Harness ready')).toBeInTheDocument();
	});
});
