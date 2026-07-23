// Utilitários de formatação partilhados entre páginas (Watchlist, StockDetail).

// Texto relativo curto ("agora mesmo", "há 5 min", "há 3h", "há 2 dias") a
// partir de um ISO datetime (ex: stock.last_quote_at) — deixa claro ao
// utilizador se o preço mostrado é de agora ou de horas atrás.
export function formatRelativeTime(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const diffMs = Date.now() - then;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'agora mesmo';
  if (diffMin < 60) return `há ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `há ${diffH}h`;
  const diffDays = Math.floor(diffH / 24);
  return `há ${diffDays} dia${diffDays > 1 ? 's' : ''}`;
}
