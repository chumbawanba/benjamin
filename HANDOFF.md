# HANDOFF — Benjamin app development

> Documento de contexto para continuar o desenvolvimento (Cowork / Claude Code).
> Ler primeiro SPEC.md (especificação) e CLAUDE.md (convenções).

## O que é o Benjamin
App pessoal de investimento: watchlist de ações + checklists de critérios
configuráveis + agente determinístico que calcula buy_score e sell_score (0-100)
e recomenda BUY/SELL/HOLD segundo os critérios do próprio utilizador.
Posicionamento: ferramenta de apoio à decisão, NÃO aconselhamento financeiro.

## Estado atual (o que já está feito)
Fases do SPEC secção 10:
- [x] Fase 1 — Skeleton: docker-compose (api+postgres), FastAPI, /health, scaffold Alembic
- [x] Fase 2 — Auth (JWT, bcrypt, registo fechado por env var) + Watchlist CRUD
- [x] Fase 3 — Ingestão yfinance (preços 1y + fundamentais), gravação idempotente, ensure_fresh()
- [x] Fase 4 — 6 indicadores MVP (PRICE_CLOSE, RSI_14, SMA_50, SMA_200, PE_RATIO, DIVIDEND_YIELD) com cache em indicator_values
- [x] Fase 5 — Agente (buy/sell scores separados, SELL prioridade ≥70) + endpoints /evaluations
- [x] Fase 6 — Frontend PWA (React+Vite+TS+Tailwind), 5 páginas (Login, Watchlist, Checklists,
  ChecklistEditor, Feed) ligadas à API real via `src/api/client.ts`. `npm install`/`npm run dev`
  ainda NÃO foram corridos neste ambiente (sem rede) — validar localmente.
- [~] Fase 7 — Scheduler APScheduler (sáb 08:00 UTC) + email resumo FEITOS; docker-compose.prod.yml com Caddy e README de deploy Hetzner POR FAZER

## Validação (sessão 2026-07-16, sandbox sem acesso a PyPI/npm/Docker)
- Núcleo puro (indicators_core + agent_core): 16 testes VERDES (unittest, corridos novamente)
- `email_service` (build_summary_html + send_summary, 3 testes): VERDES, validados por execução
  direta com stub de `app.config` (pydantic não instalável no sandbox)
- Suite pytest da API (auth, watchlist, checklists, evaluations — 14 testes): NÃO executável
  neste sandbox (sem FastAPI/SQLAlchemy/httpx instaláveis, sem Docker, sem acesso à rede além de
  docs.claude.com/support.claude.com). Revista manualmente linha a linha (routers, models, schemas,
  services) contra as asserções dos testes — nenhum bug encontrado, mas PRECISA de ser corrida
  localmente para confirmação: `cd backend && pip install -e ".[test]" && pytest`
- Frontend (Fase 6): escrito por inteiro mas nunca compilado/executado — correr
  `cd frontend && npm install && npm run dev` localmente e validar o fluxo manual da secção 10
  do SPEC.md antes de dar a fase por fechada

## Passos de arranque local
1. cp .env.example .env  (definir JWT_SECRET)
2. docker compose up --build
3. docker compose exec api alembic revision --autogenerate -m "initial schema"
4. docker compose exec api alembic upgrade head
5. docker compose exec api python -m app.seed   → demo@local / demo1234

## Decisões já tomadas (não reabrir sem razão)
- Nome: Benjamin (com n)
- Stack fechada no SPEC.md secção 2 (yfinance, PWA, APScheduler, SMTP, JWT simples)
- Fora do MVP: SPEC.md secção 13 (RLS, refresh tokens, news, portfólio, Celery...)
- Deploy alvo: Hetzner CX22 + Caddy + ufw (detalhado na conversa de arquitetura)

## Próximos passos por ordem
1. Correr `pytest` localmente (backend) e corrigir eventuais falhas na suite de API
2. Correr `npm install && npm run dev` (frontend) e validar o fluxo manual completo:
   login → adicionar ticker → criar checklist com 2 critérios → avaliar → ver feed com detalhe
3. Fase 7 restante: docker-compose.prod.yml + Caddy + guia de deploy
4. Gerar e commitar a migration inicial do Alembic
