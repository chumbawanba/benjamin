import { useEffect, useMemo, useState } from 'react';
import { ApiError, api } from '../api/client';
import { Evaluation, StrategyTemplate, WatchlistItem } from '../api/types';
import RecommendationBadge from '../components/RecommendationBadge';

export default function Feed({ embedded = false }: { embedded?: boolean }) {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runningStock, setRunningStock] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [evals, wl, tpls] = await Promise.all([
        api.get<Evaluation[]>('/evaluations/latest'),
        api.get<WatchlistItem[]>('/watchlist'),
        api.get<StrategyTemplate[]>('/strategies'),
      ]);
      setEvaluations(evals);
      setWatchlist(wl);
      setTemplates(tpls);
      setSelectedTemplate((current) => current || tpls.find((t) => t.is_active)?.id || '');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar feed');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tickerByStock = useMemo(() => {
    const map = new Map<string, string>();
    watchlist.forEach((w) => map.set(w.stock.id, w.stock.ticker));
    return map;
  }, [watchlist]);

  const itemInfoById = useMemo(() => {
    const map = new Map<string, { name: string }>();
    templates.forEach((t) => t.items.forEach((i) => map.set(i.id, { name: i.name })));
    return map;
  }, [templates]);

  async function handleRunNow() {
    if (!selectedTemplate) return;
    setRunning(true);
    setError(null);
    try {
      await api.post('/evaluations/run', { template_id: selectedTemplate });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao avaliar');
    } finally {
      setRunning(false);
    }
  }

  async function handleRunSingle(stockId: string) {
    if (!selectedTemplate) return;
    setRunningStock(stockId);
    setError(null);
    try {
      await api.post('/evaluations/run', { template_id: selectedTemplate, stock_id: stockId });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao avaliar');
    } finally {
      setRunningStock(null);
    }
  }

  return (
    <div>
      {!embedded && <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Avaliações</h1>}

      <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 flex gap-2 items-center">
        <select
          value={selectedTemplate}
          onChange={(e) => setSelectedTemplate(e.target.value)}
          className="flex-1 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Escolhe uma estratégia</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <button
          onClick={handleRunNow}
          disabled={!selectedTemplate || running}
          className="bg-navy-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 shrink-0"
        >
          {running ? 'A avaliar…' : 'Avaliar agora'}
        </button>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : evaluations.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Ainda não há avaliações. Corre uma estratégia acima.</p>
      ) : (
        <ul className="space-y-2">
          {evaluations.map((ev) => (
            <li key={ev.id} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4">
              <div className="w-full flex items-center justify-between gap-2">
                <button
                  onClick={() => setExpanded(expanded === ev.id ? null : ev.id)}
                  className="flex-1 text-left"
                >
                  <p className="font-semibold text-gray-900 dark:text-slate-100">{tickerByStock.get(ev.stock_id) ?? ev.stock_id}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {ev.price_at_evaluation !== null ? ev.price_at_evaluation : '—'}
                  </p>
                </button>
                <div className="shrink-0">
                  <RecommendationBadge recommendation={ev.recommendation} buyScore={ev.buy_score} sellScore={ev.sell_score} />
                </div>
              </div>

              <div className="mt-2 flex justify-end">
                <button
                  onClick={() => handleRunSingle(ev.stock_id)}
                  disabled={!selectedTemplate || runningStock === ev.stock_id}
                  className="text-xs text-navy-600 dark:text-navy-400 font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {runningStock === ev.stock_id ? 'A avaliar…' : '↻ Avaliar só este'}
                </button>
              </div>

              {expanded === ev.id && (
                <ul className="mt-3 border-t border-gray-100 dark:border-slate-800 pt-3 space-y-1">
                  {ev.details.map((d) => {
                    const info = itemInfoById.get(d.strategy_item_id);
                    return (
                      <li key={d.strategy_item_id} className="flex items-center justify-between text-xs gap-2">
                        <span className="text-gray-600 dark:text-slate-400">{info?.name ?? d.strategy_item_id}</span>
                        <span
                          className={
                            d.passed === null
                              ? 'text-gray-400 dark:text-slate-500'
                              : d.passed
                                ? 'text-green-600 dark:text-emerald-400'
                                : 'text-red-500 dark:text-rose-400'
                          }
                        >
                          {d.passed === null ? 'N/A' : d.passed ? 'Passou' : 'Falhou'}
                          {d.observed_value !== null ? ` (${d.observed_value})` : ''}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
