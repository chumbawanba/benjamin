interface Props {
  recommendation: 'BUY' | 'SELL' | 'HOLD';
}

// Badge único com a recomendação final — substitui o par Buy X% / Sell Y%
// (ScoreBadge), que mostrava sempre os dois lados mesmo quando só um deles
// era relevante (ex: "Buy 100 / Sell 0" numa recomendação já claramente de
// compra). Os scores continuam disponíveis nos critérios detalhados da
// avaliação (StockDetail/Feed), só deixam de aparecer duplicados aqui.
export default function RecommendationBadge({ recommendation }: Props) {
  const classes =
    recommendation === 'BUY'
      ? 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400'
      : recommendation === 'SELL'
      ? 'bg-red-100 text-red-700 dark:bg-rose-500/15 dark:text-rose-400'
      : 'bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-slate-400';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${classes}`}>
      {recommendation}
    </span>
  );
}
