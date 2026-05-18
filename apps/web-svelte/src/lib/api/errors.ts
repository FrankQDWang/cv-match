export class ApiError extends Error {
	readonly status: number;

	constructor(message: string, status: number) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
	}
}

export function safeErrorMessage(error: unknown, fallback: string) {
	if (!(error instanceof ApiError)) {
		return fallback;
	}
	if (error.status === 401) {
		return '请先登录。';
	}
	if (error.status === 403) {
		return '没有权限执行此操作。';
	}
	if (error.status >= 500) {
		return '服务暂时不可用，请稍后重试。';
	}
	return fallback;
}
