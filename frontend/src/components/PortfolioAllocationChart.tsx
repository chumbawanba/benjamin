import { Position } from '../api/types';

interface Props {
  positions: Position[];
}

function toNum(v: number | string | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

// Valor de cada posição para pesar a fatia no gráfico: preferimos o valor de
// mercado (convertido para a moeda preferida quando aplicável), e só caímos
// para o custo quando ainda não há preço/câmbio conhecido - assim uma posição
// sem cotação ainda aparece no gráfico em vez de ser omitida em silêncio.
function positionValue(p: Position): number | null {
  return (
    toNum(p.market_value_converted) ??
    toNum(p.market_value) ??
    toNum(p.cost_total_converted) ??
    toNum(p.cost_total)
  );
}

// Uma cor (hue HSL) por setor/mercado - ciclo de 10 tons bem distintos entre
// si. Dentro de cada setor, cada ação usa o mesmo hue com luminosidade
// diferente, para ficar visualmente associada ao seu setor no anel exterior.
const SECTOR_HUES = [210, 25, 145, 280, 350, 45, 175, 255, 320, 95];

function sectorColor(hue: number): string {
  return `hsl(${hue} 60% 45%)`;
}

function stockColor(hue: number, indexInSector: number): string {
  const lightness = Math.min(45 + indexInSector * 14, 78);
  return `hsl(${hue} 60% ${lightness}%)`;
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

// Fatia de anel (donut) entre startAngle e endAngle (graus, 0 = topo, sentido
// horário) - usado tanto para o anel interior (setor) como o exterior (ação).
// O clamp evita o caso degenerado de uma fatia a cobrir os 360 graus inteiros
// (ponto inicial == ponto final faria o arco desaparecer).
function ringSlicePath(cx: number, cy: number, rOuter: number, rInner: number, startAngle: number, endAngle: number): string {
  const clampedEnd = endAngle - startAngle >= 360 ? startAngle + 359.99 : endAngle;
  const largeArc = clampedEnd - startAngle > 180 ? 1 : 0;
  const p1 = polarToCartesian(cx, cy, rOuter, startAngle);
  const p2 = polarToCartesian(cx, cy, rOuter, clampedEnd);
  const p3 = polarToCartesian(cx, cy, rInner, clampedEnd);
  const p4 = polarToCartesian(cx, cy, rInner, startAngle);
  return `M ${p1.x} ${p1.y} A ${rOuter} ${rOuter} 0 ${largeArc} 1 ${p2.x} ${p2.y} L ${p3.x} ${p3.y} A ${rInner} ${rInner} 0 ${largeArc} 0 ${p4.x} ${p4.y} Z`;
}

// Gráfico de distribuição do portfolio em dois anéis concêntricos: o anel
// interior agrupa por setor/mercado (ex: 65% Tecnológico), o exterior mostra
// cada ação individual (ex: 63% MSFT) - dentro do mesmo setor no anel
// exterior para ser imediatamente visível que uma ação concentrada também
// concentra o setor. Feito à mão em SVG (sem biblioteca de gráficos), no
// mesmo espírito do Sparkline.tsx.
export default function PortfolioAllocationChart({ positions }: Props) {
  const withValue = positions
    .map((p) => ({ p, value: positionValue(p) }))
    .filter((x): x is { p: Position; value: number } => x.value !== null && x.value > 0);

  const total = withValue.reduce((sum, x) => sum + x.value, 0);
  if (total <= 0) {
    return (
      <p className="text-sm text-gray-400 dark:text-slate-500">
        Ainda sem valores de mercado conhecidos para desenhar a distribuição.
      </p>
    );
  }

  const bySector = new Map<string, { label: string; total: number; items: { ticker: string; value: number }[] }>();
  for (const { p, value } of withValue) {
    const label = p.stock.sector?.trim() || 'Outro / desconhecido';
    const entry = bySector.get(label) ?? { label, total: 0, items: [] };
    entry.total += value;
    entry.items.push({ ticker: p.stock.ticker, value });
    bySector.set(label, entry);
  }
  const sectors = Array.from(bySector.values()).sort((a, b) => b.total - a.total);

  let angle = 0;
  const sectorSlices: { label: string; pct: number; color: string; start: number; end: number }[] = [];
  const stockSlices: { ticker: string; pct: number; color: string; start: number; end: number }[] = [];
  sectors.forEach((sector, sIdx) => {
    const hue = SECTOR_HUES[sIdx % SECTOR_HUES.length];
    const sectorStart = angle;
    const items = [...sector.items].sort((a, b) => b.value - a.value);
    items.forEach((item, iIdx) => {
      const span = (item.value / total) * 360;
      stockSlices.push({
        ticker: item.ticker,
        pct: (item.value / total) * 100,
        color: stockColor(hue, iIdx),
        start: angle,
        end: angle + span,
      });
      angle += span;
    });
    sectorSlices.push({
      label: sector.label,
      pct: (sector.total / total) * 100,
      color: sectorColor(hue),
      start: sectorStart,
      end: angle,
    });
  });

  const cx = 100;
  const cy = 100;

  return (
    <div className="flex flex-col sm:flex-row items-center gap-4">
      <svg viewBox="0 0 200 200" className="w-44 h-44 shrink-0">
        {sectorSlices.map((s) => (
          <path key={`sector-${s.label}`} d={ringSlicePath(cx, cy, 62, 35, s.start, s.end)} fill={s.color}>
            <title>{`${s.label}: ${s.pct.toFixed(1)}%`}</title>
          </path>
        ))}
        {stockSlices.map((s) => (
          <path key={`stock-${s.ticker}`} d={ringSlicePath(cx, cy, 95, 65, s.start, s.end)} fill={s.color}>
            <title>{`${s.ticker}: ${s.pct.toFixed(1)}%`}</title>
          </path>
        ))}
      </svg>

      <div className="flex-1 w-full grid grid-cols-2 gap-4 text-xs">
        <div>
          <p className="font-medium text-gray-500 dark:text-slate-400 mb-1">Por ação</p>
          <ul className="space-y-1">
            {stockSlices
              .slice()
              .sort((a, b) => b.pct - a.pct)
              .map((s) => (
                <li key={s.ticker} className="flex items-center gap-1.5">
                  <span className="inline-block w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: s.color }} />
                  <span className="text-gray-700 dark:text-slate-300 truncate">{s.ticker}</span>
                  <span className="text-gray-400 dark:text-slate-500 ml-auto shrink-0">{s.pct.toFixed(1)}%</span>
                </li>
              ))}
          </ul>
        </div>
        <div>
          <p className="font-medium text-gray-500 dark:text-slate-400 mb-1">Por mercado</p>
          <ul className="space-y-1">
            {sectorSlices.map((s) => (
              <li key={s.label} className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: s.color }} />
                <span className="text-gray-700 dark:text-slate-300 truncate">{s.label}</span>
                <span className="text-gray-400 dark:text-slate-500 ml-auto shrink-0">{s.pct.toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
