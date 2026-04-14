import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5176,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:8011',
    },
  },
  test: {
    environment: 'jsdom',
  },
});
