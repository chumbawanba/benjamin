// Utilitários partilhados para os gráficos SVG hand-rolled (sem biblioteca
// de charts) que mostram valores monetários ao longo do tempo — usados pelo
// ProjectionChart e pelo HistoryChart (histórico de património).

// Escolhe ~4 valores "redondos" para as linhas-guia do eixo Y (mesma ideia
// de um gerador de ticks tipo d3, simplificada: arredonda o passo para
// 1/2/5 x uma potência de 10).
export function niceTicks(min: number, max: number, count = 4): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) return [min];
  const rawStep = (max - min) / count;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const residual = rawStep / magnitude;
  let niceResidual: number;
  if (residual > 5) niceResidual = 10;
  else if (residual > 2) niceResidual = 5;
  else if (residual > 1) niceResidual = 2;
  else niceResidual = 1;
  const step = niceResidual * magnitude;
  const start = Math.ceil(min / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= max + 1e-9; v += step) ticks.push(Math.round(v * 100) / 100);
  return ticks.length > 0 ? ticks : [min];
}

// Formato compacto para não ocupar espaço a mais no eixo (250000 -> "250k").
export function formatAxisValue(v: number): string {
  const sign = v < 0 ? '-' : '';
  const abs = Math.abs(v);
  if (abs >= 1_000_000) {
    const m = abs / 1_000_000;
    return `${sign}${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M`;
  }
  if (abs >= 1_000) {
    const k = abs / 1_000;
    return `${sign}${k % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}k`;
  }
  return `${sign}${abs.toFixed(0)}`;
}
