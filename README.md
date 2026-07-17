# Benjamin 🐦

O teu companheiro de investimento: watchlist de ações + estratégias de scoring
configuráveis + agente determinístico que avalia, segundo os **teus** critérios,
quando comprar ou vender.

> Benjamin executa os critérios que tu defines — não é aconselhamento financeiro.

## Funcionalidades

- **Watchlist** — pesquisa por nome/ticker (Finnhub), sugestões rápidas dos tickers mais populares, notas e preços-alvo por ação.
- **Estratégias configuráveis** — cada estratégia é um conjunto de critérios (`métrica` + `operador` + `threshold` + `peso`), combinando indicadores técnicos e fundamentais. Cada métrica tem uma explicação curta no editor.
- **Agente determinístico** — calcula `buy_score`/`sell_score` (0–100) por ação a partir dos critérios ativos e recomenda BUY/SELL/HOLD (SELL tem prioridade quando ≥ 70).
- **Overview** — página inicial com resumo BUY/SELL/HOLD, separador "Sinais" com a watchlist reordenável manualmente (setas ▲▼) e separador "Notícias" (agregadas por ticker via Finnhub).
- **9 indicadores prontos a usar**: `PRICE_CLOSE`, `RSI_14`, `SMA_50`, `SMA_200`, `PE_RATIO`, `DIVIDEND_YIELD`, `EPS`, `DEBT_TO_EQUITY`, `MARKET_CAP` — adicionar um novo é só uma entrada no registry (`indicators_core.py`).
- **Resumo semanal por email** — scheduler (sábados 08:00 UTC) corre as estratégias ativas e envia um resumo por SMTP.
- **Tema claro/escuro** com toggle manual persistido, PWA instalável no telemóvel.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Alembic, APScheduler |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router |
| Dados de mercado | [Finnhub](https://finnhub.io) (preço, perfil, fundamentais, pesquisa, notícias) + [Twelve Data](https://twelvedata.com) (backfill de histórico) |
| Auth | JWT (PyJWT) + bcrypt |
| Infra local | Docker Compose |

## Arranque rápido (dev)

```bash
cp .env.example .env          # editar JWT_SECRET, FINNHUB_API_KEY e TWELVEDATA_API_KEY (grátis)
docker compose up --build     # api em http://localhost:8000 — migrations correm automaticamente
```

Chaves grátis: [finnhub.io](https://finnhub.io/register) e [twelvedata.com](https://twelvedata.com/) (Basic plan).

Popular a base de dados com um utilizador de demo (opcional):
```bash
docker compose exec api python -m app.seed   # demo@benjamin.dev / demo1234 + AAPL, MSFT, GALP.LS
```

Documentação interativa da API: http://localhost:8000/docs

Frontend em modo dev, fora do compose (hot reload mais rápido):
```bash
cd frontend
cp .env.example .env   # ajustar VITE_API_BASE_URL só se a API não estiver em localhost
npm install
npm run dev             # http://localhost:5173
```

## Testes

```bash
cd backend
pip install -e ".[test]"
pytest                                      # suite completa (API + núcleo)
python -m unittest tests.test_core_logic    # só o núcleo puro (sem dependências de API)
```

Ou, com tudo a correr em Docker:
```bash
docker compose exec api pytest
```

## Estrutura

```
backend/
  app/
    models/        # SQLAlchemy — Stock, WatchlistItem, StrategyTemplate/Item, Evaluation, ...
    routers/        # FastAPI — auth, watchlist, strategies, evaluations
    schemas/        # Pydantic (request/response)
    services/
      indicators_core.py   # cálculo puro de indicadores — testável isolado, sem BD
      agent_core.py        # scoring puro (buy/sell) — testável isolado
      indicators.py        # camada de cache/BD sobre indicators_core
      agent.py              # liga o agente à BD (grava Evaluation/EvaluationDetail)
      market_data.py        # ingestão Finnhub + Twelve Data
      email_service.py       # resumo semanal por SMTP
    scheduler.py     # APScheduler — job semanal
  alembic/versions/  # migrations
  tests/
frontend/
  src/
    pages/           # Overview, Login, Watchlist, Strategies, StrategyEditor, Feed
    components/      # NavBar, Layout, ScoreBadge, ThemeToggle, ...
    context/          # AuthContext, ThemeContext
    api/              # client.ts (wrapper fetch+JWT), types.ts
reference/schema.sql # schema de referência (espelha os models)
```

- `SPEC.md` — especificação completa, com fases e critérios de aceitação
- `CLAUDE.md` — convenções seguidas durante o desenvolvimento assistido por IA
- `HANDOFF.md` — histórico de decisões e estado de cada fase (contexto de continuação)

## Estado das fases (`SPEC.md` secção 10)

- [x] Fase 1 — Skeleton (Docker Compose, `/health`, Alembic)
- [x] Fase 2 — Auth + Watchlist CRUD
- [x] Fase 3 — Ingestão de dados (Finnhub + Twelve Data, idempotente)
- [x] Fase 4 — Indicadores (9, com cache em `indicator_values`)
- [x] Fase 5 — Agente + API de `evaluations`
- [x] Fase 6 — Frontend PWA (6 páginas, tema claro/escuro, Overview com sinais + notícias)
- [~] Fase 7 — Scheduler semanal + email resumo feitos; deploy de produção (Docker Compose + Caddy/HTTPS) por fazer

## Licença

MIT — ver [LICENSE](LICENSE).
