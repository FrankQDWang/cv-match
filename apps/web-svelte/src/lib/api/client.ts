import createClient from 'openapi-fetch';

import { ApiError } from './errors';
import type { paths } from './schema';

const CSRF_HEADER = 'X-CSRF-Token';

type FetchRequest = (request: Request) => Promise<Response>;

export type CreateApiClientOptions = {
	baseUrl?: string;
	fetch?: FetchRequest;
};

function isMutating(method: string) {
	const upper = method.toUpperCase();
	return upper !== 'GET' && upper !== 'HEAD';
}

function errorMessage(error: unknown, status: number) {
	if (typeof error === 'string') {
		return error;
	}
	if (error && typeof error === 'object') {
		const payload = error as { detail?: unknown; error?: unknown; message?: unknown };
		if (typeof payload.detail === 'string') {
			return payload.detail;
		}
		if (typeof payload.error === 'string') {
			return payload.error;
		}
		if (typeof payload.message === 'string') {
			return payload.message;
		}
	}
	return `Request failed with status ${String(status)}`;
}

function defaultBaseUrl() {
	return typeof window === 'undefined' ? 'http://127.0.0.1' : window.location.origin;
}

export function createApiClient(options: CreateApiClientOptions = {}) {
	let csrfToken = '';
	const baseFetch = options.fetch ?? ((request: Request) => globalThis.fetch(request));

	async function fetchWithCsrf(sourceRequest: Request, csrfRetry: boolean): Promise<Response> {
		const retryRequest = sourceRequest.clone();
		const request = sourceRequest.clone();
		const headers = new Headers(request.headers);
		const hasCsrfToken = csrfToken.length > 0;
		const shouldSendCsrf = hasCsrfToken && isMutating(request.method) && !headers.has(CSRF_HEADER);

		if (shouldSendCsrf) {
			headers.set(CSRF_HEADER, csrfToken);
		}

		const response = await baseFetch(new Request(request, { credentials: 'include', headers }));
		const refreshedCsrf = response.headers.get(CSRF_HEADER);
		if (refreshedCsrf) {
			csrfToken = refreshedCsrf;
		}

		if (response.status === 403 && csrfRetry && hasCsrfToken && isMutating(request.method)) {
			await fetchWithCsrf(
				new Request(new URL('/api/auth/me', request.url), { method: 'GET' }),
				false
			);
			return fetchWithCsrf(retryRequest, false);
		}

		return response;
	}

	const client = createClient<paths>({
		baseUrl: options.baseUrl ?? defaultBaseUrl(),
		fetch: (request) => fetchWithCsrf(request, true)
	});

	return { client };
}

export function requireData<T>(result: { data?: T; error?: unknown; response: Response }): T {
	if (result.data !== undefined) {
		return result.data;
	}
	throw new ApiError(errorMessage(result.error, result.response.status), result.response.status);
}
