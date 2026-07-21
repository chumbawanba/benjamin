# ROADMAP — Benjamin (consolidado técnico + negócio)

> Junta três fontes: o SPEC.md técnico original (MVP fases 1-7 + Fase 8 pathway),
> o BUSINESS.md (plano de negócio e roadmap de produto fases 8-11), e o estado real
> do código depois de várias sessões de desenvolvimento que já foram além do plano
> inicial nalguns pontos. Não substitui SPEC.md nem HANDOFF.md (que continuam a ser
> a fonte de verdade técnica) — é a vista de conjunto para decidir o que vem a seguir.
>
> Os ficheiros enviados (BUSINESS.md, SPEC.md antigo, landing page) vieram de uma
> conversa de planeamento separada, anterior a grande parte do que já foi construído.
> A secção 6 lista onde esses documentos ficaram desatualizados face ao código real.

---

## 1. Fundação técnica (SPEC.md original, fases 1-7) — feito

- [x] **Fase 1 — Skeleton**: Docker Compose (api + postgres), FastAPI, `/health`, Alembic.
- [x] **Fase 2 — Auth + Watchlist CRUD**: JWT, bcrypt, registo fechado por env var,
  isolamento por utilizador testado.
- [x] **Fase 3 — Ingestão de dados**: substituída a escolha original (yfinance, que
  passou a levar 429 em produção) por **Finnhub + Twelve Data** — ver secção 6.
- [x] **Fase 4 — Indicadores**: 9 indicadores no registry (`PRICE_CLOSE`, `RSI_14`,
  `SMA_50`, `SMA_200`, `PE_RATIO`, `DIVIDEND_YIELD`, `EPS`, `DEBT_TO_EQUITY`,
  `MARKET_CAP` — 3 fundamentais a mais do que os 6 do plano original).
- [x] **Fase 5 — Agente + evaluations**: `buy_score`/`sell_score`, prioridade de venda,
  endpoints `/evaluations/*`.
- [x] **Fase 6 — Frontend PWA**: React + Vite + TS + Tailwind, ligado à API real.
- [~] **Fase 7 — Scheduler + email**: job semanal + refresh diário de preços feitos;
  **por fazer**: `docker-compose.prod.yml` com Caddy + guia de deploy Hetzner.

---

## 2. Além do MVP original — já construído (não estava no plano inicial)

Estas funcionalidades não constavam nem do SPEC.md original nem do BUSINESS.md;
nasceram de necessidade direta ao usar a app.

- **Rebranding Checklist → Estratégia** (2026-07-17): o nome original não descrevia
  bem o conceito (regras de scoring ponderado, não tarefas). Mudado em toda a stack
  + migração que preserva dados.
- **Horizonte de estratégia** (curto/médio/longo prazo) + sinais agrupados por
  estratégia no Overview.
- **Otimizador de estratégia** (`backend/app/services/backtest_core.py`): backtest
  greedy sobre ~12 meses da watchlist, propõe critérios que maximizem retorno
  simulado vs comprar-e-manter. Isto é, na prática, uma primeira versão (mais
  simples) do que o BUSINESS.md chama "Fase 9 — Backtesting técnico" — ver secção 4
  para o que falta para bater certo com a visão de produto original.
- **UX**: badge único de recomendação (BUY/SELL/HOLD, sem números confusos),
  reordenação manual na watchlist/overview, SMA 200 no gráfico, página de detalhe
  por ação (`StockDetail.tsx`), layout mais largo em tablet/desktop.
- **Fix de dois bugs reais de produção**: `ON DELETE CASCADE` em falta nas FKs de
  `evaluations`/`evaluation_details` (apagar uma estratégia avaliada rebentava).
- **Portfolio real** (`Position`, 2026-07-19): quantidade + custo médio por ação,
  independente da watchlist, com P&L não realizado calculado on-the-fly. O SPEC.md
  original listava isto explicitamente como **"fora do MVP"** — foi construído
  porque o utilizador pediu diretamente, e faz sentido dado o produto já ter
  amadurecido. Ver correção necessária na secção 6.
- **Benjamin: analista IA (OpenAI)** — não existe em nenhum dos dois documentos
  enviados. Resumo em português sobre watchlist + portfolio + mercado geral,
  gerado manualmente (nunca em scheduler), prompt de sistema editável pelo
  utilizador, deteta concentração de risco e aponta sinais de compra na watchlist
  ainda não possuídos. É provavelmente a maior diferenciação atual do produto
  face à concorrência descrita no BUSINESS.md secção 2 (nenhum concorrente listado
  tem uma camada de IA conversacional sobre os dados do utilizador).

---

## 3. Feito (2026-07-21) — era "em curso" na sessão anterior

- **Perguntas ao Benjamin com contexto** (ex: "porque não tenho sinal de compra na
  Microsoft?"): `POST /analyst/ask` reutiliza o contexto do resumo (watchlist +
  portfolio + mercado) e acrescenta o detalhe critério-a-critério de cada avaliação
  (antes só disponível na StockDetail). Histórico de conversa mantido no frontend
  (sem tabela nova na BD, máx. 20 mensagens), prompt de sistema dedicado, pergunta
  limitada a 1000 caracteres. UI: secção "Perguntar" no `AnalystSummaryCard`.
- **Fundamentais no input do Benjamin**: `analyst._build_context` passou a incluir
  P/E, dividend yield, EPS, dívida/capital próprio e market cap por posição/item da
  watchlist. Ver `HANDOFF.md` para detalhe técnico.

Ainda por considerar (não pedido): alargar o registry de indicadores com mais campos
que a Finnhub já devolve em `/stock/metric` (ROE, margens, PEG, price/book) — mesma
fonte de dados, sem custo adicional.

---

## 4. Roadmap de produto (BUSINESS.md secção 7) — por fazer

| Fase | O que é | Estado |
|---|---|---|
| **Fase 8 — Learning pathway** | Lições curtas (100% saltáveis) que terminam sempre numa ação real na app; ativação de novos utilizadores. Schema já desenhado no SPEC.md enviado (`pathway_lessons`, `pathway_progress`). | Não iniciado |
| **Fase 9 — Backtesting v1 (user-facing)** | Relatório de backtest com benchmark, drawdown máximo, nº de trades, disclaimers de overfitting/survivorship — pensado como feature de conversão grátis→pago. | **Parcial**: o motor (`backtest_core.py`) já existe e já calcula retorno simulado vs comprar-e-manter; falta drawdown máximo, nº de trades explícito, e o enquadramento/disclaimers estatísticos que o BUSINESS.md pede antes de ser vendável como feature paga |
| **Fase 10 — Screener por critérios** | Aplicar a estratégia do utilizador a um universo curado (PSI, S&P 500, Stoxx 600) para descobrir ações novas, não só avaliar a watchlist existente. Reutiliza o motor do agente. | Não iniciado — exige job de ingestão do universo + tabela de constituintes por índice |
| **Fase 11 — Comparação de variantes + fundamentais históricos** | "E se RSI<25 em vez de 30?" lado a lado; fundamentais point-in-time (não só o snapshot mais recente). | Não iniciado — fundamentais históricos são dados caros, só com receita |
| **i18n** | Strings externalizadas desde já, lançar só em PT. | Não iniciado (app toda em PT hardcoded) |

---

## 5. Negócio / go-to-market (BUSINESS.md secções 4-10) — por fazer

Nada disto tem uma linha de código ainda — a app não tem sistema de cobrança,
tiers, nem conta institucional:

1. **Uso pessoal 1-3 meses** para afinar o produto antes de mostrar a mais ninguém
   (em curso — é literalmente o que tem estado a acontecer nas últimas sessões).
2. **Landing page + lista de espera**: já existe um mockup completo enviado
   (`benjamin-landing.html` — hero, posicionamento "os teus critérios, verificados
   todas as semanas", identidade visual verde-tinta/âmbar). Ainda não está no
   repositório do produto nem publicado — é um artefacto separado, a decidir onde
   fica alojado.
3. **Consulta jurídica** (fronteira MiFID II / CMVM sobre aconselhamento financeiro)
   antes de expor a app a desconhecidos — a mais importante antes de qualquer beta
   público, mesmo grátis.
4. **Abertura de atividade** (recibos verdes → depois Lda quando houver receita
   recorrente).
5. **Beta fechado em comunidades PT** (r/literaciafinanceira, grupos de
   investimento) com lifetime deal aos primeiros testers.
6. **Stack de cobrança**: Stripe + Stripe Tax + InvoiceXpress (faturação
   certificada obrigatória em PT), modelo freemium (grátis: 1 estratégia, 5
   ações, avaliação semanal / Pro €7-59: ilimitado, diário, histórico).
7. **Migração de dados para plano comercial** antes de cobrar — Finnhub/Twelve
   Data free tier não têm licença para uso comercial pago.
8. Fase 8 (pathway) e Fase 9 (backtesting) conforme tração real, não antes.
9. Expansão EN → BR conforme validação e receita (BR só faz sentido com dados B3 +
   parceria de conteúdo local, não antes).

---

## 6. Discrepâncias entre os documentos enviados e o estado real

Os ficheiros enviados descrevem um estado anterior do produto — nada disto é
"culpa" do plano, só ficou desatualizado com a evolução real:

- O **SPEC.md enviado** ainda assume **yfinance** como fonte de dados; o produto
  real usa **Finnhub + Twelve Data** desde 2026-07-17 (yfinance começou a levar 429
  persistente em produção). O SPEC.md real do repositório já reflete isto.
- O **SPEC.md enviado** ainda usa a nomenclatura **"Checklist"**; o produto real
  chama-se **"Estratégia/Strategy"** desde 2026-07-17 (rebranding com migração de
  BD incluída).
- O **SPEC.md enviado** lista explicitamente **"Portfólio + transações"** como
  **fora do MVP** (secção 13); isto já foi construído (secção 2 acima). O
  `HANDOFF.md` real do repositório tem a mesma frase desatualizada numa lista de
  "decisões já tomadas" — corrigido nesta sessão para não continuar a confundir
  quem ler a seguir.
- Nem o SPEC.md nem o BUSINESS.md enviados mencionam o **Benjamin (analista IA)** —
  é uma adição completamente nova, não prevista em nenhum dos planos, e que na
  prática já cobre parte do valor que a Fase 9 (backtesting) e mesmo alguma
  literacia do pathway (Fase 8) se propunham a dar, só que de forma conversacional
  em vez de estruturada.
- O **`benjamin-landing.html`** enviado é um mockup de marketing, não um artefacto
  de produto — não foi integrado no repositório da app (viveria separado, como
  site institucional/waitlist, não dentro do frontend React da aplicação).

---

## 7. Sugestão de sequência a partir de agora

Dado o que já está feito, a ordem que faz mais sentido tecnicamente (sem entrar em
decisões de negócio, que são tuas):

1. ~~Perguntas ao Benjamin com contexto + fundamentais no input~~ — FEITO (secção 3).
   Falta só validar manualmente no browser (ver `HANDOFF.md`, próximos passos).
2. Fase 7 restante (Caddy + deploy Hetzner) — só é urgente quando quiseres que
   outra pessoa aceda à app fora da tua rede local.
3. Consulta jurídica (secção 5, ponto 3) — antes de qualquer beta com desconhecidos,
   independentemente do estado técnico.
4. Só depois disso, e conforme apetite: pathway (Fase 8) para ativação, ou reforçar
   o backtesting existente até bater certo com a Fase 9 do BUSINESS.md (drawdown,
   nº de trades, disclaimers) para servir de feature de conversão paga.
