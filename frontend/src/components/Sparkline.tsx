interface Props {
  points: (number | null)[];
  secondaryPoints?: (number | null)[];
  secondaryLabel?: string;
  width?: number;
  height?: number;
  className?: string;
}

// Mini-gráfico de linha, sem dependências externas — só o suficiente para dar
// uma noção de tendência do histórico de preço na página de detalhe da ação.
// secondaryPoints (opcional) desenha uma segunda linha tracejada na mesma
// escala — usado para a SMA_200.
export default function Sparkline({
  points, secondaryPoints, secondaryLabel, width = 600, height = 120, className,
}: Props) {
  const valid = points.filter((p): p is number => p !== null && p !== undefined);
  if (valid.length < 2) {
    return (
      <div
        className={`flex items-center justify-center text-xs text-gray-400 dark:text-slate-500 ${className ?? ''}`}
        style={{ width: '100%', height }}
      >
        Histórico insuficiente para gráfico.
      </div>
    );
  }
  const secondaryValid = (secondaryPoints ?? []).filter((p): p is number => p !== null && p !== undefined);
  const allValues = secondaryValid.length > 0 ? [...valid, ...secondaryValid] : valid;
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min || 1;
  const stepX = width / (points.length - 1);
  const toCoords = (series: (number | null)[]) =>
    series
      .map((p, i) => (p === null || p === undefined ? null : `${i * stepX},${height - ((p - min) / range) * height}`))
      .filter((c): c is string => c !== null)
      .join(' ');
  const coords = toCoords(points);
  const secondaryCoords = secondaryValid.length > 0 && secondaryPoints ? toCoords(secondaryPoints) : null;
  const isUp = valid[valid.length - 1] >= valid[0];
  const strokeClass = isUp ? 'stroke-green-500 dark:stroke-emerald-400' : 'stroke-red-500 dark:stroke-rose-400';

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className={className} preserveAspectRatio="none" style={{ width: '100%', height }}>
        {secondaryCoords && (
          <polyline
            points={secondaryCoords}
            fill="none"
            strokeWidth={1.5}
            strokeDasharray="5 4"
            className="stroke-amber-500 dark:stroke-amber-400"
          />
        )}
        <polyline points={coords} fill="none" strokeWidth={2} className={strokeClass} />
      </svg>
      {secondaryCoords && secondaryLabel && (
        <div className="flex items-center gap-1.5 mt-1.5 text-xs text-gray-400 dark:text-slate-500">
          <span className="inline-block w-3 h-0 border-t-2 border-dashed border-amber-500 dark:border-amber-400" />
          {secondaryLabel}
        </div>
      )}
    </div>
  );
}
