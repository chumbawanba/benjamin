import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ApiError, api } from '../api/client';
import { Loan } from '../api/types';

// Moedas sempre disponíveis no seletor, mesmo padrão de Portfolio.tsx
// (COMMON_CURRENCIES) - cobre o caso comum sem forçar o utilizador a já ter
// um empréstimo nessa moeda.
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

export default function Loans() {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('EUR');
  const [balance, setBalance] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [monthlyPayment, setMonthlyPayment] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editBalance, setEditBalance] = useState('');
  const [editInterestRate, setEditInterestRate] = useState('');
  const [editMonthlyPayment, setEditMonthlyPayment] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await api.get<Loan[]>('/loans');
      setLoans(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar empréstimos');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const currencyOptions = useMemo(() => {
    const fromLoans = loans.map((l) => l.currency);
    return Array.from(new Set([...COMMON_CURRENCIES, ...fromLoans]));
  }, [loans]);

  // Moeda de referência para o total: a do primeiro empréstimo (display_currency
  // é sempre User.preferred_currency, igual em todos - ver routers/loans.py).
  const displayCurrency = loans[0]?.display_currency ?? 'EUR';

  const totals = useMemo(() => {
    let balanceTotal = 0;
    let monthlyTotal = 0;
    let hasUnknown = false;
    for (const l of loans) {
      const converted = toNum(l.balance_converted) ?? toNum(l.balance);
      if (converted === null) {
        hasUnknown = true;
      } else {
        balanceTotal += converted;
      }
      const payment = toNum(l.monthly_payment);
      if (payment !== null) {
        // Prestação não é convertida (é só informação de referência) - soma-se
        // tal como está, por isso só faz sentido quando todos os empréstimos
        // estão na mesma moeda que a preferida (aviso abaixo cobre o resto).
        monthlyTotal += payment;
      }
    }
    return { balanceTotal, monthlyTotal, hasUnknown, hasAny: loans.length > 0 };
  }, [loans]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !balance.trim()) return;
    setAdding(true);
    setAddError(null);
    try {
      await api.post('/loans', {
        name: name.trim(),
        currency,
        balance,
        interest_rate: interestRate.trim() || null,
        monthly_payment: monthlyPayment.trim() || null,
      });
      setName('');
      setBalance('');
      setInterestRate('');
      setMonthlyPayment('');
      await load();
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : 'Erro ao adicionar empréstimo');
    } finally {
      setAdding(false);
    }
  }

  function startEdit(l: Loan) {
    setEditingId(l.id);
    setEditName(l.name);
    setEditBalance(String(l.balance));
    setEditInterestRate(l.interest_rate === null ? '' : String(l.interest_rate));
    setEditMonthlyPayment(l.monthly_payment === null ? '' : String(l.monthly_payment));
    setEditError(null);
  }

  async function saveEdit(id: string) {
    setEditSaving(true);
    setEditError(null);
    try {
      await api.put(`/loans/${id}`, {
        name: editName.trim(),
        balance: editBalance,
        interest_rate: editInterestRate.trim() || null,
        monthly_payment: editMonthlyPayment.trim() || null,
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : 'Erro ao guardar');
    } finally {
      setEditSaving(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm('Remover este empréstimo?')) return;
    try {
      await api.delete(`/loans/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao remover');
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Empréstimos</h1>

      {totals.hasAny && (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 grid grid-cols-2 gap-2 text-center">
          <div>
            <p className="text-xs text-gray-400 dark:text-slate-500">Total em dívida</p>
            <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
              {money(totals.balanceTotal, displayCurrency)}
              {totals.hasUnknown && '*'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 dark:text-slate-500">Prestações mensais</p>
            <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
              {totals.monthlyTotal > 0 ? money(totals.monthlyTotal, displayCurrency) : '—'}
            </p>
          </div>
          {totals.hasUnknown && (
            <p className="col-span-2 text-xs text-gray-400 dark:text-slate-500 mt-1">
              * exclui empréstimos sem câmbio conhecido ainda
            </p>
          )}
        </div>
      )}

      <form onSubmit={handleAdd} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Adicionar empréstimo</p>
        <div className="flex flex-wrap gap-2 mb-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nome (ex: Crédito habitação)"
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
            value={balance}
            onChange={(e) => setBalance(e.target.value)}
            placeholder="Saldo em dívida"
            inputMode="decimal"
            className="w-32 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <input
            value={interestRate}
            onChange={(e) => setInterestRate(e.target.value)}
            placeholder="Taxa de juro % (opcional)"
            inputMode="decimal"
            className="w-40 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <input
            value={monthlyPayment}
            onChange={(e) => setMonthlyPayment(e.target.value)}
            placeholder="Prestação mensal (opcional)"
            inputMode="decimal"
            className="w-44 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
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
          Taxa de juro e prestação são só informação de referência — não recalculam o saldo automaticamente.
          Atualiza o saldo à medida que fores pagando.
        </p>
        {addError && <p className="text-xs text-red-600 dark:text-rose-400 mt-2">{addError}</p>}
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : loans.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Ainda não tens empréstimos registados. Adiciona um acima para acompanhares o teu património líquido.
        </p>
      ) : (
        <ul className="space-y-2">
          {loans.map((l) => {
            const editing = editingId === l.id;
            const balanceNum = toNum(l.balance);
            const balanceConvertedNum = toNum(l.balance_converted);
            const needsConversion = l.currency !== l.display_currency;

            return (
              <li
                key={l.id}
                className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-semibold text-gray-900 dark:text-slate-100">{l.name}</span>
                  <span className="text-xs text-gray-400 dark:text-slate-500">{l.currency}</span>
                </div>

                {editing ? (
                  <div className="flex flex-wrap gap-2 items-center">
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 min-w-[140px] bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <input
                      value={editBalance}
                      onChange={(e) => setEditBalance(e.target.value)}
                      inputMode="decimal"
                      placeholder="Saldo"
                      className="w-28 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <input
                      value={editInterestRate}
                      onChange={(e) => setEditInterestRate(e.target.value)}
                      inputMode="decimal"
                      placeholder="Taxa %"
                      className="w-24 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <input
                      value={editMonthlyPayment}
                      onChange={(e) => setEditMonthlyPayment(e.target.value)}
                      inputMode="decimal"
                      placeholder="Prestação"
                      className="w-28 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <button
                      onClick={() => void saveEdit(l.id)}
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
                        <p className="text-xs text-gray-400 dark:text-slate-500">Saldo em dívida</p>
                        <p className="font-semibold text-gray-900 dark:text-slate-100">
                          {money(balanceNum, l.currency)}
                          {needsConversion && balanceConvertedNum !== null && (
                            <span className="text-xs font-normal text-gray-400 dark:text-slate-500">
                              {' '}≈ {money(balanceConvertedNum, l.display_currency)}
                            </span>
                          )}
                        </p>
                      </div>
                      {l.interest_rate !== null && (
                        <div>
                          <p className="text-xs text-gray-400 dark:text-slate-500">Taxa de juro</p>
                          <p className="font-semibold text-gray-900 dark:text-slate-100">{toNum(l.interest_rate)}%</p>
                        </div>
                      )}
                      {l.monthly_payment !== null && (
                        <div>
                          <p className="text-xs text-gray-400 dark:text-slate-500">Prestação mensal</p>
                          <p className="font-semibold text-gray-900 dark:text-slate-100">
                            {money(toNum(l.monthly_payment), l.currency)}
                          </p>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => startEdit(l)}
                        className="text-xs text-navy-600 dark:text-navy-400 font-medium"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => void handleRemove(l.id)}
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
