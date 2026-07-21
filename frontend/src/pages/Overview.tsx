import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { Horizon, NewsItem, StrategySignal, StrategySignalGroup, WatchlistItem } from '../api/types';
import AnalystSummaryCard from '../components/AnalystSummaryCard';
import PortfolioSummaryCard from '../components/PortfolioSummaryCard';
import PriceChange from '../components/PriceChange';
import RecommendationBadge from '../components/RecommendationBadge';

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'hoje';
  if (diffDays === 1) return 'ontem';
  if (diffDays < 7) return `há ${diffDays} dias`;
  return d.toLocaleDateString('pt-PT');
}

function horizonLabel(h: Horizon | null): string | null {
  if (h === 'short_term') return 'Curto prazo';
  if (h === 'medium_term') return 'Médio prazo';
  if (h === 'long_term') return 'Longo prazo';
  return null;
}

type Tab = 'sinais' | 'noticias';

export default function Overview() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [groups, setGroups] = useState<StrategySignalGroup[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [tab, setTab] = useState<Tab>('sinais');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reorderError, setReorderError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [wl, newsItems, signalGroups] = await Promise.all([
        api.get<WatchlistItem[]>('/watchlist'),
        api.get<NewsItem[]>('/watchlist/news'),
        api.get<StrategySignalGroup[]>('/evaluations/latest-by-strategy'),
      ]);
      setWatchlist(wl);
      setNews(newsItems);
      setGroups(signalGroups);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const watchlistByStockId = useMemo(() => {
    const map = new Map<string, WatchlistItem>();
    watchlist.forEach((w) => map.set(w.stock.id, w));
    return map;
  }, [watchlist]);

  async function persistOrder(items: WatchlistItem[]) {
    setReorderError(null);
    try {
      await api.put('/watchlist/reorder', { ordered_ids: items.map((i) => i.id) });
      const signalGroups = await api.get<StrategySignalGroup[]>('/evaluations/latest-by-strategy');
      setGroups(signalGroups);
    } catch (err) {
      setReorderError(err instanceof ApiError ? err.message : 'Erro ao gravar ordem');
      await load(); // repõe a ordem guardada no servidor
    }
  }

  function swapWatchlistOrder(stockIdA: string, stockIdB: string) {
    const itemA = watchlistByStockId.get(stockIdA);
    const itemB = watchlistByStockId.get(stockIdB);
    if (!itemA || !itemB) return;
    const next = [...watchlist];
    const idxA = next.findIndex((w) => w.id === itemA.id);
    const idxB = next.findIndex((w) => w.id === itemB.id);
    if (idxA === -1 || idxB === -1) return;
    [next[idxA], next[idxB]] = [next[idxB], next[idxA]];
    setWatchlist(next);
    void persistOrder(next);
  }

  function moveSignal(signals: StrategySignal[], index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= signals.length) return;
    swapWatchlistOrder(signals[index].stock.id, signals[target].stock.id);
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <img src="/icon-192.png" alt="" className="w-9 h-9 rounded-full shrink-0" />
        <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">Benjamin</h1>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : (
        <>
          <AnalystSummaryCard />
          <PortfolioSummaryCard />

          <div className="flex border-b border-gray-200 dark:border-slate-800 mb-4">
            <button
              onClick={() => setTab('sinais')}
              className={`flex-1 text-center py-2 text-sm font-medium border-b-2 -mb-px ${
                tab === 'sinais'
                  ? 'text-navy-600 dark:text-navy-400 border-navy-600 dark:border-navy-400'
                  : 'text-gray-400 dark:text-slate-500 border-transparent'
              }`}
            >
              Sinais
            </button>
            <button
              onClick={() => setTab('noticias')}
              className={`flex-1 text-center py-2 text-sm font-medium border-b-2 -mb-px ${
                tab === 'noticias'
                  ? 'text-navy-600 dark:text-navy-400 border-navy-600 dark:border-navy-400'
                  : 'text-gray-400 dark:text-slate-500 border-transparent'
              }`}
            >
              Notícias{news.length > 0 ? ` (${news.length})` : ''}
            </button>
          </div>

          {tab === 'sinais' && (
            <>
              {reorderError && <p className="text-sm text-red-600 dark:text-rose-400 mb-2">{reorderError}</p>}
              {watchlist.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  A watchlist está vazia.{' '}
                  <Link to="/workspace" className="text-navy-600 dark:text-navy-400">
                    Adiciona ações
                  </Link>
                  .
                </p>
              ) : groups.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  Ainda não tens estratégias ativas.{' '}
                  <Link to="/workspace?tab=estrategias" className="text-navy-600 dark:text-navy-400">
                    Cria uma estratégia
                  </Link>
                  .
                </p>
              ) : (
                <div className="space-y-5">
                  {groups.map((group) => (
                    <section key={group.strategy_id}>
                      <div className="flex items-center gap-2 mb-2">
                        <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
                          {group.strategy_name}
                        </h2>
                        {horizonLabel(group.horizon) && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-500/15 dark:text-navy-400">
                            {horizonLabel(group.horizon)}
                          </span>
                        )}
                        <span className="text-xs text-gray-400 dark:text-slate-500">
                          {group.signals.length} sinal{group.signals.length === 1 ? '' : 'is'}
                        </span>
                      </div>

                      {group.signals.length === 0 ? (
                        <p className="text-sm text-gray-400 dark:text-slate-500 pl-1">
                          Sem sinais de compra ou venda no momento.
                        </p>
                      ) : (
                        <ul className="space-y-2">
                          {group.signals.map((signal, index) => {
                            const wlItem = watchlistByStockId.get(signal.stock.id);
                            return (
                              <li
                                key={`${group.strategy_id}-${signal.stock.id}`}
                                className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 flex items-center justify-between gap-2"
                              >
                                <div className="flex items-center gap-2 min-w-0">
                                  <div className="flex flex-col shrink-0 -my-1">
                                    <button
                                      onClick={() => moveSignal(group.signals, index, -1)}
                                      disabled={index === 0}
                                      aria-label="Mover para cima"
                                      className="text-gray-300 dark:text-slate-600 disabled:opacity-30 hover:text-navy-600 dark:hover:text-navy-400 leading-none text-xs px-1"
                                    >
                                      ▲
                                    </button>
                                    <button
                                      onClick={() => moveSignal(group.signals, index, 1)}
                                      disabled={index === group.signals.length - 1}
                                      aria-label="Mover para baixo"
                                      className="text-gray-300 dark:text-slate-600 disabled:opacity-30 hover:text-navy-600 dark:hover:text-navy-400 leading-none text-xs px-1"
                                    >
                                      ▼
                                    </button>
                                  </div>
                                  <div className="min-w-0">
                                    <Link
                                      to={wlItem ? `/stocks/${wlItem.id}` : '#'}
                                      className="font-semibold text-gray-900 dark:text-slate-100 hover:text-navy-600 dark:hover:text-navy-400"
                                    >
                                      {signal.stock.ticker}
                                    </Link>
                                    <p className="text-xs text-gray-500 dark:text-slate-400 flex items-center gap-1.5 flex-wrap">
                                      <PriceChange
                                        price={signal.last_price}
                                        changePct={signal.price_change_pct}
                                        currency={signal.stock.currency}
                                      />
                                      <span>· avaliado {formatDate(signal.run_at)}</span>
                                    </p>
                                  </div>
                                </div>
                                <div className="shrink-0">
                                  <RecommendationBadge recommendation={signal.recommendation} />
                                </div>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </section>
                  ))}
                </div>
              )}
            </>
          )}

          {tab === 'noticias' && (
            <>
              {news.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-slate-400">Sem notícias recentes.</p>
              ) : (
                <ul className="space-y-2">
                  {news.map((item, idx) => (
                    <li key={idx} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4">
                      <a href={item.url ?? undefined} target="_blank" rel="noreferrer" className="block">
                        <p className="text-xs text-navy-600 dark:text-navy-400 font-medium">{item.ticker}</p>
                        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{item.headline}</p>
                        <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                          {item.source}
                          {item.published_at && ` · ${formatDate(item.published_at)}`}
                        </p>
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
