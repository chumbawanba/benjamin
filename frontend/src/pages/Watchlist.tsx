import { FormEvent, useEffect, useState } from 'react';
import { ApiError, api } from '../api/client';
import { WatchlistItem } from '../api/types';
import ScoreBadge from '../components/ScoreBadge';

export default function Watchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!ticker.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await api.post('/watchlist', { ticker: ticker.trim() });
      setTicker('');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao adicionar ticker');
    } finally {
      setAdding(false);
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
      <h1 className="text-xl font-bold text-gray-900 mb-4">Watchlist</h1>

      <form onSubmit={handleAdd} className="flex gap-2 mb-4">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="Ticker (ex: AAPL)"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm uppercase"
        />
        <button
          type="submit"
          disabled={adding}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50"
        >
          Adicionar
        </button>
      </form>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">A carregar…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500">Ainda não tens ações na watchlist.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className="bg-white rounded-xl shadow-sm p-4 flex items-center justify-between">
              <div>
                <p className="font-semibold text-gray-900">{item.stock.ticker}</p>
                <p className="text-xs text-gray-500">{item.stock.name}</p>
                <div className="flex gap-2 mt-2">
                  {item.latest_evaluation ? (
                    <>
                      <ScoreBadge kind="buy" score={item.latest_evaluation.buy_score} />
                      <ScoreBadge kind="sell" score={item.latest_evaluation.sell_score} />
                    </>
                  ) : (
                    <span className="text-xs text-gray-400">Sem avaliação ainda</span>
                  )}
                </div>
              </div>
              <button onClick={() => handleRemove(item.id)} className="text-red-500 text-sm font-medium px-2 py-1">
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
