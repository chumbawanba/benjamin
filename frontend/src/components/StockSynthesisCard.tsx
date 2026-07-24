import { StockSynthesis, SynthesisClassification } from '../api/types';

// Mesma paleta favorável/neutro/desfavorável usada no resto da app (ver
// RecommendationBadge.tsx: BUY=verde, SELL=vermelho, HOLD=cinza) — "misto"
// é o único caso novo aqui, quando indicadores da mesma categoria discordam
// entre si (ex: RSI sobrecomprado mas preço acima da média).
const CLASSIFICATION_STYLES: Record<SynthesisClassification, string> = {
  favoravel: 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400',
  desfavoravel: 'bg-red-100 text-red-700 dark:bg-rose-500/15 dark:text-rose-400',
  neutro: 'bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-400',
  misto: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400',
};

const CLASSIFICATION_LABELS: Record<SynthesisClassification, string> = {
  favoravel: 'Favorável',
  desfavoravel: 'Desfavorável',
  neutro: 'Neutro',
  misto: 'Misto',
};

function scoreColorClass(score: number | null): string {
  if (score === null) return 'text-gray-400 dark:text-slate-500';
  if (score >= 70) return 'text-green-600 dark:text-emerald-400';
  if (score <= 30) return 'text-red-600 dark:text-rose-400';
  return 'text-gray-500 dark:text-slate-400';
}

// Resumo visual por categoria (valuation/momentum/crescimento/rendibilidade)
// — leitura rápida a partir de thresholds fixos (ver backend/synthesis.py),
// não substitui a recomendação BUY/SELL/HOLD da estratégia configurada
// (essa usa os pesos e critérios que o próprio utilizador escolheu).
export default function StockSynthesisCard({ synthesis }: { synthesis: StockSynthesis }) {
  return (
    <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-gray-700 dark:text-slate-300">Síntese</p>
        <div className="text-right">
          <p className={`text-2xl font-semibold leading-none ${scoreColorClass(synthesis.score)}`}>
            {synthesis.score === null ? '—' : Math.round(synthesis.score)}
          </p>
          <p className="text-xs text-gray-400 dark:text-slate-500">score do sinal</p>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {synthesis.categories.map((cat) => (
          <div
            key={cat.category}
            className={`flex items-center justify-between gap-2 px-3 py-2 rounded-lg ${
              cat.classification
                ? CLASSIFICATION_STYLES[cat.classification]
                : 'bg-gray-50 dark:bg-slate-800/50 text-gray-500 dark:text-slate-400'
            }`}
          >
            <div className="min-w-0">
              <p className="text-sm font-medium">{cat.label}</p>
              <p className="text-xs opacity-80 truncate">{cat.reason ?? 'Sem dados suficientes'}</p>
            </div>
            <span className="text-xs font-medium shrink-0">
              {cat.classification ? CLASSIFICATION_LABELS[cat.classification] : 'Sem dados'}
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 dark:text-slate-500 mt-3">
        Leitura simplificada a partir de thresholds fixos — não é a recomendação da estratégia (ver "Última
        avaliação" abaixo) nem aconselhamento financeiro.
      </p>
    </div>
  );
}
