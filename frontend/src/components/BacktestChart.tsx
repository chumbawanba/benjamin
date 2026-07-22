import { BacktestPoint, BacktestTrade } from '../api/types';

interface Props {
  points: BacktestPoint[];
  trades: BacktestTrade[];
  width?: number;
  height?: number;
}

// Gráfico de preço com marcadores de compra/venda, no mesmo estilo hand-rolled
// SVG do Sparkline.tsx — mostra o que a simulação (backtest_core.simulate)
// teria feito com os critérios atualmente guardados da estratégia.
export default function BacktestChart({ points, trades, width = 600, height = 160 }: Props) {
  if (points.length < 2) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-400 dark:text-slate-500" style={{ width: '100%', height }}>
        Histórico insuficiente para gráfico.
      </div>
    );
  }

  const closes = points.map((p) => p.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const stepX = width / (points.length - 1);
  const y = (close: number) => height - ((close - min) / range) * height;
  const coords = points.map((p, i) => `${i * stepX},${y(p.close)}`).join(' ');

  const indexByDate = new Map(points.map((p, i) => [p.date, i]));
  const markers = trades
    .map((t) => {
      const idx = t.date ? indexByDate.get(t.date) : undefined;
      if (idx === undefined) return null;
      return { ...t, x: idx * stepX, y: y(t.price) };
    })
    .filter((m): m is NonNullable<typeof m> => m !== null);

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
        <polyline points={coords} fill="none" strokeWidth={1.5} className="stroke-gray-400 dark:stroke-slate-500" />
        {markers.map((m, i) => (
          <circle
            key={i}
            cx={m.x}
            cy={m.y}
            r={4}
            className={m.action === 'BUY' ? 'fill-green-500 dark:fill-emerald-400' : 'fill-red-500 dark:fill-rose-400'}
          >
            <title>{`${m.action === 'BUY' ? 'Compra' : 'Venda'} a ${m.price.toFixed(2)}${m.date ? ` em ${m.date}` : ''}`}</title>
          </circle>
        ))}
      </svg>
      <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400 dark:text-slate-500">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-green-500 dark:bg-emerald-400" />
          Compra
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500 dark:bg-rose-400" />
          Venda
        </span>
      </div>
    </div>
  );
}
