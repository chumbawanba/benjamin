import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, api } from '../api/client';
import { StockDetail as StockDetailType } from '../api/types';
import PriceChange from '../components/PriceChange';
import RecommendationBadge from '../components/RecommendationBadge';
import Sparkline from '../components/Sparkline';
import { formatRelativeTime } from '../utils/format';

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

// Indicadores fundamentais que já vêm em percentagem direta do backend (ver
// indicators_core.py) — sem o "%" ficava ambíguo (ex: "15.20" podia ler-se
// como um rácio absoluto em vez de 15.20%).
const PERCENT_INDICATOR_KEYS = new Set([
  'ROE', 'NET_MARGIN', 'REVENUE_GROWTH', 'GROSS_MARGIN', 'OPERATING_MARGIN', 'EPS_GROWTH', 'DIVIDEND_GROWTH_5Y',
]);

function formatIndicatorValue(key: string, value: number | null): string {
  const n = toNum(value);
  if (n === null) return '—';
  if (key === 'DIVIDEND_YIELD') return `${(n * 100).toFixed(2)}%`;
  if (key === 'MARKET_CAP') return `$${n.toFixed(1)}B`;
  if (PERCENT_INDICATOR_KEYS.has(key)) return `${n.toFixed(2)}%`;
  return n.toFixed(2);
}

// Rácio corrente não está na lista de indicadores configuráveis
// (INDICATORS em indicators_core.py não o inclui - não é avaliável em
// critérios de estratégia), por isso não aparece na grelha "Indicadores"
// como os restantes fundamentais (P/E, EPS, ROE, etc. - esses vêm todos de
// lá, evitando mostrar os mesmos números duas vezes na página).
const CURRENT_RATIO_DESCRIPTION =
  'Ativo circulante a dividir pelo passivo circulante. Acima de 1 sugere que a empresa consegue cobrir as dívidas de curto prazo.';

function formatCriterionValue(criterion: { threshold_value: number | null; threshold_value_max: number | null; operator: string }): string {
  if (criterion.operator === 'between') {
    return `${formatDecimal(criterion.threshold_value)} - ${formatDecimal(criterion.threshold_value_max)}`;
  }
  return `${criterion.operator} ${formatDecimal(criterion.threshold_value)}`;
}

// Frase curta derivada dos dados que já temos (sem chamada extra a nenhuma
// API) - ajuda a confirmar que a ação/ETF adicionado é mesmo o pretendido,
// sobretudo depois de escolher entre várias listagens parecidas na pesquisa.
function describeStock(stock: StockDetailType['stock']): string {
  const kind = stock.asset_type === 'etf' ? 'ETF' : 'Ação';
  const parts = [kind];
  if (stock.sector) parts.push(`do setor ${stock.sector}`);
  if (stock.exchange) parts.push(`cotada em ${stock.exchange}`);
  if (stock.currency) parts.push(`(${stock.currency})`);
  return parts.join(' ');
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
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100">{detail.stock.ticker}</h1>
            {detail.stock.asset_type === 'etf' && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-navy-50 text-navy-700 dark:bg-navy-500/15 dark:text-navy-400">
                ETF
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-slate-400">{detail.stock.name ?? '—'}</p>
        </div>
        <div className="text-right">
          <PriceChange price={detail.last_price} changePct={detail.price_change_pct} currency={detail.stock.currency} />
          {formatRelativeTime(detail.stock.last_quote_at) && (
            <p className="text-xs text-gray-400 dark:text-slate-500">
              Atualizado {formatRelativeTime(detail.stock.last_quote_at)}
            </p>
          )}
        </div>
      </div>

      <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">{describeStock(detail.stock)}</p>

      {detail.price_history.length === 0 && (
        <div className="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 rounded-xl p-4 mb-4 text-sm text-amber-800 dark:text-amber-300">
          Não há histórico de preços disponível para {detail.stock.ticker} nos fornecedores de dados que o Benjamin
          usa — por isso os indicadores abaixo aparecem vazios. É comum acontecer quando o ticker corresponde a uma
          listagem regional menos líquida (ex: uma entre várias listagens do mesmo ETF em bolsas diferentes na
          Europa). Experimenta remover esta ação e procurar de novo, escolhendo outra bolsa na lista de resultados.
        </div>
      )}

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
        {detail.fundamentals && (
          <div
            title={CURRENT_RATIO_DESCRIPTION}
            className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-3"
          >
            <p className="text-xs text-gray-500 dark:text-slate-400">RÁCIO CORRENTE</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-slate-100">
              {formatDecimal(detail.fundamentals.current_ratio)}
            </p>
          </div>
        )}
      </div>

      {!detail.fundamentals && detail.stock.asset_type === 'etf' && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mb-6">
          Fundamentais de empresa (P/E, ROE, margens…) não se aplicam a ETFs — só os indicadores de preço acima
          (RSI, médias móveis) são avaliáveis em critérios de estratégia para este tipo de ativo.
        </p>
      )}

      <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2">Última avaliação</h2>
      {detail.latest_evaluation ? (
        <div className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{detail.strategy_name ?? 'Estratégia'}</p>
            </div>
            <RecommendationBadge
              recommendation={detail.latest_evaluation.recommendation}
              buyScore={detail.latest_evaluation.buy_score}
              sellScore={detail.latest_evaluation.sell_score}
            />
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
