export type SourceKind = 'cts' | 'liepin';

export function sourceLabel(source: SourceKind) {
	return source === 'cts' ? 'CTS' : 'Liepin';
}

export function readinessTone(status: string) {
	if (status === 'ready' || status === 'configured') return 'ready';
	if (status === 'disabled' || status === 'missing' || status === 'needs_setup') return 'warning';
	return 'blocked';
}

export function readinessStatusLabel(status: string) {
	const labels: Record<string, string> = {
		ready: '可用',
		configured: '已配置',
		missing: '缺少配置',
		disabled: '未启用',
		invalid: '配置无效',
		needs_setup: '需要设置',
		safe: '安全',
		warning: '需注意',
		error: '不可用',
		unknown: '待确认'
	};
	return labels[status] ?? '待确认';
}

export function sourceStatusLabel(status: string) {
	const labels: Record<string, string> = {
		pending: '等待启动',
		queued: '排队中',
		running: '检索中',
		completed: '已完成',
		partial: '部分完成',
		blocked: '已阻塞',
		failed: '失败',
		cancelled: '已取消',
		draft: '草稿'
	};
	return labels[status] ?? status;
}

export function sourceReasonLabel(reasonCode: string | null | undefined) {
	const labels: Record<string, string> = {
		blocked_backend_unavailable: 'Liepin 浏览器执行暂不可用。',
		failed_provider_error: '检索源返回错误。',
		login_required: '需要先完成 Liepin 登录。',
		partial_timeout: '部分结果已返回，检索超时停止。',
		cancelled_by_user: '检索已取消。',
		liepin_connection_not_connected: 'Liepin 连接未就绪。'
	};
	if (!reasonCode) return null;
	return labels[reasonCode] ?? '检索源需要处理。';
}

export function selectedSourceKinds(input: { cts: boolean; liepin: boolean }): SourceKind[] {
	const result: SourceKind[] = [];
	if (input.cts) result.push('cts');
	if (input.liepin) result.push('liepin');
	return result;
}
