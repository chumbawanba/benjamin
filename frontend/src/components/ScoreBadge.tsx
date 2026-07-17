interface Props {
  kind: 'buy' | 'sell';
  score: number;
}

// Cores por regra do SPEC.md secção 9: verde >=70, cinzento 40-69, vermelho para sell >=70.
export default function ScoreBadge({ kind, score }: Props) {
  const rounded = Math.round(score);
  let classes = 'bg-gray-100 text-gray-400 dark:bg-slate-800 dark:text-slate-500';
  if (kind === 'sell' && score >= 70) {
    classes = 'bg-red-100 text-red-700 dark:bg-rose-500/15 dark:text-rose-400';
  } else if (score >= 70) {
    classes = 'bg-green-100 text-green-700 dark:bg-emerald-500/15 dark:text-emerald-400';
  } else if (score >= 40) {
    classes = 'bg-gray-200 text-gray-700 dark:bg-slate-700 dark:text-slate-300';
  }

  const label = kind === 'buy' ? 'Buy' : 'Sell';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${classes}`}>
      {label} {rounded}
    </span>
  );
}
