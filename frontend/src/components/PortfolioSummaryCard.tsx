import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Loan, OtherAsset, PortfolioCurrency, Position } from '../api/types';
import PortfolioAllocationChart from './PortfolioAllocationChart';

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

// Resumo compacto do portfolio de ações (custo/valor/P&L) e, quando há
// empréstimos e/ou outros ativos registados (imóveis, certificados, etc. -
// ver ESTADO.md secção 11), do património líquido (ações + cash + imóveis +
// outros - total em dívida) no topo do Overview, com link para a página
// Património para o detalhe por separador. Não aparece se o utilizador
// ainda não registou nada — evita ruído para quem só usa a
// watchlist/estratégias.
export default function PortfolioSummaryCard() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [otherAssets, setOtherAssets] = useState<OtherAsset[]>([]);
  const [currency, setCurrency] = useState<string>('EUR');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<Position[]>('/portfolio'),
      api.get<PortfolioCurrency>('/portfolio/currency'),
      api.get<Loan[]>('/loans').catch(() => []),
      api.get<OtherAsset[]>('/other-assets').catch(() => []),
    ])
      .then(([data, curr, loanData, assetsData]) => {
        setPositions(data);
        setCurrency(curr.currency);
        setLoans(loanData);
        setOtherAssets(assetsData);
      })
      .catch(() => setPositions([]))
      .finally(() => setLoading(false));
  }, []);

  // Mesma lógica de conversão da página Património (ver AcoesTab.tsx) - usa o
  // valor já convertido para a moeda preferida quando a ação está numa moeda
  // diferente, para não somar EUR com USD sem conversão.
  const totals = useMemo(() => {
    let costTotal = 0;
    let valueKnown = 0;
    let costOfKnown = 0;
    for (const p of positions) {
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
    return { costTotal, valueKnown, pl, plPct };
  }, [positions]);

  // Total em dívida, na mesma moeda preferida (balance_converted, ver
  // routers/loans.py) - mesmo padrão de conversão que os totais acima.
  const loansTotal = useMemo(() => {
    let total = 0;
    let hasUnknown = false;
    for (const l of loans) {
      const converted = toNum(l.balance_converted) ?? (l.currency === currency ? toNum(l.balance) : null);
      if (converted === null) {
        hasUnknown = true;
      } else {
        total += converted;
      }
    }
    return { total, hasUnknown };
  }, [loans, currency]);

  // Valor dos outros ativos (imóveis, certificados, etc. - ver
  // routers/other_assets.py), mesmo padrão de conversão.
  const otherAssetsTotal = useMemo(() => {
    let total = 0;
    let hasUnknown = false;
    for (const a of otherAssets) {
      const converted = toNum(a.value_converted) ?? (a.currency === currency ? toNum(a.value) : null);
      if (converted === null) {
        hasUnknown = true;
      } else {
        total += converted;
      }
    }
    return { total, hasUnknown };
  }, [otherAssets, currency]);

  const hasNetWorthExtras = loans.length > 0 || otherAssets.length > 0;
  const netWorth = totals.valueKnown + otherAssetsTotal.total - loansTotal.total;
  const netWorthHasUnknown = loansTotal.hasUnknown || otherAssetsTotal.hasUnknown;

  if (loading || (positions.length === 0 && loans.length === 0 && otherAssets.length === 0)) return null;

  return (
    <Link
      to="/patrimonio"
      className="block bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4"
    >
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
          Portfolio <span className="text-xs font-normal text-gray-400 dark:text-slate-500">({currency})</span>
        </h2>
        <span className="text-xs text-navy-600 dark:text-navy-400">Ver detalhe →</span>
      </div>

      {hasNetWorthExtras && (
        <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-100 dark:border-slate-800">
          <span className="text-xs font-medium text-gray-500 dark:text-slate-400">
            Património líquido
            {netWorthHasUnknown && '*'}
          </span>
          <span className={`text-sm font-bold ${plColorClass(netWorth)}`}>{money(netWorth, currency)}</span>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-xs text-gray-400 dark:text-slate-500">Custo</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{money(totals.costTotal, currency)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 dark:text-slate-500">Valor</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{money(totals.valueKnown, currency)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 dark:text-slate-500">P&L</p>
          <p className={`text-sm font-semibold ${plColorClass(totals.pl)}`}>
            {money(totals.pl, currency)}
            {totals.plPct !== null && ` (${totals.plPct > 0 ? '+' : ''}${totals.plPct.toFixed(1)}%)`}
          </p>
        </div>
      </div>

      {hasNetWorthExtras && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-2">
          Valor
          {otherAssets.length > 0 && ` + ${money(otherAssetsTotal.total, currency)} outros ativos`}
          {loans.length > 0 && ` − ${money(loansTotal.total, currency)} em dívida`}
          {netWorthHasUnknown && ' (* exclui valores sem câmbio conhecido ainda)'}
        </p>
      )}

      {positions.length > 0 && (
        <div className="border-t border-gray-100 dark:border-slate-800 mt-3 pt-3">
          <PortfolioAllocationChart positions={positions} />
        </div>
      )}
    </Link>
  );
}
