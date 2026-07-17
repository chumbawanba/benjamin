import { FormEvent, useEffect, useState } from 'react';
import { ApiError, api } from '../api/client';
import { TickerSearchResult, WatchlistItem } from '../api/types';
import ScoreBadge from '../components/ScoreBadge';

const POPULAR_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B'];

export default function Watchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addingTicker, setAddingTicker] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<TickerSearchResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.get<WatchlistItem[]>('/watchlist');
      setItems(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar watchlist');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const watchedTickers = new Set(items.map((i) => i.stock.ticker));

  async function handleAddTicker(ticker: string) {
    setAddingTicker(ticker);
    setError(null);
    try {
      await api.post('/watchlist', { ticker });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Erro ao adicionar ${ticker}`);
    } finally {
      setAddingTicker(null);
    }
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearchError(null);
    setSearched(true);
    try {
      const data = await api.get<TickerSearchResult[]>(`/watchlist/search?q=${encodeURIComponent(query.trim())}`);
      setResults(data);
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : 'Erro na pesquisa');
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm('Remover esta ação da watchlist?')) return;
    try {
      await api.delete(`/watchlist/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao remover');
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Watchlist</h1>

      <div className="mb-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Sugestões rápidas</p>
        <div className="flex flex-wrap gap-2">
          {POPULAR_TICKERS.map((ticker) => {
            const already = watchedTickers.has(ticker);
            return (
              <button
                key={ticker}
                onClick={() => handleAddTicker(ticker)}
                disabled={already || addingTicker === ticker}
                className="text-xs font-medium px-3 py-1.5 rounded-full border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {already ? `✓ ${ticker}` : addingTicker === ticker ? '…' : `+ ${ticker}`}
              </button>
            );
          })}
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 mb-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Procurar por nome ou ticker (ex: Apple, AAPL)"
          className="flex-1 bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={searching}
          className="bg-petrol-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 shrink-0"
        >
          {searching ? '…' : 'Procurar'}
        </button>
      </form>

      {searchError && <p className="text-sm text-red-600 dark:text-rose-400 mb-2">{searchError}</p>}

      {searched && !searching && (
        <ul className="space-y-1 mb-4">
          {results.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-slate-500 mb-2">Sem resultados.</p>
          ) : (
            results.map((r) => {
              const already = watchedTickers.has(r.ticker);
              return (
                <li
                  key={r.ticker}
                  className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-lg shadow-sm px-3 py-2 flex items-center justify-between text-sm gap-2"
                >
                  <div className="min-w-0">
                    <span className="font-semibold text-gray-900 dark:text-slate-100">{r.ticker}</span>
                    <span className="text-gray-500 dark:text-slate-400 ml-2">{r.name}</span>
                    {r.exchange && <span className="text-gray-400 dark:text-slate-500 ml-2 text-xs">{r.exchange}</span>}
                  </div>
                  <button
                    onClick={() => handleAddTicker(r.ticker)}
                    disabled={already || addingTicker === r.ticker}
                    className="text-petrol-600 dark:text-petrol-400 font-medium shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {already ? 'Já na lista' : 'Adicionar'}
                  </button>
                </li>
              );
            })
          )}
        </ul>
      )}

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Ainda não tens ações na watchlist.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 flex items-center justify-between"
            >
              <div>
                <div className="flex items-baseline gap-2">
                  <p className="font-semibold text-gray-900 dark:text-slate-100">{item.stock.ticker}</p>
                  {item.latest_evaluation?.price_at_evaluation !== undefined &&
                    item.latest_evaluation?.price_at_evaluation !== null && (
                      <span className="text-sm text-gray-700 dark:text-slate-300">
                        {item.latest_evaluation.price_at_evaluation} {item.stock.currency ?? ''}
                      </span>
                    )}
                </div>
                <p className="text-xs text-gray-500 dark:text-slate-400">{item.stock.name ?? '—'}</p>
                <div className="flex gap-2 mt-2">
                  {item.latest_evaluation ? (
                    <>
                      <ScoreBadge kind="buy" score={item.latest_evaluation.buy_score} />
                      <ScoreBadge kind="sell" score={item.latest_evaluation.sell_score} />
                    </>
                  ) : (
                    <span className="text-xs text-gray-400 dark:text-slate-500">
                      Sem avaliação ainda — vai a Feed e clica em "Avaliar agora"
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleRemove(item.id)}
                className="text-red-500 dark:text-rose-400 text-sm font-medium px-2 py-1 shrink-0"
              >
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
