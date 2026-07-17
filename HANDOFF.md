# HANDOFF — Benjamin app development

> Documento de contexto para continuar o desenvolvimento (Cowork / Claude Code).
> Ler primeiro SPEC.md (especificação) e CLAUDE.md (convenções).

## O que é o Benjamin
App pessoal de investimento: watchlist de ações + estratégias de critérios
configuráveis + agente determinístico que calcula buy_score e sell_score (0-100)
e recomenda BUY/SELL/HOLD segundo os critérios do próprio utilizador.
Posicionamento: ferramenta de apoio à decisão, NÃO aconselhamento financeiro.

## Estado atual (o que já está feito)
Fases do SPEC secção 10:
- [x] Fase 1 — Skeleton: docker-compose (api+postgres), FastAPI, /health, scaffold Alembic
- [x] Fase 2 — Auth (JWT, bcrypt, registo fechado por env var) + Watchlist CRUD
- [x] Fase 3 — Ingestão via Finnhub + Twelve Data (preço atual + fundamentais + backfill de
  histórico), gravação idempotente, ensure_fresh() — ver "Mudança de fornecedor" abaixo
- [x] Fase 4 — 6 indicadores MVP (PRICE_CLOSE, RSI_14, SMA_50, SMA_200, PE_RATIO, DIVIDEND_YIELD) com cache em indicator_values
- [x] Fase 5 — Agente (buy/sell scores separados, SELL prioridade ≥70) + endpoints /evaluations
- [x] Fase 6 — Frontend PWA (React+Vite+TS+Tailwind), 6 páginas (Overview, Login, Watchlist, Strategies,
  StrategyEditor, Feed) ligadas à API real via `src/api/client.ts`. `npm install`/`npm run dev`
  ainda NÃO foram corridos neste ambiente (sem rede) — validar localmente.
  - Overview (`/`, antigo "Home") é a página inicial pós-login: resumo de sinais (contagem
    BUY/SELL/HOLD), separador "Sinais" com a watchlist reordenável manualmente (setas ▲▼,
    persistido via `PUT /watchlist/reorder` + coluna `display_order`) mostrando data da última
    avaliação (reaproveita `latest_evaluation` de `GET /watchlist`), e separador "Notícias"
    (`GET /watchlist/news`, agregando Finnhub `/company-news` por cada ticker da watchlist,
    resiliente a falhas).
- [~] Fase 7 — Scheduler APScheduler (sáb 08:00 UTC) + email resumo FEITOS; docker-compose.prod.yml com Caddy e README de deploy Hetzner POR FAZER

## Validação (sessão 2026-07-16)
- `pytest` corrido localmente pelo utilizador: **33 passed**. Suite completa verde (16 núcleo +
  3 email_service + 14 API: auth, watchlist, strategies, evaluations).
- Dois bugs de ambiente encontrados e corrigidos nesta sessão (nenhum bug de lógica):
  1. `backend/pyproject.toml` sem `[tool.setuptools.packages.find]` → `pip install -e .` falhava
     com "Multiple top-level packages discovered" (via alembic/ + app/ na raiz). Corrigido com
     `include = ["app*"]`.
  2. `EmailStr` (pydantic) precisa do pacote `email-validator`, que não estava nas dependências.
     Adicionado `email-validator==2.2.0`. Depois disto, o email-validator 2.x rejeitou por defeito
     os domínios de teste `*.test.local` (RFC 6761/6762 special-use domains — `.local`, `.test`,
     etc. são bloqueados mesmo com `check_deliverability=False`). Renomeados os emails de teste
     para `*.test.dev` e o seed de `demo@local` para `demo@benjamin.dev`.
- Frontend (Fase 6): compilado e testado manualmente pelo utilizador (login, watchlist, estratégias,
  feed). Adicionadas sugestões rápidas de tickers + pesquisa na Watchlist (a pedido).

## Mudança de fornecedor de dados: yfinance → Finnhub + Twelve Data (2026-07-17)
Em uso real, o yfinance revelou-se inviável: o Yahoo Finance não tem API oficial, e o scraping
não-oficial que o yfinance usa começou a levar 429 (Too Many Requests) em praticamente todos os
pedidos, de forma persistente e sem aviso. Substituído por:
- **Finnhub** (free tier, chave em `FINNHUB_API_KEY`): preço atual (`/quote`), perfil/validação de
  ticker (`/stock/profile2`), fundamentais (`/stock/metric`), pesquisa por nome (`/search`).
  ⚠️ o endpoint `/stock/candle` (histórico) passou a ser só pago desde 2025 — por isso não é usado.
- **Twelve Data** (free tier, 800 pedidos/dia, chave em `TWELVEDATA_API_KEY`): só para o backfill
  inicial de histórico diário (`/time_series`), chamado apenas enquanto uma stock tiver menos de
  200 dias de `price_snapshots` gravados. Depois disso, o histórico cresce um dia de cada vez via
  o `/quote` do Finnhub (chamado pelo `daily_refresh_job`).
- Ambos os fornecedores são resilientes a falhas: se uma chamada falhar (rede, rate limit, etc.),
  o código não rebenta — loga um aviso e segue em frente com o que tiver (ver
  `services/market_data.py`, funções `_finnhub_get`/`_twelvedata_get` e o comentário no topo do
  ficheiro).
- Nomes dos campos de `/stock/metric` confirmados com payload real (MSFT, 2026-07-17): `peTTM`,
  `currentDividendYieldTTM`/`dividendYieldIndicatedAnnual` (em percentagem, daí a divisão por 100),
  `marketCapitalization` (em milhões, daí a multiplicação por 1_000_000), `epsTTM`,
  `totalDebt/totalEquityAnnual`. Todos corretos — nada a ajustar em `refresh_fundamentals`.
- Ambas as chaves já estão em `.env` (não commitado) e como placeholders vazios em `.env.example`.

## Rebranding: Checklist → Estratégia (2026-07-17)
"Checklist" nunca foi o nome certo: os items não são tarefas para marcar, são regras de scoring
ponderado (metric + operator + threshold + weight). Renomeado para "Estratégia/Strategy" em toda a
stack:
- Backend: `models/checklist.py` → `models/strategy.py` (`ChecklistTemplate`/`ChecklistItem` →
  `StrategyTemplate`/`StrategyItem`); `routers/checklists.py` → `routers/strategies.py`
  (`/checklists` → `/strategies`); schemas, `agent.py`, `scheduler.py`, `email_service.py`,
  `seed.py` e testes atualizados a condizer.
- BD: nova migration `8f2a1c9d4b6e_rename_checklist_to_strategy` faz `rename_table` das tabelas
  (`checklist_templates`→`strategy_templates`, `checklist_items`→`strategy_items`) e `rename_column`
  das FKs (`evaluations.checklist_template_id`→`strategy_template_id`,
  `evaluation_details.checklist_item_id`→`strategy_item_id`) — preserva os dados existentes, não
  recria as tabelas. Aproveitou para também corrigir `strategy_items.weight` para `NUMERIC(5,2)`
  (o modelo já tinha sido alargado para o slider 0-100, mas nunca tinha sido gerada a migration).
  **Ação necessária**: correr `docker compose exec api alembic upgrade head` para aplicar.
- Frontend: `Checklists.tsx`/`ChecklistEditor.tsx` → `Strategies.tsx`/`StrategyEditor.tsx`, rotas
  `/checklists` → `/strategies`, tipos `ChecklistTemplate`/`ChecklistItem` →
  `StrategyTemplate`/`StrategyItem`, label do NavBar → "Estratégias".

## Passos de arranque local
1. cp .env.example .env  (definir JWT_SECRET)
2. docker compose up --build
3. docker compose exec api alembic upgrade head
4. docker compose exec api python -m app.seed   → demo@benjamin.dev / demo1234

## Decisões já tomadas (não reabrir sem razão)
- Nome: Benjamin (com n)
- Stack fechada no SPEC.md secção 2 (Finnhub + Twelve Data, PWA, APScheduler, SMTP, JWT simples)
- Fora do MVP: SPEC.md secção 13 (RLS, refresh tokens, news, portfólio, Celery...)
- Deploy alvo: Hetzner CX22 + Caddy + ufw (detalhado na conversa de arquitetura)

## Próximos passos por ordem
1. ~~Correr `pytest` localmente~~ — FEITO, 33 passed (a subir para ~39 com os testes novos do Finnhub)
2. ~~Correr `npm install && npm run dev` e validar o fluxo manual~~ — FEITO
3. Confirmar os campos de `/stock/metric` da Finnhub (P/E, dividend yield) com um payload real
4. Fase 7 restante: docker-compose.prod.yml + Caddy + guia de deploy
5. Gerar e commitar a migration inicial do Alembic
