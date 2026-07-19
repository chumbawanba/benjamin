import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Position } from '../api/types';

function toNum(v: number | string | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

function money(v: number | null): string {
  if (v === null) return '—';
  return v.toFixed(2);
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Position[]>('/portfolio')
      .then(setPositions)
      .catch(() => setPositions([]))
      .finally(() => setLoading(false));
  }, []);

  const totals = useMemo(() => {
    let costTotal = 0;
    let valueKnown = 0;
    let costOfKnown = 0;
    for (const p of positions) {
      costTotal += toNum(p.cost_total) ?? 0;
      const mv = toNum(p.market_value);
      if (mv !== null) {
        valueKnown += mv;
        costOfKnown += toNum(p.cost_total) ?? 0;
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
        <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300">Portfolio</h2>
        <span className="text-xs text-petrol-600 dark:text-petrol-400">Ver detalhe →</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-xs text-gray-400 dark:text-slate-500">Custo</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{money(totals.costTotal)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 dark:text-slate-500">Valor</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{money(totals.valueKnown)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 dark:text-slate-500">P&L</p>
          <p className={`text-sm font-semibold ${plColorClass(totals.pl)}`}>
            {money(totals.pl)}
            {totals.plPct !== null && ` (${totals.plPct > 0 ? '+' : ''}${totals.plPct.toFixed(1)}%)`}
          </p>
        </div>
      </div>
    </Link>
  );
}
