import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: 'tests/e2e',
	testMatch: '**/*.spec.ts',
	use: {
		baseURL: 'http://127.0.0.1:5179',
		screenshot: 'only-on-failure',
		trace: 'retain-on-failure'
	},
	webServer: {
		command: 'bun run build && bun run preview:e2e',
		url: 'http://127.0.0.1:5179',
		reuseExistingServer: false,
		timeout: 120_000
	}
});
