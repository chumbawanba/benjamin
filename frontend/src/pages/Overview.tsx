import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { NewsItem, WatchlistItem } from '../api/types';
import ScoreBadge from '../components/ScoreBadge';

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

type Tab = 'sinais' | 'noticias';

export default function Overview() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [tab, setTab] = useState<Tab>('sinais');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reorderError, setReorderError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [wl, newsItems] = await Promise.all([
        api.get<WatchlistItem[]>('/watchlist'),
        api.get<NewsItem[]>('/watchlist/news'),
      ]);
      setWatchlist(wl);
      setNews(newsItems);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const summary = useMemo(() => {
    const counts = { BUY: 0, SELL: 0, HOLD: 0, none: 0 };
    watchlist.forEach((item) => {
      const rec = item.latest_evaluation?.recommendation;
      if (rec === 'BUY' || rec === 'SELL' || rec === 'HOLD') counts[rec] += 1;
      else counts.none += 1;
    });
    return counts;
  }, [watchlist]);

  async function persistOrder(items: WatchlistItem[]) {
    setReorderError(null);
    try {
      await api.put('/watchlist/reorder', { ordered_ids: items.map((i) => i.id) });
    } catch (err) {
      setReorderError(err instanceof ApiError ? err.message : 'Erro ao gravar ordem');
      await load(); // repõe a ordem guardada no servidor
    }
  }

  function moveItem(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= watchlist.length) return;
    const next = [...watchlist];
    [next[index], next[target]] = [next[target], next[index]];
    setWatchlist(next);
    void persistOrder(next);
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Overview</h1>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : (
        <>
          <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 flex gap-3 text-center">
            <div className="flex-1">
              <p className="text-2xl font-bold text-green-600 dark:text-emerald-400">{summary.BUY}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">Comprar</p>
            </div>
            <div className="flex-1 border-l border-gray-100 dark:border-slate-800">
              <p className="text-2xl font-bold text-red-600 dark:text-rose-400">{summary.SELL}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">Vender</p>
            </div>
            <div className="flex-1 border-l border-gray-100 dark:border-slate-800">
              <p className="text-2xl font-bold text-gray-400 dark:text-slate-400">{summary.HOLD}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">Manter</p>
            </div>
          </div>

          <div className="flex border-b border-gray-200 dark:border-slate-800 mb-4">
            <button
              onClick={() => setTab('sinais')}
              className={`flex-1 text-center py-2 text-sm font-medium border-b-2 -mb-px ${
                tab === 'sinais'
                  ? 'text-petrol-600 dark:text-petrol-400 border-petrol-600 dark:border-petrol-400'
                  : 'text-gray-400 dark:text-slate-500 border-transparent'
              }`}
            >
              Sinais
            </button>
            <button
              onClick={() => setTab('noticias')}
              className={`flex-1 text-center py-2 text-sm font-medium border-b-2 -mb-px ${
                tab === 'noticias'
                  ? 'text-petrol-600 dark:text-petrol-400 border-petrol-600 dark:border-petrol-400'
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
                  <Link to="/watchlist" className="text-petrol-600 dark:text-petrol-400">
                    Adiciona ações
                  </Link>
                  .
                </p>
              ) : (
                <ul className="space-y-2">
                  {watchlist.map((item, index) => (
                    <li
                      key={item.id}
                      className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="flex flex-col shrink-0 -my-1">
                          <button
                            onClick={() => moveItem(index, -1)}
                            disabled={index === 0}
                            aria-label="Mover para cima"
                            className="text-gray-300 dark:text-slate-600 disabled:opacity-30 hover:text-petrol-600 dark:hover:text-petrol-400 leading-none text-xs px-1"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => moveItem(index, 1)}
                            disabled={index === watchlist.length - 1}
                            aria-label="Mover para baixo"
                            className="text-gray-300 dark:text-slate-600 disabled:opacity-30 hover:text-petrol-600 dark:hover:text-petrol-400 leading-none text-xs px-1"
                          >
                            ▼
                          </button>
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-gray-900 dark:text-slate-100">{item.stock.ticker}</p>
                          <p className="text-xs text-gray-500 dark:text-slate-400">
                            {item.latest_evaluation?.price_at_evaluation ?? '—'}
                            {item.latest_evaluation && ` · avaliado ${formatDate(item.latest_evaluation.run_at)}`}
                          </p>
                        </div>
                      </div>
                      {item.latest_evaluation ? (
                        <div className="flex gap-2 shrink-0">
                          <ScoreBadge kind="buy" score={item.latest_evaluation.buy_score} />
                          <ScoreBadge kind="sell" score={item.latest_evaluation.sell_score} />
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400 dark:text-slate-500 shrink-0">sem avaliação</span>
                      )}
                    </li>
                  ))}
                </ul>
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
                        <p className="text-xs text-petrol-600 dark:text-petrol-400 font-medium">{item.ticker}</p>
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
