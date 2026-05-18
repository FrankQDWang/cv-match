import { describe, expect, it } from 'vitest';

import { ApiError, safeErrorMessage } from './errors';

describe('safeErrorMessage', () => {
	it('maps display-safe statuses without leaking backend detail', () => {
		const rawDetail = 'raw backend detail /tmp/provider-payload X-CSRF-Token';

		expect(safeErrorMessage(new ApiError(rawDetail, 401), 'Fallback message')).toBe('请先登录。');
		expect(safeErrorMessage(new ApiError(rawDetail, 403), 'Fallback message')).toBe(
			'没有权限执行此操作。'
		);
		expect(safeErrorMessage(new ApiError(rawDetail, 500), 'Fallback message')).toBe(
			'服务暂时不可用，请稍后重试。'
		);
		expect(safeErrorMessage(new ApiError(rawDetail, 422), 'Fallback message')).toBe(
			'Fallback message'
		);
		expect(safeErrorMessage(new Error(rawDetail), 'Fallback message')).toBe('Fallback message');
	});
});
