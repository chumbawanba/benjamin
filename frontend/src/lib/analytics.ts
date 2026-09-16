// GA4 - só fica ativo se VITE_GA_MEASUREMENT_ID estiver definido em build-time
// (ver frontend/Dockerfile.prod + docker-compose.prod.yml). Em dev local a
// variável não existe, por isso nunca envia nada - não precisa de opt-out.
declare global {
  interface Window {
    dataLayer: unknown[];
    gtag: (...args: unknown[]) => void;
  }
}

const GA_ID = import.meta.env.VITE_GA_MEASUREMENT_ID as string | undefined;

let initialized = false;

export function initAnalytics(): void {
  if (!GA_ID || initialized) return;
  initialized = true;

  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag(...args: unknown[]) {
    window.dataLayer.push(args);
  };
  window.gtag('js', new Date());
  // send_page_view desligado - numa SPA o carregamento inicial do gtag.js só
  // vê a 1ª rota; sem isto, navegações seguintes via React Router (sem reload
  // de página) nunca seriam contadas. trackPageview() é chamado manualmente
  // em cada mudança de rota, incluindo a primeira (ver AnalyticsTracker em
  // App.tsx), para não duplicar nem perder nenhuma.
  window.gtag('config', GA_ID, { send_page_view: false });
}

export function trackPageview(path: string): void {
  if (!GA_ID || !window.gtag) return;
  window.gtag('event', 'page_view', { page_path: path, page_title: document.title });
}
