# Frontend AI Rules

This project uses SvelteKit + Svelte 5 + TypeScript.

Rules:

- Use Svelte 5 runes in new code: `$state`, `$derived`, `$effect`, `$props`.
- Use Svelte 5 event property syntax such as `onclick`, not old `on:click`, in new files.
- Do not write React patterns.
- Do not use TanStack Router. SvelteKit file-based routes own routing.
- Use `src/lib/api` for all API calls. No raw `fetch` in route components.
- Use `src/lib/query/keys.ts` for Svelte Query keys. Do not invent ad hoc query keys in pages.
- Use `@tanstack/svelte-query` for server state that needs caching, mutation, invalidation, polling, or optimistic updates.
- Treat Svelte Query results as reactive objects, such as `query.isPending` and `query.data`; do not use legacy store `$query` syntax unless the installed package documentation for this exact version requires it.
- Use local runes only for local UI state.
- Do not edit generated OpenAPI files manually.
- Do not display raw backend error detail in UI. Use `safeErrorMessage()` from `src/lib/api/errors.ts`.
- Every route page must handle loading, error, empty, and permission states.
- Before finishing, run `bun run check`, `bun run lint`, `bun run test`, `bun run build`, and `bun run test:e2e`.
