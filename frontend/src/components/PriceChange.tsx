interface Props {
  price: number | string | null;
  changePct: number | string | null;
  currency?: string | null;
}

// Preço + variação diária colorida (verde/vermelho), estilo comum a
// investing.com/Yahoo Finance/Robinhood — o Overview/Watchlist só mostravam
// o preço absoluto antes, sem noção de direção do movimento do dia.
//
// O backend devolve estes campos como Decimal, que o pydantic serializa em
// JSON como string (para não perder precisão) — não como number. Por isso
// convertemos explicitamente aqui antes de qualquer .toFixed()/comparação.
export default function PriceChange({ price, changePct, currency }: Props) {
  const priceNum = price === null || price === undefined ? null : Number(price);
  const changePctNum = changePct === null || changePct === undefined ? null : Number(changePct);

  if (priceNum === null || Number.isNaN(priceNum)) {
    return <span className="text-gray-400 dark:text-slate-500">—</span>;
  }
  const changePctValid = changePctNum !== null && !Number.isNaN(changePctNum) ? changePctNum : null;
  const sign = changePctValid !== null && changePctValid > 0 ? '+' : '';
  const colorClass =
    changePctValid === null
      ? 'text-gray-400 dark:text-slate-500'
      : changePctValid > 0
      ? 'text-green-600 dark:text-emerald-400'
      : changePctValid < 0
      ? 'text-red-600 dark:text-rose-400'
      : 'text-gray-400 dark:text-slate-500';

  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-gray-900 dark:text-slate-100">
        {priceNum} {currency ?? ''}
      </span>
      {changePctValid !== null && (
        <span className={`text-xs font-medium ${colorClass}`}>
          {sign}
          {changePctValid.toFixed(2)}%
        </span>
      )}
    </span>
  );
}
