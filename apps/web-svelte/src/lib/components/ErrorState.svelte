<script lang="ts">
	let { message, title = '加载失败' } = $props<{ message: string; title?: string }>();
</script>

<section class="error-state" role="alert" data-testid="error-state">
	<strong>{title}</strong>
	<p>{message}</p>
</section>

<style>
	.error-state {
		display: grid;
		gap: 8px;
		min-height: 140px;
		align-content: center;
		padding: 24px;
		border: 1px solid #fecdd3;
		background: #fff1f2;
		color: #9f1239;
	}

	strong,
	p {
		margin: 0;
	}

	strong {
		font-size: 15px;
	}

	p {
		font-size: 14px;
		line-height: 1.6;
	}
</style>
