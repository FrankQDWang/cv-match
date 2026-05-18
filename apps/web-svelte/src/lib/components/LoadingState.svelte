<script lang="ts">
	let { label = '正在加载' } = $props<{ label?: string }>();
</script>

<section class="loading-state" aria-live="polite" data-testid="loading-state">
	<span class="loading-spinner" aria-hidden="true"></span>
	<p>{label}</p>
</section>

<style>
	.loading-state {
		display: grid;
		min-height: 160px;
		place-items: center;
		gap: 12px;
		border: 1px solid color-mix(in srgb, #1f2937 12%, transparent);
		background: #ffffff;
		color: #475569;
	}

	.loading-spinner {
		width: 28px;
		height: 28px;
		border: 3px solid #dbe4ee;
		border-top-color: #0f766e;
		border-radius: 999px;
		animation: spin 0.9s linear infinite;
	}

	p {
		margin: 0;
		font-size: 14px;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
