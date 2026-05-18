import { describe, expect, it } from 'vitest';

import {
	readinessStatusLabel,
	readinessTone,
	selectedSourceKinds,
	sourceReasonLabel,
	sourceStatusLabel
} from './sourceDisplay';

describe('source display helpers', () => {
	it('preserves explicit source order', () => {
		expect(selectedSourceKinds({ cts: true, liepin: true })).toEqual(['cts', 'liepin']);
		expect(selectedSourceKinds({ cts: false, liepin: true })).toEqual(['liepin']);
	});

	it('maps statuses to business-facing labels', () => {
		expect(sourceStatusLabel('running')).toBe('检索中');
		expect(sourceStatusLabel('blocked')).toBe('已阻塞');
		expect(readinessStatusLabel('missing')).toBe('缺少配置');
		expect(readinessTone('configured')).toBe('ready');
		expect(readinessTone('missing')).toBe('warning');
		expect(sourceReasonLabel('blocked_backend_unavailable')).toContain('暂不可用');
		expect(sourceReasonLabel('secret-token')).toBe('检索源需要处理。');
	});
});
