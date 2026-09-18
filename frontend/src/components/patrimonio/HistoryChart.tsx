import { PatrimonySnapshot } from '../../api/types';
import { formatAxisValue, niceTicks } from '../../utils/chart';

interface Props {
  snapshots: PatrimonySnapshot[]; // já ordenados por data ascendente
  width?: number;
  height?: number;
}

function toNum(v: number | string): number {
  const n = Number(v);
  return Number.isNaN(n) ? 0 : n;
}

function formatDateShort(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

// Gráfico do histórico real de património (pedido do Edgar: "manter um
// histórico do meu património" - separadamente da Projeção, que é uma
// extrapolação). Ao contrário do ProjectionChart (pontos equidistantes por
// ano), aqui as datas são escolhidas livremente pelo utilizador, por isso o
// eixo X é escalado pela data real, não pelo índice do ponto. Mostra só o
// património líquido (o breakdown completo - stocks/cash/outros/dívida -
// fica visível na tabela ao lado, não no gráfico, para não sobrecarregar).
// Pontos com nota (ex: "Compra de casa") ganham um marcador maior, mesmo
// estilo visual do mockup da landing page.
export default function HistoryChart({ snapshots, width = 600, height = 200 }: Props) {
  if (snapshots.length < 2) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-400 dark:text-slate-500 text-center px-4" style={{ width: '100%', height }}>
        Adiciona pelo menos duas datas para veres a evolução do teu património.
      </div>
    );
  }

  const netWorths = snapshots.map((s) => toNum(s.net_worth));
  const min = Math.min(0, ...netWorths);
  const max = Math.max(...netWorths, 1);
  const range = max - min || 1;

  const axisWidth = 46;
  const plotWidth = Math.max(width - axisWidth, 1);
  const times = snapshots.map((s) => new Date(s.date).getTime());
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const timeRange = maxTime - minTime || 1;

  const y = (v: number) => height - ((v - min) / range) * height;
  const x = (t: number) => axisWidth + ((t - minTime) / timeRange) * plotWidth;

  const ticks = niceTicks(min, max);
  const linePoints = snapshots.map((s, i) => `${x(times[i])},${y(netWorths[i])}`).join(' ');
  const areaPoints = `${axisWidth},${height} ${linePoints} ${width},${height}`;

  const noted = snapshots.filter((s) => !!s.note?.trim());

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
        <defs>
          <linearGradient id="historyChartFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2f4a7c" stopOpacity={0.16} />
            <stop offset="100%" stopColor="#2f4a7c" stopOpacity={0} />
          </linearGradient>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={axisWidth} y1={y(t)} x2={width} y2={y(t)} strokeWidth={1} className="stroke-gray-100 dark:stroke-slate-800" />
            <text x={axisWidth - 6} y={y(t)} dy="0.32em" textAnchor="end" className="fill-gray-400 dark:fill-slate-500" style={{ fontSize: 9 }}>
              {formatAxisValue(t)}
            </text>
          </g>
        ))}
        {min < 0 && max > 0 && (
          <line x1={axisWidth} y1={y(0)} x2={width} y2={y(0)} strokeWidth={1} className="stroke-gray-200 dark:stroke-slate-700" />
        )}
        <polygon points={areaPoints} fill="url(#historyChartFill)" />
        <polyline points={linePoints} fill="none" strokeWidth={2.5} className="stroke-navy-600 dark:stroke-navy-400" />
        {snapshots.map((s, i) => {
          const hasNote = !!s.note?.trim();
          return (
            <circle
              key={s.id}
              cx={x(times[i])}
              cy={y(netWorths[i])}
              r={hasNote ? 5 : 3}
              className={hasNote ? 'fill-white stroke-navy-600 dark:fill-slate-900 dark:stroke-navy-400' : 'fill-navy-600 dark:fill-navy-400'}
              strokeWidth={hasNote ? 2.5 : 0}
            />
          );
        })}
      </svg>
      <div className="flex items-center justify-between text-xs text-gray-400 dark:text-slate-500 mt-0.5" style={{ paddingLeft: axisWidth }}>
        <span>{formatDateShort(snapshots[0].date)}</span>
        <span>{formatDateShort(snapshots[snapshots.length - 1].date)}</span>
      </div>

      {noted.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-800 space-y-1.5">
          {noted.map((s) => (
            <div key={s.id} className="flex items-start gap-2 text-xs">
              <span className="w-4 h-4 rounded-full border-2 border-navy-600 dark:border-navy-400 shrink-0 mt-0.5" />
              <span>
                <span className="font-medium text-gray-700 dark:text-slate-300">{formatDateShort(s.date)}</span>{' '}
                <span className="text-gray-500 dark:text-slate-400">{s.note}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
