import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { Loan, OtherAsset, PatrimonySnapshot, PortfolioCurrency, Position, WatchlistItem } from '../api/types';
import AcoesTab from '../components/patrimonio/AcoesTab';
import CashTab from '../components/patrimonio/CashTab';
import EmprestimosTab from '../components/patrimonio/EmprestimosTab';
import HistoricoTab from '../components/patrimonio/HistoricoTab';
import OtherAssetsTab from '../components/patrimonio/OtherAssetsTab';
import { IconBanknote, IconBuilding, IconHistory, IconLayers, IconTrendingUp, IconWallet } from '../components/icons';

// Moedas sempre disponíveis nos seletores, mesmo sem nenhuma posição/ativo
// ainda nelas - cobre o caso comum (EUR/USD) sem forçar o utilizador a já
// ter algo nessa moeda. Mesmo padrão das antigas Portfolio.tsx/Loans.tsx.
const COMMON_CURRENCIES = ['EUR', 'USD', 'GBP'];

type Tab = 'acoes' | 'cash' | 'imoveis' | 'outros' | 'emprestimos' | 'historico';

const TABS: { key: Tab; label: string; icon: typeof IconWallet }[] = [
  { key: 'acoes', label: 'Ações', icon: IconTrendingUp },
  { key: 'cash', label: 'Cash', icon: IconWallet },
  { key: 'imoveis', label: 'Imóveis', icon: IconBuilding },
  { key: 'outros', label: 'Outros', icon: IconLayers },
  { key: 'emprestimos', label: 'Empréstimos', icon: IconBanknote },
  { key: 'historico', label: 'Histórico', icon: IconHistory },
];

function isTab(value: string | null): value is Tab {
  return (
    value === 'acoes' || value === 'cash' || value === 'imoveis' || value === 'outros' ||
    value === 'emprestimos' || value === 'historico'
  );
}

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

// Página "Património" - substitui a antiga Portfolio.tsx (rota /portfolio) e
// agrupa Ações, Cash, Imóveis, Outros e Empréstimos (antiga Loans.tsx, rota
// /loans) em separadores, pedido do Edgar depois de perguntar onde colocar
// imóveis/certificados de tesouro (ver ESTADO.md secção 11): "estava a pensar
// ter um 'património' em vez de portfolio e dentro vários separadores
// (portfolio ações, imoveis, cash, outros)". O separador ativo vem de ?tab=
// na URL (mesmo padrão de StrategyWorkspace.tsx), para outras páginas
// poderem linkar já para o separador certo.
//
// A moeda preferida (currency) é um único valor global do utilizador (ver
// User.preferred_currency no backend) - por isso o seletor vive aqui, ao
// nível da página, e afeta a conversão em todos os separadores, não só em
// Ações/Cash.
export default function Patrimonio() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');
  const tab: Tab = isTab(tabParam) ? tabParam : 'acoes';

  function selectTab(next: Tab) {
    setSearchParams(next === 'acoes' ? {} : { tab: next });
  }

  const [positions, setPositions] = useState<Position[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [otherAssets, setOtherAssets] = useState<OtherAsset[]>([]);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [patrimonyHistory, setPatrimonyHistory] = useState<PatrimonySnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [currency, setCurrency] = useState<string>('EUR');
  const [currencySaving, setCurrencySaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [posData, curr, wl, assetsData, loansData, historyData] = await Promise.all([
        api.get<Position[]>('/portfolio'),
        api.get<PortfolioCurrency>('/portfolio/currency'),
        api.get<WatchlistItem[]>('/watchlist'),
        api.get<OtherAsset[]>('/other-assets'),
        api.get<Loan[]>('/loans'),
        api.get<PatrimonySnapshot[]>('/patrimony-history'),
      ]);
      setPositions(posData);
      setCurrency(curr.currency);
      setWatchlist(wl);
      setOtherAssets(assetsData);
      setLoans(loansData);
      setPatrimonyHistory(historyData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erro ao carregar património');
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

  const stockPositions = useMemo(() => positions.filter((p) => p.stock.asset_type !== 'cash'), [positions]);
  const cashPositions = useMemo(() => positions.filter((p) => p.stock.asset_type === 'cash'), [positions]);
  const imoveis = useMemo(() => otherAssets.filter((a) => a.category === 'imovel'), [otherAssets]);
  const outros = useMemo(() => otherAssets.filter((a) => a.category === 'outro'), [otherAssets]);

  const currencyOptions = useMemo(() => {
    const fromData = [
      ...positions.map((p) => p.stock.currency),
      ...otherAssets.map((a) => a.currency),
      ...loans.map((l) => l.currency),
    ].filter((c): c is string => !!c);
    return Array.from(new Set([...COMMON_CURRENCIES, ...fromData, currency]));
  }, [positions, otherAssets, loans, currency]);

  // Património líquido = ações + cash + imóveis + outros - empréstimos, tudo
  // convertido para a moeda preferida (mesmo padrão de conversão do resto da
  // app - cai para o valor nativo só quando a moeda já coincide).
  const netWorth = useMemo(() => {
    let assetsTotal = 0;
    let hasUnknown = false;
    for (const p of positions) {
      const v = toNum(p.market_value_converted) ?? (p.stock.currency === currency ? toNum(p.market_value) : null);
      if (v === null) hasUnknown = true;
      else assetsTotal += v;
    }
    for (const a of otherAssets) {
      const v = toNum(a.value_converted) ?? (a.currency === currency ? toNum(a.value) : null);
      if (v === null) hasUnknown = true;
      else assetsTotal += v;
    }
    let loansTotal = 0;
    for (const l of loans) {
      const v = toNum(l.balance_converted) ?? (l.currency === currency ? toNum(l.balance) : null);
      if (v === null) hasUnknown = true;
      else loansTotal += v;
    }
    return { value: assetsTotal - loansTotal, hasUnknown, hasAny: positions.length > 0 || otherAssets.length > 0 || loans.length > 0 };
  }, [positions, otherAssets, loans, currency]);

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">Património</h1>
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

      {!loading && netWorth.hasAny && (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4 text-center">
          <p className="text-xs text-gray-400 dark:text-slate-500">
            Património líquido
            {netWorth.hasUnknown && '*'}
          </p>
          <p className={`text-lg font-bold ${plColorClass(netWorth.value)}`}>{money(netWorth.value, currency)}</p>
          {netWorth.hasUnknown && (
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
              * exclui valores sem preço de mercado ou câmbio conhecido ainda
            </p>
          )}
        </div>
      )}

      {error && <p className="text-sm text-red-600 dark:text-rose-400 mb-4">{error}</p>}

      <div className="flex border-b border-gray-200 dark:border-slate-800 mb-4 overflow-x-auto">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => selectTab(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 whitespace-nowrap px-2 text-center py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === key
                ? 'text-navy-600 dark:text-navy-400 border-navy-600 dark:border-navy-400'
                : 'text-gray-400 dark:text-slate-500 border-transparent'
            }`}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>
      ) : (
        <>
          {tab === 'acoes' && (
            <AcoesTab positions={stockPositions} watchlist={watchlist} currency={currency} onReload={load} />
          )}
          {tab === 'cash' && (
            <CashTab positions={cashPositions} currency={currency} currencyOptions={currencyOptions} onReload={load} />
          )}
          {tab === 'imoveis' && (
            <OtherAssetsTab
              assets={imoveis}
              category="imovel"
              itemLabel="imóvel"
              namePlaceholder="Nome (ex: Apartamento T2 Lisboa)"
              emptyMessage="Ainda não tens imóveis registados. Adiciona um acima para o incluíres no teu património."
              onReload={load}
            />
          )}
          {tab === 'outros' && (
            <OtherAssetsTab
              assets={outros}
              category="outro"
              itemLabel="ativo"
              namePlaceholder="Nome (ex: Certificados de aforro)"
              emptyMessage="Ainda não tens outros ativos registados. Adiciona um acima para o incluíres no teu património."
              onReload={load}
            />
          )}
          {tab === 'emprestimos' && <EmprestimosTab loans={loans} onReload={load} />}
          {tab === 'historico' && (
            <HistoricoTab snapshots={patrimonyHistory} currency={currency} onReload={load} />
          )}
        </>
      )}
    </div>
  );
}
