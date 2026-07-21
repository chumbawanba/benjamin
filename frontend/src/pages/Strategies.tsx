import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { Horizon, OptimizeResult, StrategyTemplate } from '../api/types';

const HORIZON_OPTIONS: { value: Horizon | ''; label: string }[] = [
  { value: '', label: 'Sem horizonte' },
  { value: 'short_term', label: 'Curto prazo' },
  { value: 'medium_term', label: 'Médio prazo' },
  { value: 'long_term', label: 'Longo prazo' },
];

function horizonLabel(h: Horizon | null): string | null {
  if (h === 'short_term') return 'Curto prazo';
  if (h === 'medium_term') return 'Médio prazo';
  if (h === 'long_term') return 'Longo prazo';
  return null;
}

export default function Strategies({ embedded = false }: { embedded?: boolean }) {
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [name, setName] = useState('');
  const [horizon, setHorizon] = useState<Horizon | ''>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [proposals, setProposals] = useState<Record<string, OptimizeResult>>({});
  const [optimizing, setOptimizing] = useState<Record<string, boolean>>({});
  const [applying, setApplying] = useState<Record<string, boolean>>({});

  async function load() {
    setLoading(true);
    try {
      const data = await api.get<StrategyTemplate[]>('/strategies');
      setTemplates(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar estratégias');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.post('/strategies', { name: name.trim(), horizon: horizon || null });
      setName('');
      setHorizon('');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao criar estratégia');
    }
  }

  async function toggleActive(t: StrategyTemplate) {
    try {
      await api.put(`/strategies/${t.id}`, {
        name: t.name,
        description: t.description,
        horizon: t.horizon,
        is_active: !t.is_active,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao atualizar estratégia');
    }
  }

  async function changeHorizon(t: StrategyTemplate, newHorizon: Horizon | '') {
    try {
      await api.put(`/strategies/${t.id}`, {
        name: t.name,
        description: t.description,
        horizon: newHorizon || null,
        is_active: t.is_active,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao atualizar horizonte');
    }
  }

  async function optimizeStrategy(t: StrategyTemplate) {
    setError(null);
    setOptimizing((prev) => ({ ...prev, [t.id]: true }));
    try {
      const result = await api.post<OptimizeResult>(`/strategies/${t.id}/optimize`);
      setProposals((prev) => ({ ...prev, [t.id]: result }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao otimizar estratégia');
    } finally {
      setOptimizing((prev) => ({ ...prev, [t.id]: false }));
    }
  }

  function discardProposal(templateId: string) {
    setProposals((prev) => {
      const next = { ...prev };
      delete next[templateId];
      return next;
    });
  }

  async function applyProposal(t: StrategyTemplate) {
    const proposal = proposals[t.id];
    if (!proposal) return;
    setApplying((prev) => ({ ...prev, [t.id]: true }));
    try {
      await Promise.all(t.items.map((item) => api.delete(`/strategies/items/${item.id}`)));
      for (const item of proposal.items) {
        await api.post(`/strategies/${t.id}/items`, item);
      }
      discardProposal(t.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao aplicar a proposta');
    } finally {
      setApplying((prev) => ({ ...prev, [t.id]: false }));
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Apagar esta estratégia e todos os seus critérios?')) return;
    try {
      await api.delete(`/strategies/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao apagar estratégia');
    }
  }

  return (
    <div>
      {!embedded && <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Estratégias</h1>}

      <form onSubmit={handleCreate} className="flex flex-wrap gap-2 mb-4">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Nome da nova estratégia"
          className="flex-1 min-w-[10rem] bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
        />
        <select
          value={horizon}
          onChange={(e) => setHorizon(e.target.value as Horizon | '')}
          className="bg-white dark:bg-slate-900 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
        >
          {HORIZON_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button type="submit" className="bg-navy-600 text-white rounded-lg px-4 py-2 text-sm font-semibold">
          Criar
        </button>
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : templates.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">Ainda não tens estratégias.</p>
      ) : (
        <ul className="space-y-2">
          {templates.map((t) => (
            <li key={t.id} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-semibold text-gray-900 dark:text-slate-100">{t.name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t.items.length} critério(s)</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {horizonLabel(t.horizon) && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-navy-50 text-navy-700 dark:bg-navy-500/15 dark:text-navy-400">
                      {horizonLabel(t.horizon)}
                    </span>
                  )}
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      t.is_active
                        ? 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400'
                        : 'bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-500'
                    }`}
                  >
                    {t.is_active ? 'Ativa' : 'Inativa'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3 mt-3 text-sm font-medium">
                <Link to={`/strategies/${t.id}`} className="text-navy-600 dark:text-navy-400">
                  Editar
                </Link>
                <button onClick={() => toggleActive(t)} className="text-gray-600 dark:text-slate-400">
                  {t.is_active ? 'Desativar' : 'Ativar'}
                </button>
                <button onClick={() => handleDelete(t.id)} className="text-red-500 dark:text-rose-400">
                  Apagar
                </button>
                <button
                  onClick={() => optimizeStrategy(t)}
                  disabled={optimizing[t.id]}
                  className="text-navy-600 dark:text-navy-400 disabled:opacity-50"
                >
                  {optimizing[t.id] ? 'A otimizar…' : 'Otimizar'}
                </button>
                <select
                  value={t.horizon ?? ''}
                  onChange={(e) => changeHorizon(t, e.target.value as Horizon | '')}
                  className="ml-auto text-xs bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-600 dark:text-slate-300 rounded-lg px-2 py-1"
                >
                  {HORIZON_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {proposals[t.id] && (
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-800">
                  <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
                    Backtest sobre os últimos ~12 meses da watchlist ({proposals[t.id].stocks_evaluated} ação(ões)).
                    Fundamentais assumidos constantes; sem custos de transação — ponto de partida, não garantia de
                    desempenho futuro.
                  </p>
                  <div className="flex gap-4 text-sm mb-2">
                    <span>
                      Estratégia proposta:{' '}
                      <strong
                        className={
                          proposals[t.id].backtest_return_pct >= 0
                            ? 'text-green-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-rose-400'
                        }
                      >
                        {proposals[t.id].backtest_return_pct.toFixed(2)}%
                      </strong>
                    </span>
                    <span className="text-gray-500 dark:text-slate-400">
                      Comprar-e-manter:{' '}
                      {proposals[t.id].buy_and_hold_return_pct !== null
                        ? `${proposals[t.id].buy_and_hold_return_pct!.toFixed(2)}%`
                        : '—'}
                    </span>
                  </div>
                  {proposals[t.id].items.length === 0 ? (
                    <p className="text-sm text-gray-400 dark:text-slate-500">
                      Não encontrei nenhum critério que batesse o "não fazer nada" com este histórico.
                    </p>
                  ) : (
                    <ul className="text-sm space-y-1 mb-3">
                      {proposals[t.id].items.map((item, idx) => (
                        <li key={idx} className="text-gray-700 dark:text-slate-300">
                          <span
                            className={
                              item.direction === 'buy_signal'
                                ? 'text-green-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-rose-400'
                            }
                          >
                            {item.direction === 'buy_signal' ? 'Compra' : 'Venda'}
                          </span>{' '}
                          se {item.metric} {item.operator} {item.threshold_value}
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="flex gap-3 text-sm font-medium">
                    <button
                      onClick={() => applyProposal(t)}
                      disabled={applying[t.id] || proposals[t.id].items.length === 0}
                      className="text-navy-600 dark:text-navy-400 disabled:opacity-50"
                    >
                      {applying[t.id] ? 'A aplicar…' : 'Aplicar (substitui critérios atuais)'}
                    </button>
                    <button onClick={() => discardProposal(t.id)} className="text-gray-500 dark:text-slate-400">
                      Descartar
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
