import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { PortfolioCurrency, Position } from '../api/types';
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

// Resumo compacto do portfolio (custo/valor/P&L) no topo do Overview, com
// link para a página Portfolio para o detalhe por posição. Não aparece se o
// utilizador ainda não registou nenhuma posição — evita ruído para quem só
// usa a watchlist/estratégias sem acompanhar posições reais.
export default function PortfolioSummaryCard() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [currency, setCurrency] = useState<string>('EUR');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get<Position[]>('/portfolio'), api.get<PortfolioCurrency>('/portfolio/currency')])
      .then(([data, curr]) => {
        setPositions(data);
        setCurrency(curr.currency);
      })
      .catch(() => setPositions([]))
      .finally(() => setLoading(false));
  }, []);

  // Mesma lógica de conversão da página Portfolio (ver Portfolio.tsx) - usa o
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

  if (loading || positions.length === 0) return null;

  return (
    <Link
      to="/portfolio"
      className="block bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4"
    >
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
          Portfolio <span className="text-xs font-normal text-gray-400 dark:text-slate-500">({currency})</span>
        </h2>
        <span className="text-xs text-navy-600 dark:text-navy-400">Ver detalhe →</span>
      </div>
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

      <div className="border-t border-gray-100 dark:border-slate-800 mt-3 pt-3">
        <PortfolioAllocationChart positions={positions} />
      </div>
    </Link>
  );
}
