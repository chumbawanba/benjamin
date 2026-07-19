# SPEC — App de Watchlist + Estratégias + Agente de Avaliação de Investimentos

> Documento de implementação. Todas as decisões técnicas estão fechadas.
> Implementar por fases, na ordem indicada. Cada fase tem critérios de aceitação.
> Nenhuma fase está completa sem os testes correspondentes a passar.

---

## 1. Resumo do produto

App pessoal (1 utilizador no MVP, preparada para multi-user depois) que permite:
1. Gerir uma **watchlist** de ações
2. Criar **estratégias** de critérios de compra/venda (dados configuráveis, não código)
3. Correr um **agente determinístico** que avalia cada ação da watchlist e devolve `buy_score` e `sell_score` (0-100)
4. Ver um **feed de propostas** (BUY / SELL / HOLD)
5. Receber um **email resumo semanal**
6. (Fase futura, fora do MVP) gerir portfólio real

---

## 2. Stack — decisões fechadas

| Componente | Escolha | Notas |
|---|---|---|
| Backend | Python 3.12 + FastAPI | async |
| ORM | SQLAlchemy 2.0 (async) + Alembic | |
| Base de dados | PostgreSQL 16 | via Docker Compose, também em dev |
| Dados de mercado | **Finnhub** (preço atual, fundamentais, pesquisa) + **Twelve Data** (backfill de histórico diário) | API keys grátis; substituiu o yfinance (secção 13 original) por rate-limiting imprevisível do Yahoo |
| Indicadores | pandas (cálculo manual de RSI/SMA) | não usar ta-lib (instalação frágil) |
| Scheduler | APScheduler (in-process, no container da API) | job semanal: sábado 08:00 UTC |
| Email | SMTP (Gmail com app password) | config via env vars |
| Auth | JWT access token, 24h de validade, sem refresh token | bcrypt para passwords |
| Frontend | PWA — React 18 + Vite + TypeScript | sem app nativa |
| Estilo frontend | Tailwind CSS | |
| Reverse proxy (prod) | Caddy | HTTPS automático |
| Deploy | Docker Compose num VPS Hetzner CX22 | |
| Testes | pytest + httpx (backend) | frontend: sem testes no MVP |

**Fora do MVP (não implementar agora):** Row Level Security, refresh tokens, 2FA, news/sentiment, notificações push, portfólio, fila de jobs (Celery/RQ), multi-utilizador com registo público.

---

## 3. Estrutura de ficheiros

```
projeto/
├── CLAUDE.md
├── SPEC.md                     # este ficheiro
├── docker-compose.yml          # api + db + frontend (dev)
├── docker-compose.prod.yml     # api + db + caddy
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/                # migrations
│   ├── app/
│   │   ├── main.py             # FastAPI app + APScheduler startup
│   │   ├── config.py           # settings via pydantic-settings
│   │   ├── database.py         # engine, SessionLocal, get_db
│   │   ├── models/             # SQLAlchemy models (1 ficheiro por domínio)
│   │   │   ├── user.py
│   │   │   ├── stock.py
│   │   │   ├── watchlist.py
│   │   │   ├── strategy.py
│   │   │   ├── market_data.py  # price/fundamentals snapshots, indicator_values
│   │   │   └── evaluation.py
│   │   ├── schemas/            # Pydantic schemas (mesma divisão)
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── watchlist.py
│   │   │   ├── strategies.py
│   │   │   └── evaluations.py
│   │   ├── services/
│   │   │   ├── market_data.py  # Finnhub + Twelve Data: fetch + gravar snapshots
│   │   │   ├── indicators.py   # registry + cálculo + cache
│   │   │   ├── agent.py        # evaluate(stock, template) -> Evaluation
│   │   │   └── email.py        # resumo semanal
│   │   └── scheduler.py        # job semanal
│   └── tests/
│       ├── conftest.py         # fixtures: db de teste, client, user, seed
│       ├── test_auth.py
│       ├── test_watchlist.py
│       ├── test_strategies.py
│       ├── test_indicators.py
│       ├── test_agent.py
│       └── test_evaluations_api.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.ts          # com plugin PWA
    └── src/
        ├── api/client.ts       # fetch wrapper com JWT
        ├── pages/
        │   ├── Login.tsx
        │   ├── Watchlist.tsx
        │   ├── Strategies.tsx
        │   ├── StrategyEditor.tsx
        │   └── Feed.tsx        # propostas (evaluations mais recentes)
        └── components/
```

---

## 4. Modelo de dados

Schema SQL de referência em anexo (`schema.sql`), com estas alterações para o MVP:
- Ignorar tabelas `news_items`, `portfolio_positions`, `transactions` (fase futura — não criar migrations para elas)
- `evaluations` tem `buy_score` e `sell_score` (duas colunas DECIMAL(6,2)), além de `recommendation`
- Gerar os modelos SQLAlchemy a partir do schema; as migrations Alembic são a fonte de verdade

### Regras de negócio no modelo
- `strategy_items.metric` referencia uma chave do registry de indicadores (string, ex: `"RSI_14"`)
- `strategy_items.direction` ∈ {`buy_signal`, `sell_signal`}
- `strategy_items.operator` ∈ {`<`, `>`, `<=`, `>=`, `==`, `between`}
- `evaluations.recommendation` ∈ {`BUY`, `SELL`, `HOLD`}

---

## 5. Registry de indicadores

Implementados em `services/indicators_core.py` (registry `INDICATORS`):

| Chave | Cálculo | Fonte |
|---|---|---|
| `PRICE_CLOSE` | último fecho | price_snapshots |
| `RSI_14` | RSI de 14 períodos (método Wilder) | price_snapshots |
| `SMA_50` | média móvel simples 50 dias | price_snapshots |
| `SMA_200` | média móvel simples 200 dias | price_snapshots |
| `PE_RATIO` | valor mais recente | fundamentals_snapshots |
| `DIVIDEND_YIELD` | valor mais recente | fundamentals_snapshots |
| `EPS` | valor mais recente | fundamentals_snapshots |
| `DEBT_TO_EQUITY` | valor mais recente | fundamentals_snapshots |
| `MARKET_CAP` | valor mais recente, escalado para mil milhões de USD (`scale: 1e9`) | fundamentals_snapshots |

Regras:
- Cada indicador declara `lookback_days` mínimo; se não houver histórico suficiente, devolve `None` (nunca lança exceção)
- Valores calculados são gravados em `indicator_values` (cache); antes de calcular, verificar se já existe valor para (stock, indicador, data de hoje)
- Indicadores fundamentais podem declarar `"scale"` (divisor aplicado ao valor bruto) — usado por `MARKET_CAP` para caber nas colunas `Numeric(12,4)`/`Numeric(14,6)` de threshold e cache, já que o valor bruto em USD (na casa dos biliões) excederia essa precisão
- Adicionar um indicador novo = adicionar entrada ao dict `INDICATORS` + (se for "price") função de cálculo. Nada mais muda — o endpoint `/strategies/metrics` e o dropdown do frontend derivam automaticamente do registry.

---

## 6. Agente (`services/agent.py`)

```
async def evaluate(stock_id, template_id, user_id) -> Evaluation
```

Algoritmo:
1. Garantir dados de mercado atualizados para a stock (delegar em `market_data.ensure_fresh(stock_id)` — busca via Finnhub/Twelve Data se o snapshot mais recente tiver > 3 dias)
2. Para cada `strategy_item` ativo do template:
   - `observed_value = indicators.get(stock_id, item.metric)`
   - Se `observed_value is None` → `passed = None`, `contribution = 0`, e o `weight` desse item é excluído do denominador
   - Senão: `passed = aplicar_operador(observed_value, item.operator, item.threshold_value, item.threshold_value_max)`
   - `contribution = item.weight if passed else 0`
3. Scores separados por direção:
   - `buy_score = 100 * Σ(contribution | buy_signal) / Σ(weight | buy_signal avaliáveis)` (0 se não houver critérios buy avaliáveis)
   - `sell_score` idem para `sell_signal`
4. Recomendação:
   - `sell_score >= 70` → `SELL` (venda tem prioridade sobre compra)
   - senão `buy_score >= 70` → `BUY`
   - senão → `HOLD`
5. Gravar `Evaluation` (com `price_at_evaluation` = PRICE_CLOSE) + um `EvaluationDetail` por item (incluindo os `passed = None`)
6. Devolver a Evaluation

### Exemplo de referência (usar como caso de teste)
Estratégia "Value simples":
```json
[
  {"name": "RSI sobrevendido", "metric": "RSI_14", "operator": "<", "threshold_value": 30, "weight": 2, "direction": "buy_signal"},
  {"name": "P/E barato", "metric": "PE_RATIO", "operator": "<", "threshold_value": 15, "weight": 1, "direction": "buy_signal"},
  {"name": "RSI sobrecomprado", "metric": "RSI_14", "operator": ">", "threshold_value": 70, "weight": 1, "direction": "sell_signal"}
]
```
Dados: RSI_14 = 25, PE_RATIO = 12.
Esperado: buy_score = 100 (3/3 pontos), sell_score = 0, recommendation = BUY.

Dados: RSI_14 = 50, PE_RATIO = None (sem fundamentais).
Esperado: buy_score = 0 (0/2 pontos avaliáveis), sell_score = 0, recommendation = HOLD, detail do P/E com passed = None.

---

## 7. API

Prefixo `/api/v1`. Todos os endpoints (exceto auth) exigem `Authorization: Bearer <jwt>`.
Todas as queries filtram por `user_id` extraído do token — **nunca** aceitar user_id do cliente.

```
POST /auth/register        # MVP: protegido por env var ALLOW_REGISTRATION=false por defeito
POST /auth/login           # -> {access_token}

GET    /watchlist                      # itens + última evaluation + last_price/price_change_pct de cada stock
GET    /watchlist/search?q=            # pesquisa tickers por nome/símbolo (Finnhub)
GET    /watchlist/news?limit=20        # notícias agregadas por ticker da watchlist, deduplicadas
GET    /watchlist/{item_id}/detail     # histórico de preço + indicadores + fundamentais + breakdown da última evaluation
POST   /watchlist                      # body: {ticker, notes?, target_buy_price?, target_sell_price?}
                                       # se o ticker não existir em stocks, criar via Finnhub (validar que existe)
                                       # corre logo as estratégias ativas do utilizador contra a nova ação
PUT    /watchlist/reorder              # body: {ordered_ids: [uuid, ...]} — grava display_order manual
DELETE /watchlist/{item_id}

GET    /strategies
POST   /strategies                     # {name, description?, horizon?}  horizon: short_term|medium_term|long_term|null
PUT    /strategies/{id}
DELETE /strategies/{id}
POST   /strategies/{id}/items
PUT    /strategies/items/{item_id}
DELETE /strategies/items/{item_id}
GET    /strategies/metrics             # lista as chaves do registry (para dropdowns no frontend)
POST   /strategies/{id}/optimize       # backtest greedy sobre a watchlist inteira (~12 meses); devolve proposta de
                                       # critérios + retorno simulado vs comprar-e-manter — não altera a estratégia,
                                       # o cliente aplica via POST/DELETE .../items

POST /evaluations/run                  # body: {template_id, stock_id?} — sem stock_id corre a watchlist toda
GET  /evaluations/latest               # última evaluation por stock da watchlist (feed)
GET  /evaluations/latest-by-strategy   # sinais BUY/SELL mais recentes agrupados por estratégia ativa (HOLD omitido, Overview)
GET  /evaluations?stock_id=&limit=20   # histórico

GET  /analyst/summary                  # último resumo do analista ("Benjamin") gerado (cache, não chama o LLM)
POST /analyst/summary/refresh          # gera um novo resumo via OpenAI (portfolio + watchlist + mercado geral) — manual, sem scheduler
GET  /analyst/prompt                   # prompt de sistema em uso (personalizado ou predefinição)
PUT  /analyst/prompt                   # {prompt?} — guarda um prompt personalizado; null/vazio repõe a predefinição

GET    /portfolio                      # posições reais (qty + custo médio) com valor de mercado e P&L não realizado calculados on-the-fly
POST   /portfolio                      # body: {ticker, quantity, avg_cost} — 422 se já existir posição nesse ticker
PUT    /portfolio/{position_id}        # body: {quantity, avg_cost} — substitui os valores (sem histórico de transações)
DELETE /portfolio/{position_id}

GET /health                            # sem auth: {"status": "ok", "db": true}
```

Erros: HTTP 404 para recursos de outro utilizador (não 403, para não revelar existência), 422 para validação, 401 sem token.

---

## 8. Scheduler + email

- APScheduler arranca no lifespan do FastAPI, com dois jobs:
  1. **`daily_refresh_job`** (diário, 06:00 UTC): para cada stock presente em alguma watchlist,
     chama `market_data.ensure_fresh()`. Não avalia estratégias nem envia email — só mantém os
     preços/fundamentais aquecidos em cache, para a app raramente precisar de consultar o Yahoo
     Finance em tempo real enquanto o utilizador a usa (adicionado após o MVP inicial, por pedido
     explícito, para mitigar os 429 do Yahoo durante o uso interativo).
  2. **`weekly_job`** (sábado 08:00 UTC): para cada utilizador, para cada estratégia ativa →
     `agent.evaluate()` sobre todas as stocks da watchlist (deduplicar fetch de dados por ticker)
- No fim do `weekly_job`: enviar email com tabela ticker | buy_score | sell_score | recomendação | preço, agrupado por estratégia. Enviar só se houver pelo menos 1 stock na watchlist
- Configuração SMTP e email de destino via env vars; se SMTP não estiver configurado, fazer log e não falhar o job

---

## 9. Frontend (PWA)

Páginas mínimas, mobile-first:
1. **Login** — guarda o JWT em memória + localStorage (aceitável no MVP)
2. **Watchlist** — lista com ticker, preço, badges buy/sell score coloridos (verde ≥70, cinzento 40-69, vermelho para sell ≥70); adicionar por ticker; swipe/botão para remover
3. **Estratégias** — lista de templates; criar/ativar/desativar
4. **StrategyEditor** — CRUD de items: dropdown de metric (vem de `/strategies/metrics`), operador, threshold, weight, direction
5. **Feed** — cartões das evaluations mais recentes ordenados por score, com detalhe expansível (critérios passed/failed/N.A.); botão "Avaliar agora" que chama `/evaluations/run`

PWA: manifest + service worker via `vite-plugin-pwa` (só instalabilidade; sem offline logic no MVP).

---

## 10. Fases de implementação

> Ordem obrigatória. Critério global: `pytest` verde + a app sobe com `docker compose up`.

**Fase 1 — Skeleton**
Docker Compose (api + db), FastAPI com `/health`, Alembic configurado, migration inicial com todas as tabelas do MVP, config via pydantic-settings.
✅ Pronto quando: `docker compose up` sobe, `GET /health` devolve `{"status":"ok","db":true}`, `alembic upgrade head` corre limpo.

**Fase 2 — Auth + Watchlist CRUD**
Registo (fechado por env var), login, JWT, CRUD watchlist com validação de ticker via Finnhub (mock nos testes).
✅ Pronto quando: testes de auth + watchlist passam; utilizador A não vê itens do utilizador B (teste explícito).

**Fase 3 — Ingestão de dados**
`services/market_data.py`: fetch de preço atual e fundamentais via Finnhub + backfill de histórico via Twelve Data, gravação idempotente em snapshots, `ensure_fresh()`.
✅ Pronto quando: testes com Finnhub/Twelve Data mockados passam; correr duas vezes não duplica linhas.

**Fase 4 — Indicadores**
Registry com os 6 indicadores, cache em `indicator_values`, handling de histórico insuficiente.
✅ Pronto quando: testes com séries de preços sintéticas validam RSI/SMA contra valores conhecidos; segundo cálculo no mesmo dia lê do cache.

**Fase 5 — Agente + API de evaluations**
`agent.evaluate()`, scores buy/sell, endpoints `/evaluations/*`.
✅ Pronto quando: os dois exemplos de referência da secção 6 passam como testes; `POST /evaluations/run` sobre watchlist com 2 stocks cria 2 evaluations com details.

**Fase 6 — Frontend PWA**
As 5 páginas, ligadas à API real.
✅ Pronto quando: fluxo completo manual funciona — login → adicionar ticker → criar estratégia com 2 critérios → avaliar → ver feed com detalhe.

**Fase 7 — Scheduler + email + prod**
APScheduler, email resumo, `docker-compose.prod.yml` com Caddy, `.env.example` completo, README com passos de deploy no Hetzner (firewall ufw + SSH hardening documentados, não automatizados).
✅ Pronto quando: job pode ser disparado manualmente num teste (função isolada) e gera o email esperado (SMTP mockado).

---

## 11. Variáveis de ambiente (`.env.example`)

```
DATABASE_URL=postgresql+asyncpg://app:app@db:5432/investdb
JWT_SECRET=change-me
JWT_EXPIRES_HOURS=24
ALLOW_REGISTRATION=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SUMMARY_EMAIL_TO=
SCHEDULER_ENABLED=true
FINNHUB_API_KEY=
TWELVEDATA_API_KEY=
```

---

## 12. Seed data (para dev)

Script `backend/app/seed.py` (correr manualmente): cria utilizador `demo@benjamin.dev / demo1234`, adiciona AAPL, MSFT e GALP.LS à watchlist, e cria a estratégia "Value simples" do exemplo da secção 6.

---

## 13. Fora do MVP — planeado para depois (não implementar)

- Row Level Security no Postgres (quando multi-user)
- Refresh tokens + 2FA
- News/sentiment como categoria de indicadores
- Fila de jobs (Celery/RQ) com rate limiting de APIs externas
- Portfólio + transações
- Backups automatizados da BD
