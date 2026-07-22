import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { StockDetail as StockDetailType } from '../api/types';
import PriceChange from '../components/PriceChange';
import RecommendationBadge from '../components/RecommendationBadge';
import Sparkline from '../components/Sparkline';

// Campos Decimal do backend (pydantic) chegam como string em JSON, não number
// — nunca assumir .toFixed() diretamente sem passar por Number() primeiro.
function toNum(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

function formatDecimal(value: number | string | null | undefined, digits = 2): string {
  const n = toNum(value);
  return n === null ? '—' : n.toFixed(digits);
}

function formatIndicatorValue(key: string, value: number | null): string {
  const n = toNum(value);
  if (n === null) return '—';
  if (key === 'DIVIDEND_YIELD') return `${(n * 100).toFixed(2)}%`;
  if (key === 'MARKET_CAP') return `$${n.toFixed(1)}B`;
  return n.toFixed(2);
}

// Descrições curtas para tooltip (title), mesmo padrão já usado nos
// indicadores técnicos (ver ind.description mais abaixo) — os fundamentais
// não vêm do backend com descrição porque são campos fixos, não uma lista
// configurável como os indicadores (ver INDICATORS em indicators_core.py).
const FUNDAMENTALS_DESCRIPTIONS: Record<string, string> = {
  'P/E': 'Preço da ação a dividir pelo lucro por ação (EPS). Quanto mais baixo, mais "barata" a ação parece face aos lucros atuais.',
  EPS: 'Lucro por ação — lucro líquido da empresa a dividir pelo número total de ações.',
  'Debt/Equity': 'Dívida total a dividir pelo capital próprio. Quanto mais alto, mais a empresa depende de dívida para se financiar.',
  'Dividend Yield': 'Dividendo anual a dividir pelo preço da ação, em percentagem — quanto a ação "paga" em dividendos por ano.',
};

function formatCriterionValue(criterion: { threshold_value: number | null; threshold_value_max: number | null; operator: string }): string {
  if (criterion.operator === 'between') {
    return `${formatDecimal(criterion.threshold_value)} - ${formatDecimal(criterion.threshold_value_max)}`;
  }
  return `${criterion.operator} ${formatDecimal(criterion.threshold_value)}`;
}

export default function StockDetail() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<StockDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await api.get<StockDetailType>(`/watchlist/${id}/detail`);
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Erro ao carregar detalhe');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) return <p className="text-sm text-gray-500 dark:text-slate-400">A carregar…</p>;

  if (error || !detail) {
    return (
      <p className="text-sm text-red-600 dark:text-rose-400">
        {error ?? 'Não encontrado.'}{' '}
        <Link to="/workspace" className="text-navy-600 dark:text-navy-400">
          Voltar à watchlist
        </Link>
      </p>
    );
  }

  const closes = detail.price_history.map((p) => p.close);
  const sma200 = detail.price_history.map((p) => p.sma_200);
  const hasSma200 = sma200.some((v) => v !== null && v !== undefined);

  return (
    <div>
      <Link to="/workspace" className="text-sm text-navy-600 dark:text-navy-400">
        &larr; Watchlist
      </Link>

      <div className="flex items-baseline justify-between mt-2 mb-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">{detail.stock.ticker}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400">{detail.stock.name ?? '—'}</p>
        </div>
        <div className="text-right">
          <PriceChange price={detail.last_price} changePct={detail.price_change_pct} currency={detail.stock.currency} />
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-4">
        <Sparkline
          points={closes}
          secondaryPoints={hasSma200 ? sma200 : undefined}
          secondaryLabel="SMA 200"
          height={100}
        />
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-2">
          Últimos {detail.price_history.length} dias com fecho registado.
          {!hasSma200 && ' Histórico ainda insuficiente para a SMA 200 (precisa de 200 dias).'}
        </p>
      </div>

      <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2">Indicadores</h2>
      <div className="grid grid-cols-2 gap-2 mb-6">
        {detail.indicators.map((ind) => (
          <div
            key={ind.key}
            title={ind.description ?? undefined}
            className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-3"
          >
            <p className="text-xs text-gray-500 dark:text-slate-400">{ind.key}</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-slate-100">
              {formatIndicatorValue(ind.key, ind.value)}
            </p>
          </div>
        ))}
      </div>

      {detail.fundamentals && (
        <>
          <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2">Fundamentais</h2>
          <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-6 grid grid-cols-2 gap-3 text-sm">
            <div title={FUNDAMENTALS_DESCRIPTIONS['P/E']}>
              <p className="text-xs text-gray-500 dark:text-slate-400">P/E</p>
              <p className="text-gray-900 dark:text-slate-100">{formatDecimal(detail.fundamentals.pe_ratio)}</p>
            </div>
            <div title={FUNDAMENTALS_DESCRIPTIONS.EPS}>
              <p className="text-xs text-gray-500 dark:text-slate-400">EPS</p>
              <p className="text-gray-900 dark:text-slate-100">{formatDecimal(detail.fundamentals.eps)}</p>
            </div>
            <div title={FUNDAMENTALS_DESCRIPTIONS['Debt/Equity']}>
              <p className="text-xs text-gray-500 dark:text-slate-400">Debt/Equity</p>
              <p className="text-gray-900 dark:text-slate-100">{formatDecimal(detail.fundamentals.debt_to_equity)}</p>
            </div>
            <div title={FUNDAMENTALS_DESCRIPTIONS['Dividend Yield']}>
              <p className="text-xs text-gray-500 dark:text-slate-400">Dividend Yield</p>
              <p className="text-gray-900 dark:text-slate-100">
                {(() => {
                  const y = toNum(detail.fundamentals!.dividend_yield);
                  return y === null ? '—' : `${(y * 100).toFixed(2)}%`;
                })()}
              </p>
            </div>
          </div>
        </>
      )}

      <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2">Última avaliação</h2>
      {detail.latest_evaluation ? (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{detail.strategy_name ?? 'Estratégia'}</p>
            </div>
            <RecommendationBadge recommendation={detail.latest_evaluation.recommendation} />
          </div>
          <ul className="space-y-2">
            {detail.criteria.map((c, idx) => (
              <li key={idx} className="flex items-center justify-between text-sm border-t border-gray-100 dark:border-slate-800 pt-2 first:border-0 first:pt-0">
                <div className="min-w-0">
                  <p className="text-gray-900 dark:text-slate-100">{c.name}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {c.metric} {formatCriterionValue(c)} · observado {formatDecimal(c.observed_value)} · peso {formatDecimal(c.weight, 0)}
                  </p>
                </div>
                <span
                  className={
                    c.passed
                      ? 'text-xs font-semibold text-green-600 dark:text-emerald-400 shrink-0'
                      : 'text-xs font-semibold text-gray-400 dark:text-slate-500 shrink-0'
                  }
                >
                  {c.passed ? '✓ passou' : '— falhou'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">
          Ainda sem avaliação.{' '}
          <Link to="/workspace?tab=avaliacoes" className="text-navy-600 dark:text-navy-400">
            Corre uma estratégia em Avaliações
          </Link>
          .
        </p>
      )}
    </div>
  );
}
