import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    open: true,
    proxy: {
      '/voice': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
      '/customers': 'http://127.0.0.1:8000',
      '/transactions': 'http://127.0.0.1:8000',
      '/reports': 'http://127.0.0.1:8000',
      '/inventory': 'http://127.0.0.1:8000',
      '/stock': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
});
