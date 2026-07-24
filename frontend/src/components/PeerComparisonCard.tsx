import { Fundamentals, PeerComparison } from '../api/types';

function toNum(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

function fmtRatio(value: number | string | null | undefined): string {
  const n = toNum(value);
  return n === null ? '—' : n.toFixed(1);
}

function fmtPercent(value: number | string | null | undefined): string {
  const n = toNum(value);
  return n === null ? '—' : `${n.toFixed(1)}%`;
}

interface CompanyCardProps {
  ticker: string;
  name: string | null;
  peRatio: number | string | null;
  roe: number | string | null;
  netMargin: number | string | null;
  highlighted?: boolean;
}

function CompanyCard({ ticker, name, peRatio, roe, netMargin, highlighted }: CompanyCardProps) {
  return (
    <div
      className={`shrink-0 w-36 rounded-lg p-3 ${
        highlighted
          ? 'bg-navy-50 dark:bg-navy-500/15 border-2 border-navy-300 dark:border-navy-500/40'
          : 'bg-gray-50 dark:bg-slate-800/50 border border-gray-100 dark:border-slate-800'
      }`}
    >
      <p className="text-sm font-semibold text-gray-900 dark:text-slate-100 truncate">{ticker}</p>
      <p className="text-xs text-gray-500 dark:text-slate-400 truncate mb-2">{name ?? '—'}</p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-400 dark:text-slate-500">PE</span>
          <span className="text-gray-900 dark:text-slate-100">{fmtRatio(peRatio)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400 dark:text-slate-500">ROE</span>
          <span className="text-gray-900 dark:text-slate-100">{fmtPercent(roe)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400 dark:text-slate-500">Margem líq.</span>
          <span className="text-gray-900 dark:text-slate-100">{fmtPercent(netMargin)}</span>
        </div>
      </div>
    </div>
  );
}

// Comparação rápida com "peers" (mesma indústria, via Finnhub /stock/peers,
// só os que já têm fundamentais na nossa BD - ver watchlist.py::
// watchlist_item_detail) - scroll horizontal em vez de tabela, mais amigável
// em mobile com poucas colunas cabendo no ecrã.
export default function PeerComparisonCard({
  ticker,
  name,
  fundamentals,
  peers,
}: {
  ticker: string;
  name: string | null;
  fundamentals: Fundamentals | null;
  peers: PeerComparison[];
}) {
  if (peers.length === 0) return null;

  return (
    <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
      <p className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3">Comparação com peers</p>
      <div className="flex gap-2 overflow-x-auto pb-1">
        <CompanyCard
          ticker={ticker}
          name={name}
          peRatio={fundamentals?.pe_ratio ?? null}
          roe={fundamentals?.roe ?? null}
          netMargin={fundamentals?.net_margin ?? null}
          highlighted
        />
        {peers.map((p) => (
          <CompanyCard key={p.ticker} ticker={p.ticker} name={p.name} peRatio={p.pe_ratio} roe={p.roe} netMargin={p.net_margin} />
        ))}
      </div>
      <p className="text-xs text-gray-400 dark:text-slate-500 mt-2">
        Ações da mesma indústria que já têm fundamentais na base de dados do Benjamin.
      </p>
    </div>
  );
}
