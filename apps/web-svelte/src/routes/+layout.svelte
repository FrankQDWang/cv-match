<script lang="ts">
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { createQueryClient } from '$lib/query/client';

	let { children } = $props();
	const queryClient = createQueryClient();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<QueryClientProvider client={queryClient}>
	{@render children()}
</QueryClientProvider>
