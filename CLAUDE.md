# CLAUDE.md — Convenções do projeto

## Contexto
App de watchlist de ações + estratégias configuráveis + agente determinístico de avaliação.
A especificação completa está em `SPEC.md` — segue-a. Implementação por fases, na ordem da secção 10.

## Regras obrigatórias

### Workflow
- Trabalhar uma fase de cada vez. Não avançar para a fase seguinte sem os critérios de aceitação da atual cumpridos.
- Correr `pytest` (em `backend/`) antes de dar qualquer fase por concluída. Testes vermelhos = fase não concluída.
- Ao terminar uma fase, resumir o que foi feito e o que falta, sem começar automaticamente a próxima.

### Backend
- Python 3.12, FastAPI, SQLAlchemy 2.0 **async** (sintaxe 2.0: `select()`, sem legacy Query API).
- Todas as datas/timestamps em **UTC**. Nunca usar `datetime.now()` sem timezone — usar `datetime.now(timezone.utc)`.
- `user_id` vem **sempre** do JWT validado, nunca do body/query do pedido.
- Recursos de outro utilizador devolvem **404**, não 403.
- Toda a lógica de negócio vive em `app/services/` — routers só validam input e chamam services.
- Migrations sempre via Alembic; nunca `create_all()` fora dos testes.
- Finnhub/Twelve Data: **nunca** chamados diretamente nos testes — sempre mockados (`_finnhub_get`/`_twelvedata_get`).

### Dependências
- Não adicionar dependências novas sem necessidade clara; preferir stdlib e o que já está no `pyproject.toml`.
- Fixar versões (pin exato) no `pyproject.toml`.
- Não usar ta-lib (instalação frágil) — indicadores calculados com pandas.

### Testes
- pytest + httpx AsyncClient; BD de teste isolada (schema criado/destruído por sessão de teste).
- Cada endpoint novo tem pelo menos: caso de sucesso, caso sem auth, caso de isolamento entre utilizadores (quando aplicável).
- Os dois exemplos de referência do agente (SPEC.md secção 6) são testes obrigatórios.

### Frontend
- React 18 + TypeScript + Vite + Tailwind. Mobile-first.
- Sem bibliotecas de state management (Redux, etc.) — useState/useContext chegam.
- Todas as chamadas à API passam por `src/api/client.ts` (wrapper único com JWT).

### Segurança
- Segredos só em variáveis de ambiente; `.env` está no `.gitignore` e nunca é commitado.
- Passwords com bcrypt. JWT com expiração.
- Em `docker-compose` (dev): porta da BD mapeada só para `127.0.0.1`. Porta da API aberta na
  rede local (`8000:8000`, sem restrição a `127.0.0.1`) a pedido explícito, para testar no
  telemóvel — CORS via `allow_origin_regex` restrito a `localhost`/IPs privados (192.168.x.x,
  10.x.x.x), nunca aberto à internet. Em produção (`docker-compose.prod.yml`, Fase 7) isto muda
  para Caddy + HTTPS na frente, sem expor a API diretamente.

### O que NÃO fazer
- Não implementar nada da secção 13 do SPEC.md (fora do MVP), mesmo que pareça útil.
- Não criar abstrações "para o futuro" — o código mais simples que cumpre a fase atual.
- Não alterar o schema sem migration Alembic correspondente.
