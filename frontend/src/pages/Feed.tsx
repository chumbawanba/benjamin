import { useEffect, useMemo, useState } from 'react';
import { ApiError, api } from '../api/client';
import { ChecklistTemplate, Evaluation, WatchlistItem } from '../api/types';
import ScoreBadge from '../components/ScoreBadge';

export default function Feed() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [evals, wl, tpls] = await Promise.all([
        api.get<Evaluation[]>('/evaluations/latest'),
        api.get<WatchlistItem[]>('/watchlist'),
        api.get<ChecklistTemplate[]>('/checklists'),
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

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 mb-4">Feed</h1>

      <div className="bg-white rounded-xl shadow-sm p-4 mb-4 flex gap-2 items-center">
        <select
          value={selectedTemplate}
          onChange={(e) => setSelectedTemplate(e.target.value)}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">Escolhe uma checklist</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <button
          onClick={handleRunNow}
          disabled={!selectedTemplate || running}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 shrink-0"
        >
          {running ? 'A avaliar…' : 'Avaliar agora'}
        </button>
      </div>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500">A carregar…</p>
      ) : evaluations.length === 0 ? (
        <p className="text-sm text-gray-500">Ainda não há avaliações. Corre uma checklist acima.</p>
      ) : (
        <ul className="space-y-2">
          {evaluations.map((ev) => (
            <li key={ev.id} className="bg-white rounded-xl shadow-sm p-4">
              <button
                onClick={() => setExpanded(expanded === ev.id ? null : ev.id)}
                className="w-full flex items-center justify-between text-left"
              >
                <div>
                  <p className="font-semibold text-gray-900">{tickerByStock.get(ev.stock_id) ?? ev.stock_id}</p>
                  <p className="text-xs text-gray-500">
                    {ev.recommendation} · {ev.price_at_evaluation !== null ? ev.price_at_evaluation : '—'}
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <ScoreBadge kind="buy" score={ev.buy_score} />
                  <ScoreBadge kind="sell" score={ev.sell_score} />
                </div>
              </button>

              {expanded === ev.id && (
                <ul className="mt-3 border-t border-gray-100 pt-3 space-y-1">
                  {ev.details.map((d) => {
                    const info = itemInfoById.get(d.checklist_item_id);
                    return (
                      <li key={d.checklist_item_id} className="flex items-center justify-between text-xs gap-2">
                        <span className="text-gray-600">{info?.name ?? d.checklist_item_id}</span>
                        <span className={d.passed === null ? 'text-gray-400' : d.passed ? 'text-green-600' : 'text-red-500'}>
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
