import { useSearchParams } from 'react-router-dom';
import Feed from './Feed';
import Strategies from './Strategies';
import Watchlist from './Watchlist';

type SubTab = 'watchlist' | 'estrategias' | 'avaliacoes';

const TABS: [SubTab, string][] = [
  ['watchlist', 'Watchlist'],
  ['estrategias', 'Estratégias'],
  ['avaliacoes', 'Avaliações'],
];

function isSubTab(value: string | null): value is SubTab {
  return value === 'watchlist' || value === 'estrategias' || value === 'avaliacoes';
}

// Agrupa as 3 páginas de "parametrização" (adicionar tickers, afinar critérios,
// forçar reavaliação) sob um único destino na navegação principal - decisão
// 2026-07-21: o fluxo do dia a dia vive quase todo na Overview (leitura), estas
// três só se usam quando se está a configurar/afinar algo, por isso ficam juntas
// aqui em vez de ocuparem 3 lugares na barra de baixo (relevante sobretudo no
// mobile). O Portfolio fica de fora de propósito - é dinheiro real, mais
// frequente/emocional do que afinar critérios, mantém o seu próprio lugar.
// O separador ativo vem de ?tab= na URL (ex: /workspace?tab=avaliacoes), para
// links de outras páginas poderem abrir já no separador certo, não sempre no
// primeiro.
export default function StrategyWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');
  const tab: SubTab = isSubTab(tabParam) ? tabParam : 'watchlist';

  function selectTab(next: SubTab) {
    setSearchParams(next === 'watchlist' ? {} : { tab: next });
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-900 dark:text-slate-100 mb-4">Desenhar estratégia</h1>

      <div className="flex border-b border-gray-200 dark:border-slate-800 mb-4">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            onClick={() => selectTab(key)}
            className={`flex-1 text-center py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === key
                ? 'text-navy-600 dark:text-navy-400 border-navy-600 dark:border-navy-400'
                : 'text-gray-400 dark:text-slate-500 border-transparent'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'watchlist' && <Watchlist embedded />}
      {tab === 'estrategias' && <Strategies embedded />}
      {tab === 'avaliacoes' && <Feed embedded />}
    </div>
  );
}
