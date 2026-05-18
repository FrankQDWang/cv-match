<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { safeErrorMessage } from '$lib/api/errors';
	import { login } from '$lib/api/workbench';

	let email = $state('admin@example.com');
	let password = $state('');
	let errorMessage = $state('');
	let isSubmitting = $state(false);

	async function submitLogin(event: SubmitEvent) {
		event.preventDefault();
		errorMessage = '';
		isSubmitting = true;
		try {
			await login({ email, password });
			await goto(resolve('/sessions'));
		} catch (error) {
			errorMessage = safeErrorMessage(error, '登录失败');
		} finally {
			isSubmitting = false;
		}
	}
</script>

<main class="center-shell">
	<form class="login-panel" aria-label="登录" onsubmit={submitLogin}>
		<p class="eyebrow">SeekTalent Workbench</p>
		<h1>登录</h1>
		<label>
			<span>邮箱</span>
			<input autocomplete="email" name="email" type="email" bind:value={email} required />
		</label>
		<label>
			<span>密码</span>
			<input
				autocomplete="current-password"
				name="password"
				type="password"
				bind:value={password}
				required
			/>
		</label>
		{#if errorMessage}
			<p class="form-error" role="alert">{errorMessage}</p>
		{/if}
		<button class="button" type="submit" disabled={isSubmitting}>
			{isSubmitting ? '登录中' : '登录'}
		</button>
	</form>
</main>
