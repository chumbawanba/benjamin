import { ProjectionPoint } from '../api/types';

interface Props {
  points: ProjectionPoint[];
  width?: number;
  height?: number;
}

function toNum(v: number | string): number {
  const n = Number(v);
  return Number.isNaN(n) ? 0 : n;
}

// Gráfico simples de 3 linhas (portfolio a crescer, dívida a descer,
// património líquido) ao longo dos anos da projeção - mesmo estilo
// hand-rolled SVG sem dependências do BacktestChart.tsx/Sparkline.tsx.
export default function ProjectionChart({ points, width = 600, height = 200 }: Props) {
  if (points.length < 2) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-400 dark:text-slate-500" style={{ width: '100%', height }}>
        Sem dados suficientes para gráfico.
      </div>
    );
  }

  const portfolio = points.map((p) => toNum(p.portfolio_value));
  const loans = points.map((p) => toNum(p.loans_balance));
  const netWorth = points.map((p) => toNum(p.net_worth));
  const all = [...portfolio, ...loans, ...netWorth];
  const min = Math.min(0, ...all);
  const max = Math.max(...all, 1);
  const range = max - min || 1;
  const stepX = width / (points.length - 1);
  const y = (v: number) => height - ((v - min) / range) * height;

  const line = (values: number[]) => values.map((v, i) => `${i * stepX},${y(v)}`).join(' ');

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
        {min < 0 && max > 0 && (
          <line x1={0} y1={y(0)} x2={width} y2={y(0)} strokeWidth={1} className="stroke-gray-200 dark:stroke-slate-700" />
        )}
        <polyline points={line(portfolio)} fill="none" strokeWidth={1.5} className="stroke-navy-400 dark:stroke-navy-500" strokeDasharray="4 3" />
        <polyline points={line(loans)} fill="none" strokeWidth={1.5} className="stroke-red-400 dark:stroke-rose-500" strokeDasharray="4 3" />
        <polyline points={line(netWorth)} fill="none" strokeWidth={2.5} className="stroke-navy-600 dark:stroke-navy-400" />
      </svg>
      <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400 dark:text-slate-500">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-navy-600 dark:bg-navy-400" />
          Património líquido
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-navy-400 dark:bg-navy-500" style={{ opacity: 0.7 }} />
          Portfolio
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-0.5 bg-red-400 dark:bg-rose-500" style={{ opacity: 0.7 }} />
          Dívida
        </span>
      </div>
    </div>
  );
}
