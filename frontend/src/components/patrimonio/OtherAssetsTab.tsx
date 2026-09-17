import { FormEvent, useMemo, useState } from 'react';
import { ApiError, api } from '../../api/client';
import { OtherAsset } from '../../api/types';

const COMMON_CURRENCIES = ['EUR', 'USD', 'GBP'];

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
  assets: OtherAsset[];
  category: 'imovel' | 'outro';
  itemLabel: string;
  namePlaceholder: string;
  emptyMessage: string;
  onReload: () => Promise<void>;
}

// Separadores "Imóveis" e "Outros" da página Património - ambos usam a mesma
// entidade OtherAsset (só muda a `category`), por isso este componente é
// genérico e reutilizado pelos dois (ver ESTADO.md secção 11: imóveis,
// certificados de aforro/tesouro, etc. - fora do Portfolio de ações/cash e
// dos Empréstimos). `expected_return_pct` é opcional - cada ativo cresce à
// sua própria taxa na Projeção (ver services/projection.py), 0/None mantém
// o valor constante lá.
export default function OtherAssetsTab({ assets, category, itemLabel, namePlaceholder, emptyMessage, onReload }: Props) {
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('EUR');
  const [value, setValue] = useState('');
  const [expectedReturnPct, setExpectedReturnPct] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editValue, setEditValue] = useState('');
  const [editExpectedReturnPct, setEditExpectedReturnPct] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  const currencyOptions = useMemo(() => {
    const fromAssets = assets.map((a) => a.currency);
    return Array.from(new Set([...COMMON_CURRENCIES, ...fromAssets]));
  }, [assets]);

  // Moeda de referência para o total: a do primeiro ativo (display_currency é
  // sempre User.preferred_currency, igual em todos - ver routers/other_assets.py).
  const displayCurrency = assets[0]?.display_currency ?? 'EUR';

  const totals = useMemo(() => {
    let total = 0;
    let hasUnknown = false;
    for (const a of assets) {
      const converted = toNum(a.value_converted) ?? toNum(a.value);
      if (converted === null) {
        hasUnknown = true;
      } else {
        total += converted;
      }
    }
    return { total, hasUnknown, hasAny: assets.length > 0 };
  }, [assets]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !value.trim()) return;
    setAdding(true);
    setAddError(null);
    try {
      await api.post('/other-assets', {
        category,
        name: name.trim(),
        currency,
        value,
        expected_return_pct: expectedReturnPct.trim() || null,
      });
      setName('');
      setValue('');
      setExpectedReturnPct('');
      await onReload();
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : `Erro ao adicionar ${itemLabel}`);
    } finally {
      setAdding(false);
    }
  }

  function startEdit(a: OtherAsset) {
    setEditingId(a.id);
    setEditName(a.name);
    setEditValue(String(a.value));
    setEditExpectedReturnPct(a.expected_return_pct === null ? '' : String(a.expected_return_pct));
    setEditError(null);
  }

  async function saveEdit(id: string) {
    setEditSaving(true);
    setEditError(null);
    try {
      await api.put(`/other-assets/${id}`, {
        name: editName.trim(),
        value: editValue,
        expected_return_pct: editExpectedReturnPct.trim() || null,
      });
      setEditingId(null);
      await onReload();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : 'Erro ao guardar');
    } finally {
      setEditSaving(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm(`Remover este ${itemLabel}?`)) return;
    try {
      await api.delete(`/other-assets/${id}`);
      await onReload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao remover');
    }
  }

  return (
    <div>
      {totals.hasAny && (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 text-center">
          <p className="text-xs text-gray-400 dark:text-slate-500">Valor total</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
            {money(totals.total, displayCurrency)}
            {totals.hasUnknown && '*'}
          </p>
          {totals.hasUnknown && (
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">* exclui ativos sem câmbio conhecido ainda</p>
          )}
        </div>
      )}

      <form onSubmit={handleAdd} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Adicionar {itemLabel}</p>
        <div className="flex flex-wrap gap-2 mb-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={namePlaceholder}
            className="flex-1 min-w-[160px] bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
          >
            {currencyOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Valor atual"
            inputMode="decimal"
            className="w-32 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <input
            value={expectedReturnPct}
            onChange={(e) => setExpectedReturnPct(e.target.value)}
            placeholder="Rendimento anual esperado % (opcional)"
            inputMode="decimal"
            className="w-56 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={adding}
            className="bg-navy-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 shrink-0"
          >
            {adding ? '…' : 'Adicionar'}
          </button>
        </div>
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-2">
          O rendimento esperado é usado na Projeção de património — cada ativo cresce à sua própria taxa em
          vez da taxa geral do portfolio. Deixa em branco para manter o valor constante na projeção.
        </p>
        {addError && <p className="text-xs text-red-600 dark:text-rose-400 mt-2">{addError}</p>}
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {assets.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">{emptyMessage}</p>
      ) : (
        <ul className="space-y-2">
          {assets.map((a) => {
            const editing = editingId === a.id;
            const valueNum = toNum(a.value);
            const valueConvertedNum = toNum(a.value_converted);
            const needsConversion = a.currency !== a.display_currency;

            return (
              <li
                key={a.id}
                className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-semibold text-gray-900 dark:text-slate-100">{a.name}</span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">{a.currency}</span>
                </div>

                {editing ? (
                  <div className="flex flex-wrap gap-2 items-center">
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 min-w-[140px] bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <input
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      inputMode="decimal"
                      placeholder="Valor"
                      className="w-28 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <input
                      value={editExpectedReturnPct}
                      onChange={(e) => setEditExpectedReturnPct(e.target.value)}
                      inputMode="decimal"
                      placeholder="Rend. %"
                      className="w-24 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <button
                      onClick={() => void saveEdit(a.id)}
                      disabled={editSaving}
                      className="bg-navy-600 text-white rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                    >
                      Guardar
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="text-xs text-gray-500 dark:text-slate-400 px-2"
                    >
                      Cancelar
                    </button>
                    {editError && <p className="text-xs text-red-600 dark:text-rose-400 w-full">{editError}</p>}
                  </div>
                ) : (
                  <div className="flex flex-wrap items-end justify-between gap-2">
                    <div className="flex flex-wrap gap-4 text-sm">
                      <div>
                        <p className="text-xs text-gray-400 dark:text-slate-500">Valor</p>
                        <p className="font-semibold text-gray-900 dark:text-slate-100">
                          {money(valueNum, a.currency)}
                          {needsConversion && valueConvertedNum !== null && (
                            <span className="text-xs font-normal text-gray-400 dark:text-slate-500">
                              {' '}≈ {money(valueConvertedNum, a.display_currency)}
                            </span>
                          )}
                        </p>
                      </div>
                      {a.expected_return_pct !== null && (
                        <div>
                          <p className="text-xs text-gray-400 dark:text-slate-500">Rendimento esperado</p>
                          <p className="font-semibold text-gray-900 dark:text-slate-100">{toNum(a.expected_return_pct)}%</p>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => startEdit(a)}
                        className="text-xs text-navy-600 dark:text-navy-400 font-medium"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => void handleRemove(a.id)}
                        className="text-xs text-red-600 dark:text-rose-400 font-medium"
                      >
                        Remover
                      </button>
                    </div>
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
