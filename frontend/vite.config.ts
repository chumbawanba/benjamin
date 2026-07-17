import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// PWA: só instalabilidade (manifest + service worker mínimo), sem offline logic no MVP (SPEC.md secção 9).
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Benjamin',
        short_name: 'Benjamin',
        description: 'Watchlist + estratégias + agente de avaliação de investimentos',
        theme_color: '#07423e',
        background_color: '#020617',
        display: 'standalone',
        start_url: '/',
        icons: [{ src: 'icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
  },
});
