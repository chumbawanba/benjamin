import { useEffect, useMemo, useState } from 'react';
import { ApiError, api } from '../api/client';
import { BacktestChart as BacktestChartData, Evaluation, StrategyTemplate, WatchlistItem } from '../api/types';
import BacktestChart from '../components/BacktestChart';
import RecommendationBadge from '../components/RecommendationBadge';

// Estado do gráfico de backtest de uma linha, isolado num componente próprio
// para que o fetch aconteça só quando a linha é expandida (não para todas de
// uma vez) e seja automaticamente refeito se a estratégia selecionada mudar.
function BacktestSection({ templateId, stockId }: { templateId: string; stockId: string }) {
  const [state, setState] = useState<{ loading: boolean; data?: BacktestChartData; error?: string }>({ loading: true });

  useEffect(() => {
    let cancelled = false;
    setState({ loading: true });
    api
      .get<BacktestChartData>(
        `/evaluations/backtest-chart?template_id=${encodeURIComponent(templateId)}&stock_id=${encodeURIComponent(stockId)}`
      )
      .then((data) => {
        if (!cancelled) setState({ loading: false, data });
      })
      .catch((err) => {
        if (!cancelled) setState({ loading: false, error: err instanceof ApiError ? err.message : 'Erro ao carregar gráfico' });
      });
    return () => {
      cancelled = true;
    };
  }, [templateId, stockId]);

  return (
    <div className="mt-3 border-t border-gray-100 dark:border-slate-800 pt-3">
      <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
        Backtest — compras/vendas no último ano com os critérios atuais
      </p>
      {state.loading && <p className="text-xs text-gray-400 dark:text-slate-500">A carregar gráfico…</p>}
      {state.error && <p className="text-xs text-red-500 dark:text-rose-400">{state.error}</p>}
      {state.data && (
        <>
          <BacktestChart points={state.data.points} trades={state.data.trades} />
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-2">
            Retorno simulado:{' '}
            <span className={state.data.return_pct >= 0 ? 'text-green-600 dark:text-emerald-400' : 'text-red-500 dark:text-rose-400'}>
              {state.data.return_pct.toFixed(2)}%
            </span>
            {state.data.buy_and_hold_return_pct !== null && (
              <> · Comprar-e-manter: {state.data.buy_and_hold_return_pct.toFixed(2)}%</>
            )}
          </p>
          {state.data.trades.length === 0 && (
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
              Nenhuma compra/venda simulada — os critérios desta estratégia não chegaram a ser cumpridos no último
              ano para esta ação (não é um erro; a estratégia pode simplesmente ser demasiado restritiva, ou esta
              ação nunca ter estado nas condições certas no período).
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default function Feed({ embedded = false }: { embedded?: boolean }) {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [runningStock, setRunningStock] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [evalsLoading, setEvalsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Watchlist + estratégias só mudam por ação do próprio utilizador (nunca
  // por troca de estratégia selecionada) - separado do carregamento das
  // avaliações para não recarregar tudo sempre que o <select> muda.
  async function loadStatic() {
    setLoading(true);
    try {
      const [wl, tpls] = await Promise.all([
        api.get<WatchlistItem[]>('/watchlist'),
        api.get<StrategyTemplate[]>('/strategies'),
      ]);
      setWatchlist(wl);
      setTemplates(tpls);
      setSelectedTemplate((current) => current || tpls.find((t) => t.is_active)?.id || '');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar feed');
    } finally {
      setLoading(false);
    }
  }

  // Avaliação mais recente só da estratégia selecionada - sem template_id, o
  // endpoint devolvia a mais recente entre TODAS as estratégias por ação, sem
  // indicar qual, o que não correspondia ao que o <select> dizia estar
  // selecionado. Repete sempre que a seleção muda.
  async function loadEvaluations(templateId: string) {
    if (!templateId) {
      setEvaluations([]);
      return;
    }
    setEvalsLoading(true);
    try {
      const evals = await api.get<Evaluation[]>(`/evaluations/latest?template_id=${encodeURIComponent(templateId)}`);
      setEvaluations(evals);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar avaliações');
    } finally {
      setEvalsLoading(false);
    }
  }

  useEffect(() => {
    loadStatic();
  }, []);

  useEffect(() => {
    loadEvaluations(selectedTemplate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTemplate]);

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
      await loadEvaluations(selectedTemplate);
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
      await loadEvaluations(selectedTemplate);
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

      {loading || evalsLoading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : !selectedTemplate ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Escolhe uma estratégia acima para ver as avaliações.</p>
      ) : evaluations.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Ainda não há avaliações desta estratégia. Corre-a acima.</p>
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

              {expanded === ev.id && selectedTemplate && <BacktestSection templateId={selectedTemplate} stockId={ev.stock_id} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
