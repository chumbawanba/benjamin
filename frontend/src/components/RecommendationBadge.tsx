interface Props {
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  // Score do lado relevante (buy_score se BUY, sell_score se SELL) - Decimal
  // no backend, por isso pode chegar como string em JSON (ver PriceChange.tsx).
  // Omitido/HOLD -> não mostra número, só o texto (ver comentário abaixo).
  buyScore?: number | string | null;
  sellScore?: number | string | null;
}

function toNum(v: number | string | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

// Explicação do que cada recomendação significa e como é calculada — cada
// critério da estratégia contribui com o seu peso para um score de compra e
// um score de venda (0-100%); se o score de venda atingir 70% é SELL (a
// venda é verificada primeiro), senão se o score de compra atingir 70% é
// BUY, senão é HOLD. HOLD não é "seguro" nem uma recomendação em si — é só
// o resultado de nenhum dos dois lados ter chegado ao limiar com os
// pesos/critérios configurados nesta estratégia (ver StrategyEditor para o
// que cada critério e peso individual significam).
const EXPLANATIONS: Record<Props['recommendation'], string> = {
  BUY: 'Compra: a pontuação ponderada dos critérios de compra desta estratégia atingiu o limiar de 70%.',
  SELL: 'Venda: a pontuação ponderada dos critérios de venda desta estratégia atingiu o limiar de 70% (a venda é verificada antes da compra).',
  HOLD: 'Manter: nem os critérios de compra nem os de venda atingiram o limiar de 70% — não é um sinal de segurança, só significa que nenhum lado disparou com os pesos e limiares configurados nesta estratégia.',
};

// Badge com a recomendação final + o score do lado que disparou o sinal (ex:
// "BUY 92%") — substituiu um "ScoreBadge" antigo que mostrava sempre os dois
// lados (Buy X% / Sell Y%), redundante quando só um era relevante. Para HOLD
// não mostramos número: nenhum dos dois lados "venceu", o score por si só não
// é acionável (ver pedido do utilizador: score só faz sentido com BUY/SELL).
export default function RecommendationBadge({ recommendation, buyScore, sellScore }: Props) {
  const classes =
    recommendation === 'BUY'
      ? 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400'
      : recommendation === 'SELL'
      ? 'bg-red-100 text-red-700 dark:bg-rose-500/15 dark:text-rose-400'
      : 'bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-400';

  const score = recommendation === 'BUY' ? toNum(buyScore) : recommendation === 'SELL' ? toNum(sellScore) : null;

  return (
    <span
      title={EXPLANATIONS[recommendation]}
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold cursor-help ${classes}`}
    >
      {recommendation}
      {score !== null && <span className="ml-1 font-normal opacity-80">{score.toFixed(0)}%</span>}
    </span>
  );
}
