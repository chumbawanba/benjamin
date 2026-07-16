# Benjamin 🐦

O teu companheiro de investimento: watchlist + checklists configuráveis + agente
determinístico que avalia quando os **teus** critérios indicam comprar ou vender.

> Benjamin executa os critérios que tu defines — não é aconselhamento financeiro.

## Arranque rápido (dev)

```bash
cp .env.example .env          # editar JWT_SECRET no mínimo
docker compose up --build     # api em http://localhost:8000, migrations automáticas
```

Gerar a migration inicial (primeira vez, com a BD a correr):
```bash
docker compose exec api alembic revision --autogenerate -m "initial schema"
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed   # demo@local / demo1234 + AAPL, MSFT, GALP.LS
```

Documentação interativa da API: http://localhost:8000/docs

## Testes

```bash
cd backend
pip install -e ".[test]"
pytest                        # suite completa (API + núcleo)
python -m unittest tests.test_core_logic   # só o núcleo puro (sem dependências de API)
```

## Estrutura

- `SPEC.md` — especificação completa com fases e critérios de aceitação
- `CLAUDE.md` — convenções para desenvolvimento com Claude Code
- `backend/app/services/indicators_core.py` + `agent_core.py` — lógica pura (testável isolada)
- `backend/app/services/` — market data (yfinance), indicadores com cache, agente, email
- `reference/schema.sql` — schema de referência original

## Estado das fases (SPEC secção 10)

- [x] Fase 1 — Skeleton (docker compose, /health, alembic)
- [x] Fase 2 — Auth + Watchlist CRUD (+ testes de isolamento entre utilizadores)
- [x] Fase 3 — Ingestão de dados (yfinance, gravação idempotente)
- [x] Fase 4 — Indicadores (6 indicadores MVP + cache em indicator_values)
- [x] Fase 5 — Agente + API de evaluations (exemplos de referência como testes)
- [x] Fase 6 — Frontend PWA (5 páginas ligadas à API; `npm install` ainda não corrido/verificado)
- [x] Fase 7 (parcial) — Scheduler semanal + email resumo (deploy prod por fazer)

## Frontend (dev)

```bash
cd frontend
cp .env.example .env   # ajustar VITE_API_BASE_URL se necessário
npm install
npm run dev             # http://localhost:5173
```
