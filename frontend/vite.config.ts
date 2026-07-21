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
        // Navy do BRAND.md (logo da coruja, 2026-07-21) - substituiu o antigo
        // verde-petróleo (#07423e) do rebrand petrol -> navy.
        theme_color: '#0F172A',
        background_color: '#020617',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
    // Docker Desktop no Windows não propaga de forma fiável eventos de
    // sistema de ficheiros (inotify) através do bind mount ./frontend:/srv —
    // sem polling, o Vite fica a servir ficheiros desatualizados até o
    // container ser reiniciado manualmente (bug real encontrado ao vivo).
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
});
