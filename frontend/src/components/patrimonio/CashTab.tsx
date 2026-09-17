import { FormEvent, useState } from 'react';
import { ApiError, api } from '../../api/client';
import { Position } from '../../api/types';

function toNum(v: number | string | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

function money(v: number | null, currency?: string | null): string {
  if (v === null) return '—';
  return `${v.toFixed(2)} ${currency ?? ''}`.trim();
}

interface Props {
  positions: Position[];
  currency: string;
  currencyOptions: string[];
  onReload: () => Promise<void>;
}

// Separador "Cash" da página Património - posições de asset_type='cash'
// (uma por moeda, ver backend market_data.get_or_create_cash_stock).
// Extraído da antiga Portfolio.tsx, que misturava cash com ações na mesma
// lista (ver ESTADO.md secção 11).
export default function CashTab({ positions, currency, currencyOptions, onReload }: Props) {
  const [cashCurrency, setCashCurrency] = useState('EUR');
  const [cashAmount, setCashAmount] = useState('');
  const [cashAdding, setCashAdding] = useState(false);
  const [cashError, setCashError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editQuantity, setEditQuantity] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  const total = positions.reduce((sum, p) => sum + (toNum(p.market_value_converted) ?? toNum(p.market_value) ?? 0), 0);

  async function handleAddCash(e: FormEvent) {
    e.preventDefault();
    if (!cashAmount.trim()) return;
    setCashAdding(true);
    setCashError(null);
    try {
      await api.post('/portfolio/cash', { currency: cashCurrency, amount: cashAmount });
      setCashAmount('');
      await onReload();
    } catch (err) {
      setCashError(err instanceof ApiError ? err.message : 'Erro ao adicionar cash');
    } finally {
      setCashAdding(false);
    }
  }

  function startEdit(p: Position) {
    setEditingId(p.id);
    setEditQuantity(String(p.quantity));
    setEditError(null);
  }

  // Cash não tem preço médio (é sempre 1, ver backend market_data.get_or_create_cash_stock)
  // - guardar mantém sempre avg_cost tal como veio, nunca exposto para editar.
  async function saveEdit(id: string) {
    setEditSaving(true);
    setEditError(null);
    try {
      await api.put(`/portfolio/${id}`, { quantity: editQuantity, avg_cost: '1' });
      setEditingId(null);
      await onReload();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : 'Erro ao guardar');
    } finally {
      setEditSaving(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm('Remover este cash do portfolio?')) return;
    try {
      await api.delete(`/portfolio/${id}`);
      await onReload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao remover');
    }
  }

  return (
    <div>
      {positions.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 text-center">
          <p className="text-xs text-gray-400 dark:text-slate-500">Total em cash</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{money(total, currency)}</p>
        </div>
      )}

      <form onSubmit={handleAddCash} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Adicionar cash</p>
        <div className="flex flex-wrap gap-2">
          <select
            value={cashCurrency}
            onChange={(e) => setCashCurrency(e.target.value)}
            className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
          >
            {currencyOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            value={cashAmount}
            onChange={(e) => setCashAmount(e.target.value)}
            placeholder="Montante"
            inputMode="decimal"
            className="flex-1 min-w-[100px] bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={cashAdding}
            className="bg-navy-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 shrink-0"
          >
            {cashAdding ? '…' : 'Adicionar'}
          </button>
        </div>
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-2">
          Uma posição por moeda — se já tiveres cash em {cashCurrency}, edita o montante existente em vez de
          adicionar outra vez.
        </p>
        {cashError && <p className="text-xs text-red-600 dark:text-rose-400 mt-2">{cashError}</p>}
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {positions.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Ainda não tens cash registado. Adiciona um montante acima para o incluíres no teu património.
        </p>
      ) : (
        <ul className="space-y-2">
          {positions.map((p) => {
            const quantityNum = toNum(p.quantity);
            const editing = editingId === p.id;
            const needsConversion = p.stock.currency !== currency;
            const marketValueConvertedNum = toNum(p.market_value_converted);

            return (
              <li
                key={p.id}
                className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-semibold text-gray-900 dark:text-slate-100">{p.stock.currency}</span>
                  <div className="shrink-0 flex items-center gap-3 text-xs font-medium">
                    <button onClick={() => (editing ? setEditingId(null) : startEdit(p))} className="text-gray-500 dark:text-slate-400">
                      {editing ? 'Cancelar' : 'Editar'}
                    </button>
                    <button onClick={() => handleRemove(p.id)} className="text-red-500 dark:text-rose-400">
                      Remover
                    </button>
                  </div>
                </div>

                {editing ? (
                  <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 dark:border-slate-800 pt-2">
                    <input
                      value={editQuantity}
                      onChange={(e) => setEditQuantity(e.target.value)}
                      inputMode="decimal"
                      className="w-28 bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <span className="text-xs text-gray-400 dark:text-slate-500">{p.stock.currency ?? ''}</span>
                    <button
                      onClick={() => saveEdit(p.id)}
                      disabled={editSaving}
                      className="text-navy-600 dark:text-navy-400 text-xs font-medium disabled:opacity-50"
                    >
                      {editSaving ? 'A guardar…' : 'Guardar'}
                    </button>
                    {editError && <p className="text-xs text-red-600 dark:text-rose-400 w-full">{editError}</p>}
                  </div>
                ) : (
                  <div className="border-t border-gray-100 dark:border-slate-800 pt-2 text-center">
                    <p className="text-xs text-gray-400 dark:text-slate-500">Montante</p>
                    <p className="text-sm text-gray-900 dark:text-slate-100">{money(quantityNum, p.stock.currency)}</p>
                    {needsConversion && marketValueConvertedNum !== null && (
                      <p className="text-xs text-gray-400 dark:text-slate-500">
                        ≈ {money(marketValueConvertedNum, currency)}
                      </p>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
