interface LibraryCriterion {
  metric: string;
  operator: string;
  threshold: string;
  direction: 'buy_signal' | 'sell_signal';
}

interface LibraryStrategy {
  name: string;
  forWhom: string;
  explanation: string;
  criteria: LibraryCriterion[];
  note?: string;
}

// Conteúdo estático de referência - não faz chamadas à API nem cria nada.
// Cada critério usa apenas métricas que o motor de estratégias já sabe
// avaliar (ver GET /strategies/metrics); onde a estratégia clássica não
// corresponde exatamente aos dados disponíveis, isso fica explícito na nota.
const STRATEGIES: LibraryStrategy[] = [
  {
    name: 'Value Investing',
    forWhom: 'Quem procura empresas "baratas" face aos lucros, com fundamentos sólidos.',
    explanation:
      'Popularizada por Benjamin Graham e Warren Buffett. Procura empresas subavaliadas: P/E baixo, dívida controlada, capazes de gerar caixa de forma consistente.',
    criteria: [
      { metric: 'PE_RATIO', operator: '<', threshold: '15', direction: 'buy_signal' },
      { metric: 'DEBT_TO_EQUITY', operator: '<', threshold: '1.0', direction: 'buy_signal' },
    ],
  },
  {
    name: 'Growth Investing',
    forWhom: 'Quem aceita pagar mais por um crescimento elevado.',
    explanation:
      'Procura empresas que crescem depressa, mesmo com P/E elevado ou lucros ainda reduzidos face ao preço.',
    criteria: [
      { metric: 'REVENUE_GROWTH', operator: '>', threshold: '15', direction: 'buy_signal' },
      { metric: 'EPS', operator: '>', threshold: '0', direction: 'buy_signal' },
    ],
    note: 'Sem histórico diário de fundamentais, o crescimento reflete sempre o valor trimestral mais recente conhecido, não uma tendência ao longo do tempo.',
  },
  {
    name: 'GARP (Growth at a Reasonable Price)',
    forWhom: 'Meio-termo entre Value e Growth — quer crescimento, mas sem pagar qualquer preço por ele.',
    explanation: 'Mistura os dois mundos: exige crescimento real, mas com um P/E ainda razoável.',
    criteria: [
      { metric: 'REVENUE_GROWTH', operator: '>', threshold: '10', direction: 'buy_signal' },
      { metric: 'PE_RATIO', operator: '<', threshold: '25', direction: 'buy_signal' },
      { metric: 'ROE', operator: '>', threshold: '15', direction: 'buy_signal' },
    ],
  },
  {
    name: 'Dividend Investing',
    forWhom: 'Quem procura rendimento passivo em vez de valorização do capital.',
    explanation: 'Compra empresas que distribuem dividendos consistentes e sustentáveis.',
    criteria: [
      { metric: 'DIVIDEND_YIELD', operator: '>', threshold: '0.03', direction: 'buy_signal' },
      { metric: 'DEBT_TO_EQUITY', operator: '<', threshold: '1.5', direction: 'buy_signal' },
    ],
    note: 'O critério de dívida serve para filtrar dividendos pouco sustentáveis — uma empresa muito endividada tem mais probabilidade de cortar o dividendo no futuro.',
  },
  {
    name: 'Quality Investing',
    forWhom: 'Quem prefere pagar por negócios excelentes a apostar em "gangas".',
    explanation: 'Só entra em empresas de elevada qualidade: rentabilidade alta, margens sólidas, pouca dívida.',
    criteria: [
      { metric: 'ROE', operator: '>', threshold: '15', direction: 'buy_signal' },
      { metric: 'NET_MARGIN', operator: '>', threshold: '15', direction: 'buy_signal' },
      { metric: 'DEBT_TO_EQUITY', operator: '<', threshold: '1.0', direction: 'buy_signal' },
    ],
  },
  {
    name: 'Momentum Investing',
    forWhom: 'Quem prefere seguir a tendência do que tentar prever viragens.',
    explanation:
      'Compra o que já está a subir, partindo da ideia de que uma tendência tende a persistir durante algum tempo. Vende quando a tendência quebra.',
    criteria: [
      { metric: 'PRICE_VS_SMA_50', operator: '>', threshold: '0', direction: 'buy_signal' },
      { metric: 'PRICE_VS_SMA_50', operator: '<', threshold: '0', direction: 'sell_signal' },
    ],
    note: 'Ignora por completo se a ação está "barata" ou "cara" — só olha para a direção do preço. Combina mal com Value/Quality no mesmo conjunto de critérios.',
  },
  {
    name: 'Mean Reversion',
    forWhom: 'Quem acredita que quedas acentuadas tendem a corrigir, desde que o negócio continue saudável.',
    explanation: 'Assume que o preço regressa à média: compra quando cai demasiado, vende quando sobe demasiado.',
    criteria: [
      { metric: 'RSI_14', operator: '<', threshold: '30', direction: 'buy_signal' },
      { metric: 'RSI_14', operator: '>', threshold: '70', direction: 'sell_signal' },
    ],
    note: 'Funciona melhor combinado com um filtro de qualidade (ex: adicionar ROE > 10 como critério extra) para evitar comprar apenas porque caiu, sem olhar à saúde da empresa por trás — "apanhar facas a cair".',
  },
  {
    name: 'Small Cap Value',
    forWhom: 'Quem procura empresas pequenas e baratas, aceitando mais volatilidade.',
    explanation: 'Combina duas ideias: empresas de menor dimensão (mais espaço para crescer) e P/E baixo.',
    criteria: [
      { metric: 'MARKET_CAP', operator: '<', threshold: '10', direction: 'buy_signal' },
      { metric: 'PE_RATIO', operator: '<', threshold: '15', direction: 'buy_signal' },
    ],
  },
  {
    name: 'Graham Defensive Investor (aproximação)',
    forWhom: 'Investidor conservador, avesso a risco.',
    explanation: 'Versão simplificada dos critérios de Graham para o "investidor defensivo": preço moderado, dívida baixa, algum dividendo.',
    criteria: [
      { metric: 'PE_RATIO', operator: '<', threshold: '15', direction: 'buy_signal' },
      { metric: 'DEBT_TO_EQUITY', operator: '<', threshold: '1.0', direction: 'buy_signal' },
      { metric: 'DIVIDEND_YIELD', operator: '>', threshold: '0.01', direction: 'buy_signal' },
    ],
    note: 'A versão original de Graham também exige 20 anos seguidos de lucros e uma dimensão mínima da empresa — dados que o Benjamin não guarda. Isto é só uma aproximação nos rácios disponíveis.',
  },
  {
    name: 'Dogs of the Dow (aproximação)',
    forWhom: 'Quem quer uma regra simples e mecânica focada em dividendo elevado de empresas grandes.',
    explanation: 'A estratégia original escolhe as 10 maiores dividend yields do índice Dow Jones a cada ano. Aqui fica só o filtro de yield elevado em empresas de grande dimensão.',
    criteria: [
      { metric: 'DIVIDEND_YIELD', operator: '>', threshold: '0.03', direction: 'buy_signal' },
      { metric: 'MARKET_CAP', operator: '>', threshold: '10', direction: 'buy_signal' },
    ],
    note: 'Não é a estratégia original (essa exige comparar as 10 maiores yields dentro de um índice específico), só um filtro com o mesmo espírito.',
  },
  {
    name: 'Magic Formula (aproximação, Joel Greenblatt)',
    forWhom: 'Quem quer uma fórmula mecânica que combine qualidade e preço.',
    explanation: 'A fórmula original ordena as empresas por ROIC (retorno sobre capital investido) e earnings yield combinados, e compra as mais bem classificadas.',
    criteria: [
      { metric: 'ROE', operator: '>', threshold: '15', direction: 'buy_signal' },
      { metric: 'PE_RATIO', operator: '<', threshold: '20', direction: 'buy_signal' },
    ],
    note: 'Não é a fórmula real: falta o ROIC (o Benjamin usa ROE como aproximação mais próxima disponível) e o ranking cruzado entre ações — aqui são só dois limiares fixos, não uma ordenação.',
  },
  {
    name: 'Rule-Based Investing',
    forWhom: 'Toda a gente que usa o Benjamin.',
    explanation:
      'A estratégia é composta por regras objetivas (ex: "se ROE > 15% E dívida/capital < 0.5 E crescimento de receita > 10% E P/E < 25, então comprar"). É exatamente o que qualquer estratégia criada aqui já faz — todas as anteriores desta lista são só pontos de partida, o Benjamin não faz mais nada por trás disso.',
    criteria: [],
  },
];

const NOT_APPLICABLE: { name: string; reason: string }[] = [
  { name: 'Dollar-Cost Averaging (DCA)', reason: 'compra uma quantia fixa num calendário regular — não é uma condição sobre a ação, é uma decisão de agenda.' },
  { name: 'Index Investing', reason: 'compra de um índice ou ETF inteiro — o Benjamin avalia critérios por ação individual, não gere fundos.' },
  { name: 'Asset Allocation', reason: 'define percentagens por classe de ativo (ações, obrigações, ouro) na carteira toda — é decisão ao nível da carteira, não da ação.' },
  { name: 'Rebalancing', reason: 'ajustar a carteira de volta a percentagens-alvo — trabalha sobre a carteira, não sobre critérios de compra/venda por ação.' },
  { name: 'Calendar Investing', reason: 'comprar em datas fixas (todas as segundas, fim do mês) — decisão de calendário, não de critério de mercado.' },
  { name: 'Covered Calls / Wheel Strategy', reason: 'envolve contratos de opções, que o Benjamin não modela.' },
  { name: 'Pairs Trading / Long-Short Equity', reason: 'compra uma ação e vende outra em simultâneo, com base na relação entre as duas — o motor avalia sempre uma ação de cada vez, isoladamente.' },
  { name: 'Risk Parity', reason: 'aloca capital por contribuição de risco entre classes de ativos — cálculo ao nível da carteira, fora do que o motor de critérios faz.' },
];

function CriterionRow({ c }: { c: LibraryCriterion }) {
  return (
    <span
      className={`text-xs px-2 py-1 rounded-lg ${
        c.direction === 'buy_signal'
          ? 'bg-green-50 text-green-700 dark:bg-emerald-500/10 dark:text-emerald-400'
          : 'bg-red-50 text-red-700 dark:bg-rose-500/10 dark:text-rose-400'
      }`}
    >
      {c.metric} {c.operator} {c.threshold}
    </span>
  );
}

// Lista de referência só para consulta - nenhum destes cartões cria ou aplica
// nada; servem de inspiração para montar uma estratégia própria em "Nova
// estratégia" com os critérios equivalentes.
export default function StrategyLibrary() {
  return (
    <div>
      <p className="text-sm text-gray-500 dark:text-slate-400 mb-4">
        Estratégias conhecidas, para inspiração — nenhuma se aplica automaticamente. Usa os critérios sugeridos como
        ponto de partida ao criar a tua própria estratégia.
      </p>

      <div className="space-y-3">
        {STRATEGIES.map((s) => (
          <div
            key={s.name}
            className="bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl shadow-sm p-4"
          >
            <p className="font-semibold text-gray-900 dark:text-slate-100">{s.name}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{s.forWhom}</p>
            <p className="text-sm text-gray-700 dark:text-slate-300 mt-2">{s.explanation}</p>
            {s.criteria.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {s.criteria.map((c, i) => (
                  <CriterionRow key={i} c={c} />
                ))}
              </div>
            )}
            {s.note && <p className="text-xs text-gray-400 dark:text-slate-500 mt-2">{s.note}</p>}
          </div>
        ))}
      </div>

      <div className="mt-6 bg-gray-50 dark:bg-slate-900/50 border border-gray-100 dark:border-slate-800 rounded-xl p-4">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100 mb-1">Não dá para montar no Benjamin</p>
        <p className="text-xs text-gray-500 dark:text-slate-400 mb-3">
          Estas são estratégias reais, mas trabalham ao nível da carteira toda, do calendário, ou de instrumentos
          (opções, posições relativas) que o motor de critérios por ação não cobre.
        </p>
        <ul className="space-y-2">
          {NOT_APPLICABLE.map((n) => (
            <li key={n.name} className="text-xs text-gray-600 dark:text-slate-400">
              <span className="font-medium text-gray-700 dark:text-slate-300">{n.name}</span> — {n.reason}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
