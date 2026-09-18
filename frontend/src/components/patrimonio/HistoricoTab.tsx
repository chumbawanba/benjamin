import { FormEvent, useEffect, useState } from 'react';
import { ApiError, api } from '../../api/client';
import { PatrimonyCurrentTotals, PatrimonySnapshot } from '../../api/types';
import HistoryChart from './HistoryChart';

function toNum(v: number | string): number {
  const n = Number(v);
  return Number.isNaN(n) ? 0 : n;
}

function money(v: number, currency?: string | null): string {
  return `${v.toFixed(2)} ${currency ?? ''}`.trim();
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

interface FormFields {
  date: string;
  currency: string;
  stocksValue: string;
  cashValue: string;
  otherAssetsValue: string;
  loansBalance: string;
  note: string;
}

function emptyFields(currency: string): FormFields {
  return { date: todayStr(), currency, stocksValue: '', cashValue: '', otherAssetsValue: '', loansBalance: '', note: '' };
}

interface Props {
  snapshots: PatrimonySnapshot[]; // ordenados por data ascendente (ver router patrimony_history.py)
  currency: string;
  onReload: () => Promise<void>;
}

// Separador "Histórico" da página Património (pedido do Edgar: "como posso
// manter um histórico do meu património" - Position/OtherAsset/Loan só
// guardam o valor atual, sem histórico). O utilizador tira "fotografias"
// manuais numa data à escolha - por defeito hoje, com os valores atuais
// pré-preenchidos (GET /patrimony-history/current-totals) para não obrigar a
// calcular tudo à mão, mas também pode escolher uma data passada (ex: "há um
// ano tinha em cash 1000 euros") e preencher os valores manualmente. Uma
// nota opcional documenta o que mudou (ex: "Compra de casa") - mostrada como
// marcador no HistoryChart, mesma ideia do mockup da landing page.
export default function HistoricoTab({ snapshots, currency, onReload }: Props) {
  const [fields, setFields] = useState<FormFields>(() => emptyFields(currency));
  const [prefilling, setPrefilling] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editFields, setEditFields] = useState<FormFields | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);

  const isToday = fields.date === todayStr();

  // Ao escolher "hoje" (por defeito, ou voltando atrás depois de teres
  // escolhido uma data passada), pré-preenche com os totais atuais - o
  // utilizador pode sempre ajustar os valores antes de guardar (ex: já sabe
  // que vai gastar 1000€ que ainda não saíram da conta).
  useEffect(() => {
    if (!isToday) return;
    let cancelled = false;
    setPrefilling(true);
    api
      .get<PatrimonyCurrentTotals>('/patrimony-history/current-totals')
      .then((totals) => {
        if (cancelled) return;
        setFields((f) => ({
          ...f,
          currency: totals.currency,
          stocksValue: String(toNum(totals.stocks_value)),
          cashValue: String(toNum(totals.cash_value)),
          otherAssetsValue: String(toNum(totals.other_assets_value)),
          loansBalance: String(toNum(totals.loans_balance)),
        }));
      })
      .catch(() => {
        // Falha silenciosa - o utilizador ainda pode preencher à mão.
      })
      .finally(() => {
        if (!cancelled) setPrefilling(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fields.date]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setAdding(true);
    setAddError(null);
    try {
      await api.post('/patrimony-history', {
        date: fields.date,
        currency: fields.currency,
        stocks_value: fields.stocksValue || '0',
        cash_value: fields.cashValue || '0',
        other_assets_value: fields.otherAssetsValue || '0',
        loans_balance: fields.loansBalance || '0',
        note: fields.note.trim() || null,
      });
      setFields(emptyFields(currency));
      await onReload();
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : 'Erro ao guardar');
    } finally {
      setAdding(false);
    }
  }

  function startEdit(s: PatrimonySnapshot) {
    setEditingId(s.id);
    setEditFields({
      date: s.date,
      currency: s.currency,
      stocksValue: String(toNum(s.stocks_value)),
      cashValue: String(toNum(s.cash_value)),
      otherAssetsValue: String(toNum(s.other_assets_value)),
      loansBalance: String(toNum(s.loans_balance)),
      note: s.note ?? '',
    });
    setEditError(null);
  }

  async function saveEdit() {
    if (!editFields) return;
    setEditSaving(true);
    setEditError(null);
    try {
      // Upsert por data (POST substitui a entrada existente nessa data - ver
      // routers/patrimony_history.py) - não há PUT/{id} separado, porque
      // "editar" e "criar de novo nessa data" são a mesma operação.
      await api.post('/patrimony-history', {
        date: editFields.date,
        currency: editFields.currency,
        stocks_value: editFields.stocksValue || '0',
        cash_value: editFields.cashValue || '0',
        other_assets_value: editFields.otherAssetsValue || '0',
        loans_balance: editFields.loansBalance || '0',
        note: editFields.note.trim() || null,
      });
      setEditingId(null);
      setEditFields(null);
      await onReload();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : 'Erro ao guardar');
    } finally {
      setEditSaving(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm('Remover esta data do histórico?')) return;
    try {
      await api.delete(`/patrimony-history/${id}`);
      await onReload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao remover');
    }
  }

  return (
    <div>
      {snapshots.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
          <HistoryChart snapshots={snapshots} />
        </div>
      )}

      <form onSubmit={handleAdd} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Registar património numa data</p>
        <div className="flex flex-wrap gap-2 mb-2">
          <input
            type="date"
            value={fields.date}
            max={todayStr()}
            onChange={(e) => setFields((f) => ({ ...f, date: e.target.value }))}
            className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
          />
          {!isToday && (
            <button
              type="button"
              onClick={() => setFields(emptyFields(currency))}
              className="text-xs text-navy-600 dark:text-navy-400 font-medium px-2"
            >
              Hoje
            </button>
          )}
          {isToday && prefilling && <span className="text-xs text-gray-400 dark:text-slate-500 self-center">a carregar valores atuais…</span>}
        </div>
        {isToday && !prefilling && (
          <p className="text-xs text-gray-400 dark:text-slate-500 mb-2">
            Pré-preenchido com os valores atuais — ajusta se precisares.
          </p>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2">
          <div>
            <label className="text-xs text-gray-400 dark:text-slate-500">Ações</label>
            <input
              value={fields.stocksValue}
              onChange={(e) => setFields((f) => ({ ...f, stocksValue: e.target.value }))}
              inputMode="decimal"
              placeholder="0"
              className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 dark:text-slate-500">Cash</label>
            <input
              value={fields.cashValue}
              onChange={(e) => setFields((f) => ({ ...f, cashValue: e.target.value }))}
              inputMode="decimal"
              placeholder="0"
              className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 dark:text-slate-500">Outros ativos</label>
            <input
              value={fields.otherAssetsValue}
              onChange={(e) => setFields((f) => ({ ...f, otherAssetsValue: e.target.value }))}
              inputMode="decimal"
              placeholder="0"
              className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 dark:text-slate-500">Dívida</label>
            <input
              value={fields.loansBalance}
              onChange={(e) => setFields((f) => ({ ...f, loansBalance: e.target.value }))}
              inputMode="decimal"
              placeholder="0"
              className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            value={fields.note}
            onChange={(e) => setFields((f) => ({ ...f, note: e.target.value }))}
            placeholder="Nota (opcional, ex: Compra de casa)"
            className="flex-1 min-w-[200px] bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={adding}
            className="bg-navy-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50 shrink-0"
          >
            {adding ? '…' : 'Guardar'}
          </button>
        </div>
        {addError && <p className="text-xs text-red-600 dark:text-rose-400 mt-2">{addError}</p>}
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {snapshots.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Ainda não tens nenhuma data registada. Guarda a de hoje acima para começares a acompanhar a evolução.
        </p>
      ) : (
        <ul className="space-y-2">
          {[...snapshots].reverse().map((s) => {
            const editing = editingId === s.id;
            return (
              <li key={s.id} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4">
                {editing && editFields ? (
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-2">
                      <input
                        type="date"
                        value={editFields.date}
                        max={todayStr()}
                        onChange={(e) => setEditFields((f) => (f ? { ...f, date: e.target.value } : f))}
                        className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                      />
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      <input
                        value={editFields.stocksValue}
                        onChange={(e) => setEditFields((f) => (f ? { ...f, stocksValue: e.target.value } : f))}
                        inputMode="decimal"
                        placeholder="Ações"
                        className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                      />
                      <input
                        value={editFields.cashValue}
                        onChange={(e) => setEditFields((f) => (f ? { ...f, cashValue: e.target.value } : f))}
                        inputMode="decimal"
                        placeholder="Cash"
                        className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                      />
                      <input
                        value={editFields.otherAssetsValue}
                        onChange={(e) => setEditFields((f) => (f ? { ...f, otherAssetsValue: e.target.value } : f))}
                        inputMode="decimal"
                        placeholder="Outros ativos"
                        className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                      />
                      <input
                        value={editFields.loansBalance}
                        onChange={(e) => setEditFields((f) => (f ? { ...f, loansBalance: e.target.value } : f))}
                        inputMode="decimal"
                        placeholder="Dívida"
                        className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                      />
                    </div>
                    <input
                      value={editFields.note}
                      onChange={(e) => setEditFields((f) => (f ? { ...f, note: e.target.value } : f))}
                      placeholder="Nota (opcional)"
                      className="w-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => void saveEdit()}
                        disabled={editSaving}
                        className="bg-navy-600 text-white rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                      >
                        Guardar
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(null);
                          setEditFields(null);
                        }}
                        className="text-xs text-gray-500 dark:text-slate-400 px-2"
                      >
                        Cancelar
                      </button>
                    </div>
                    {editError && <p className="text-xs text-red-600 dark:text-rose-400">{editError}</p>}
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="font-semibold text-gray-900 dark:text-slate-100">{formatDate(s.date)}</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-slate-100">
                        {money(toNum(s.net_worth), s.currency)}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-slate-400 mb-2">
                      <span>Ações: {money(toNum(s.stocks_value), s.currency)}</span>
                      <span>Cash: {money(toNum(s.cash_value), s.currency)}</span>
                      <span>Outros: {money(toNum(s.other_assets_value), s.currency)}</span>
                      <span>Dívida: {money(toNum(s.loans_balance), s.currency)}</span>
                    </div>
                    {s.note && <p className="text-xs text-navy-600 dark:text-navy-400 mb-2">{s.note}</p>}
                    <div className="flex gap-2">
                      <button onClick={() => startEdit(s)} className="text-xs text-navy-600 dark:text-navy-400 font-medium">
                        Editar
                      </button>
                      <button onClick={() => void handleRemove(s.id)} className="text-xs text-red-600 dark:text-rose-400 font-medium">
                        Remover
                      </button>
                    </div>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
