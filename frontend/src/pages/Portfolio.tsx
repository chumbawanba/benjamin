import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { PortfolioCurrency, Position, WatchlistItem } from '../api/types';
import PortfolioAllocationChart from '../components/PortfolioAllocationChart';
import PriceChange from '../components/PriceChange';

// Moedas sempre disponíveis no seletor, mesmo sem nenhuma posição ainda nelas -
// cobre o caso comum (EUR/USD) sem forçar o utilizador a já ter uma posição
// nessa moeda. Outras moedas presentes nas posições (ex: GBP) são adicionadas
// dinamicamente em `currencyOptions`.
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

function plColorClass(v: number | null): string {
  if (v === null) return 'text-gray-400 dark:text-slate-500';
  if (v > 0) return 'text-green-600 dark:text-emerald-400';
  if (v < 0) return 'text-red-600 dark:text-rose-400';
  return 'text-gray-400 dark:text-slate-500';
}

export default function Portfolio() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [currency, setCurrency] = useState<string>('EUR');
  const [currencySaving, setCurrencySaving] = useState(false);

  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [avgCost, setAvgCost] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editQuantity, setEditQuantity] = useState('');
  const [editAvgCost, setEditAvgCost] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [data, curr, wl] = await Promise.all([
        api.get<Position[]>('/portfolio'),
        api.get<PortfolioCurrency>('/portfolio/currency'),
        api.get<WatchlistItem[]>('/watchlist'),
      ]);
      setPositions(data);
      setCurrency(curr.currency);
      setWatchlist(wl);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar portfolio');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCurrencyChange(next: string) {
    setCurrencySaving(true);
    try {
      await api.put<PortfolioCurrency>('/portfolio/currency', { currency: next });
      setCurrency(next);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao mudar de moeda');
    } finally {
      setCurrencySaving(false);
    }
  }

  const currencyOptions = useMemo(() => {
    const fromPositions = positions.map((p) => p.stock.currency).filter((c): c is string => !!c);
    return Array.from(new Set([...COMMON_CURRENCIES, ...fromPositions, currency]));
  }, [positions, currency]);

  // Para o link "ver detalhe" de cada posição — a página StockDetail é
  // indexada por watchlist_item_id, não por stock_id, por isso só há link
  // quando a ação da posição também está na watchlist (mesmo padrão de
  // Overview.tsx::watchlistByStockId).
  const watchlistByStockId = useMemo(() => {
    const map = new Map<string, WatchlistItem>();
    watchlist.forEach((w) => map.set(w.stock.id, w));
    return map;
  }, [watchlist]);

  // Ações da watchlist que ainda não têm posição — usado no dropdown "ou
  // escolhe da watchlist" do formulário de adicionar (o backend rejeita uma
  // 2ª posição na mesma ação, por isso já não faz sentido oferecê-las aqui).
  const positionedTickers = useMemo(() => new Set(positions.map((p) => p.stock.ticker)), [positions]);
  const watchlistOptions = useMemo(
    () => watchlist.filter((w) => !positionedTickers.has(w.stock.ticker)),
    [watchlist, positionedTickers],
  );

  const totals = useMemo(() => {
    let costTotal = 0;
    let valueKnown = 0;
    let costOfKnown = 0;
    for (const p of positions) {
      // Usa o valor convertido quando disponível (posições em moedas diferentes
      // da preferida) - cai para o valor nativo só quando a moeda já coincide
      // (cost_total_converted vem null nesse caso, ver routers/portfolio.py).
      const cost = toNum(p.cost_total_converted) ?? toNum(p.cost_total) ?? 0;
      costTotal += cost;
      const mv = toNum(p.market_value_converted) ?? toNum(p.market_value);
      if (mv !== null) {
        valueKnown += mv;
        costOfKnown += cost;
      }
    }
    const pl = valueKnown - costOfKnown;
    const plPct = costOfKnown !== 0 ? (pl / costOfKnown) * 100 : null;
    const hasUnknown = positions.some(
      (p) => toNum(p.market_value) === null || (p.stock.currency !== currency && toNum(p.market_value_converted) === null),
    );
    return { costTotal, valueKnown, pl, plPct, hasUnknown, hasAny: positions.length > 0 };
  }, [positions, currency]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!ticker.trim() || !quantity.trim() || !avgCost.trim()) return;
    setAdding(true);
    setAddError(null);
    try {
      await api.post('/portfolio', { ticker: ticker.trim(), quantity, avg_cost: avgCost });
      setTicker('');
      setQuantity('');
      setAvgCost('');
      await load();
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : 'Erro ao adicionar posição');
    } finally {
      setAdding(false);
    }
  }

  function startEdit(p: Position) {
    setEditingId(p.id);
    setEditQuantity(String(p.quantity));
    setEditAvgCost(String(p.avg_cost));
    setEditError(null);
  }

  async function saveEdit(id: string) {
    setEditSaving(true);
    setEditError(null);
    try {
      await api.put(`/portfolio/${id}`, { quantity: editQuantity, avg_cost: editAvgCost });
      setEditingId(null);
      await load();
    } catch (err) {
      setEditError(err instanceof ApiError ? err.message : 'Erro ao guardar');
    } finally {
      setEditSaving(false);
    }
  }

  async function handleRemove(id: string) {
    if (!confirm('Remover esta posição do portfolio?')) return;
    try {
      await api.delete(`/portfolio/${id}`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao remover');
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">Portfolio</h1>
        <label className="flex items-center gap-2 text-xs text-gray-500 dark:text-slate-400">
          Moeda
          <select
            value={currency}
            disabled={currencySaving}
            onChange={(e) => void handleCurrencyChange(e.target.value)}
            className="bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1 text-xs disabled:opacity-50"
          >
            {currencyOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <Link to="/portfolio/fx-rates" className="inline-block text-xs text-navy-600 dark:text-navy-400 font-medium mb-4">
        Ver taxas de câmbio →
      </Link>

      {totals.hasAny && (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="text-xs text-gray-400 dark:text-slate-500">Custo total</p>
            <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{money(totals.costTotal, currency)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 dark:text-slate-500">Valor de mercado</p>
            <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
              {money(totals.valueKnown, currency)}
              {totals.hasUnknown && '*'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 dark:text-slate-500">P&L não realizado</p>
            <p className={`text-sm font-semibold ${plColorClass(totals.pl)}`}>
              {money(totals.pl, currency)}
              {totals.plPct !== null && ` (${totals.plPct > 0 ? '+' : ''}${totals.plPct.toFixed(2)}%)`}
            </p>
          </div>
          {totals.hasUnknown && (
            <p className="col-span-3 text-xs text-gray-400 dark:text-slate-500 mt-1">
              * exclui posições sem preço de mercado ou câmbio conhecido ainda
            </p>
          )}
        </div>
      )}

      {totals.hasAny && (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-3">Distribuição do portfolio</p>
          <PortfolioAllocationChart positions={positions} />
        </div>
      )}

      <form onSubmit={handleAdd} className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
        <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Adicionar posição</p>
        {watchlistOptions.length > 0 && (
          <label className="flex items-center gap-2 text-xs text-gray-500 dark:text-slate-400 mb-2">
            Ou escolhe da watchlist
            <select
              value=""
              onChange={(e) => e.target.value && setTicker(e.target.value)}
              className="flex-1 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-xs"
            >
              <option value="">Escolher…</option>
              {watchlistOptions.map((w) => (
                <option key={w.id} value={w.stock.ticker}>
                  {w.stock.ticker} {w.stock.name ? `— ${w.stock.name}` : ''}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="flex flex-wrap gap-2">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="Ticker (ex: AAPL)"
            className="flex-1 min-w-[100px] bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <input
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="Quantidade"
            inputMode="decimal"
            className="w-28 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
          />
          <input
            value={avgCost}
            onChange={(e) => setAvgCost(e.target.value)}
            placeholder="Preço médio"
            inputMode="decimal"
            className="w-28 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 placeholder:text-gray-400 dark:placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm"
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
          O preço médio deve estar na moeda em que a ação negoceia (ex: USD para ações dos EUA, EUR para
          europeias) — não na tua moeda preferida. A conversão para a moeda que escolheste acima é feita
          automaticamente.
        </p>
        {addError && <p className="text-xs text-red-600 dark:text-rose-400 mt-2">{addError}</p>}
      </form>

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : positions.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">
          Ainda não tens posições registadas. Adiciona uma acima para começares a acompanhar o P&L real.
        </p>
      ) : (
        <ul className="space-y-2">
          {positions.map((p) => {
            const quantityNum = toNum(p.quantity);
            const avgCostNum = toNum(p.avg_cost);
            const costTotalNum = toNum(p.cost_total);
            const marketValueNum = toNum(p.market_value);
            const plNum = toNum(p.unrealized_pl);
            const plPctNum = toNum(p.unrealized_pl_pct);
            const editing = editingId === p.id;
            // Só mostra o "≈ convertido" quando a moeda da ação é diferente da
            // preferida - evita repetir o mesmo valor duas vezes sem necessidade.
            const needsConversion = p.stock.currency !== currency;
            const marketValueConvertedNum = toNum(p.market_value_converted);
            const plConvertedNum = toNum(p.unrealized_pl_converted);
            const wlItem = watchlistByStockId.get(p.stock.id);

            return (
              <li
                key={p.id}
                className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="min-w-0">
                    <div className="flex items-baseline gap-2">
                      {wlItem ? (
                        <Link
                          to={`/stocks/${wlItem.id}`}
                          className="font-semibold text-gray-900 dark:text-slate-100 hover:text-navy-600 dark:hover:text-navy-400"
                        >
                          {p.stock.ticker}
                        </Link>
                      ) : (
                        <span className="font-semibold text-gray-900 dark:text-slate-100">{p.stock.ticker}</span>
                      )}
                      {p.stock.asset_type === 'etf' && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-navy-50 text-navy-700 dark:bg-navy-500/15 dark:text-navy-400">
                          ETF
                        </span>
                      )}
                      <span className="text-sm">
                        <PriceChange price={p.last_price} changePct={p.price_change_pct} currency={p.stock.currency} />
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-slate-400">{p.stock.name ?? '—'}</p>
                  </div>
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
                      className="w-24 bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
                    />
                    <span className="text-xs text-gray-400 dark:text-slate-500">×</span>
                    <input
                      value={editAvgCost}
                      onChange={(e) => setEditAvgCost(e.target.value)}
                      inputMode="decimal"
                      className="w-24 bg-gray-50 dark:bg-slate-800 border border-gray-300 dark:border-slate-700 text-gray-900 dark:text-slate-100 rounded-lg px-2 py-1.5 text-sm"
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
                  <div className="grid grid-cols-3 gap-2 text-center border-t border-gray-100 dark:border-slate-800 pt-2">
                    <div>
                      <p className="text-xs text-gray-400 dark:text-slate-500">
                        {quantityNum ?? '—'} × {money(avgCostNum, p.stock.currency)}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-slate-400">Custo: {money(costTotalNum, p.stock.currency)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 dark:text-slate-500">Valor</p>
                      <p className="text-sm text-gray-900 dark:text-slate-100">{money(marketValueNum, p.stock.currency)}</p>
                      {needsConversion && marketValueConvertedNum !== null && (
                        <p className="text-xs text-gray-400 dark:text-slate-500">
                          ≈ {money(marketValueConvertedNum, currency)}
                        </p>
                      )}
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 dark:text-slate-500">P&L</p>
                      <p className={`text-sm font-medium ${plColorClass(plNum)}`}>
                        {money(plNum, p.stock.currency)}
                        {plPctNum !== null && (
                          <span className="block text-xs">
                            {plPctNum > 0 ? '+' : ''}
                            {plPctNum.toFixed(2)}%
                          </span>
                        )}
                      </p>
                      {needsConversion && plConvertedNum !== null && (
                        <p className="text-xs text-gray-400 dark:text-slate-500">≈ {money(plConvertedNum, currency)}</p>
                      )}
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
