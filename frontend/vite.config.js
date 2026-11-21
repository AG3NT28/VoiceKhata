import { defineConfig } from 'vite';

const backend = 'http://127.0.0.1:8000';

export default defineConfig({
  server: {
    port: 5173,
    host: '127.0.0.1',
    open: true,
    proxy: {
      '/voice': { target: backend, changeOrigin: true },
      '/ws': { target: backend, ws: true, changeOrigin: true },
      '/customers': { target: backend, changeOrigin: true },
      '/transactions': { target: backend, changeOrigin: true },
      '/reports': { target: backend, changeOrigin: true },
      '/inventory': { target: backend, changeOrigin: true },
      '/stock': { target: backend, changeOrigin: true },
      '/auth': { target: backend, changeOrigin: true },
      '/health': { target: backend, changeOrigin: true },
      '/api': { target: backend, changeOrigin: true },
    },
  },
});
