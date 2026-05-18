import { QueryClient } from '@tanstack/svelte-query';

export function createQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: {
				retry: false,
				staleTime: 15_000
			},
			mutations: {
				retry: false
			}
		}
	});
}
