import { describe, expect, it, vi } from 'vitest';

import { createApiClient } from './client';

const CSRF_HEADER = 'X-CSRF-Token';

function jsonResponse(body: unknown, init: ResponseInit = {}) {
	const headers = new Headers(init.headers);
	headers.set('Content-Type', 'application/json');
	return new Response(JSON.stringify(body), { ...init, headers });
}

function requestAt(requests: Request[], index: number) {
	const request = requests[index];
	if (!request) {
		throw new Error(`Expected request at index ${String(index)}`);
	}
	return request;
}

describe('createApiClient', () => {
	it('sends credentials and carries captured CSRF only on mutating requests', async () => {
		const requests: Request[] = [];
		const fetchMock = vi.fn(async (request: Request) => {
			requests.push(request.clone());
			if (requests.length === 1) {
				return jsonResponse({ user: { userId: 'u1' } }, { headers: { [CSRF_HEADER]: 'token-1' } });
			}
			return new Response(null, { status: 204 });
		});
		const { client } = createApiClient({ baseUrl: 'http://seektalent.test', fetch: fetchMock });

		await client.GET('/api/auth/me');
		await client.POST('/api/auth/logout');

		expect(fetchMock).toHaveBeenCalledTimes(2);
		expect(requestAt(requests, 0).credentials).toBe('include');
		expect(requestAt(requests, 0).headers.get(CSRF_HEADER)).toBeNull();
		expect(requestAt(requests, 1).credentials).toBe('include');
		expect(requestAt(requests, 1).headers.get(CSRF_HEADER)).toBe('token-1');
		expect(requestAt(requests, 1).headers.has('Content-Type')).toBe(false);
	});

	it('refreshes CSRF through /api/auth/me once before retrying a mutating 403', async () => {
		const paths: string[] = [];
		const csrfValues: (string | null)[] = [];
		const fetchMock = vi.fn(async (request: Request) => {
			paths.push(new URL(request.url).pathname);
			csrfValues.push(request.headers.get(CSRF_HEADER));

			if (paths.length === 1) {
				return jsonResponse(
					{ user: { userId: 'u1' } },
					{ headers: { [CSRF_HEADER]: 'old-token' } }
				);
			}
			if (paths.length === 2) {
				return jsonResponse({ detail: 'csrf failed with raw backend detail' }, { status: 403 });
			}
			if (paths.length === 3) {
				return jsonResponse(
					{ user: { userId: 'u1' } },
					{ headers: { [CSRF_HEADER]: 'new-token' } }
				);
			}
			return new Response(null, { status: 204 });
		});
		const { client } = createApiClient({ baseUrl: 'http://seektalent.test', fetch: fetchMock });

		await client.GET('/api/auth/me');
		const result = await client.POST('/api/auth/logout');

		expect(result.response.status).toBe(204);
		expect(paths).toEqual(['/api/auth/me', '/api/auth/logout', '/api/auth/me', '/api/auth/logout']);
		expect(csrfValues).toEqual([null, 'old-token', null, 'new-token']);
	});
});
