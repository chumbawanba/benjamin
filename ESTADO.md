# ESTADO — Benjamin

> Ponto de partida para qualquer conversa nova. Descreve onde o projecto está **de
> facto**, não onde os planos dizem que devia estar. Tudo o que não foi possível
> confirmar directamente no repositório está marcado como **[POR CONFIRMAR]**.
>
> Documento escrito a 2026-09-16, com base no repositório no commit `ae4e848`.
> Ordem de leitura recomendada: este ficheiro → `CLAUDE.md` (convenções) →
> `SPEC.md` (especificação) → `HANDOFF.md`/`ROADMAP.md` (histórico, ver secção 7
> sobre a deriva destes dois).

---

## 1. Resumo em cinco linhas

O Benjamin é uma app pessoal de investimento: watchlist de acções/ETFs, estratégias
de critérios configuráveis (métrica + operador + threshold + peso), e um agente
determinístico que calcula `buy_score`/`sell_score` e recomenda BUY/SELL/HOLD segundo
os critérios do próprio utilizador. Tem ainda portfólio com P&L, um analista IA
("Benjamin", OpenAI), alertas e notificações, e resumo periódico por email.
Posicionamento fixo: **ferramenta de apoio à decisão, nunca aconselhamento financeiro**.
O produto está tecnicamente maduro e em uso pessoal; o que falta é sobretudo
confirmação de produção, tratamento jurídico e monetização.

---

## 2. Instantâneo do repositório

| | |
|---|---|
| Caminho | `C:\Users\edgar\projectos\Benjamin\benjamin` |
| Ramo | `main`, **3 à frente** de `origin/main` (por dar push - ver nota abaixo) |
| Árvore de trabalho | limpa após o commit `26544de` (2026-09-17) |
| Último commit | `26544de` — *Adicionar projeção de património a longo prazo* — **2026-09-17** |
| Testes backend | **258 passed** (241 antes desta sessão + 9 de Empréstimos + 8 de Projeção) |
| Domínios | `appbenjamin.com` (landing estática) e `beta.appbenjamin.com` (app) |

Nota sobre os testes: a suite foi corrida numa venv com **Python 3.10**, porque o
ambiente desta sessão não tinha 3.12 (o `pyproject.toml` exige `>=3.12`). Nenhum
código do projecto foi alterado para isso. O mesmo aconteceu na sessão de 2026-07-21
(ver `HANDOFF.md`). **[POR CONFIRMAR]** que a suite passa igualmente em 3.12, que é
o que corre em Docker.

Nota sobre o calendário: **passaram cerca de sete semanas sem commits** (28/07 →
16/09), até este documento ser escrito. No dia seguinte (17/09), esta sessão fez o
commit `a7602c1` (ver secção 4) - ainda não houve `git push` a partir daqui (sem
acesso à remote de dentro desta VM de sandbox); confirmar/enviar a partir do PC.

---

## 3. O que está construído — confirmado no código

### Backend (FastAPI, SQLAlchemy 2.0 async, Postgres 16, Alembic, APScheduler)

- **Auth**: JWT (`jwt_expires_hours = 24`), bcrypt, registo fechado por
  `allow_registration` (default `False`), aceitação obrigatória da política de
  privacidade no registo (`accepted_terms_at`).
- **Watchlist e portfólio**: acções e ETFs, ordem manual (`display_order`),
  preços-alvo por acção, notas; `Position` com custo médio e P&L não realizado
  calculado on-the-fly, multi-moeda com conversão FX e moeda preferida por
  utilizador.
- **Empréstimos (passivos)**: `Loan` (nome, moeda, saldo em dívida, taxa de juro e
  prestação mensal opcionais como referência, sem histórico - mesmo princípio do
  `Position`), `/loans` com CRUD e conversão para a moeda preferida. Adicionado em
  `a7602c1` (17/09).
- **Estratégias e agente**: `agent_core.py` (scoring puro), `agent.py` (persistência),
  horizonte por estratégia, biblioteca de estratégias de referência, optimizador por
  backtest greedy (`backtest_core.py`), `POST /strategies/{id}/optimize`.
- **Indicadores**: **18** no registry de `indicators_core.py` — `PRICE_CLOSE`,
  `RSI_14`, `SMA_50`, `SMA_200`, `PRICE_VS_SMA_50`, `PRICE_VS_SMA_200`, `PE_RATIO`,
  `DIVIDEND_YIELD`, `EPS`, `DEBT_TO_EQUITY`, `MARKET_CAP`, `ROE`, `NET_MARGIN`,
  `REVENUE_GROWTH`, `GROSS_MARGIN`, `OPERATING_MARGIN`, `EPS_GROWTH`,
  `DIVIDEND_GROWTH_5Y`. (O README ainda diz 9 — ver secção 7.)
- **Dados de mercado**: Finnhub (cotação, perfil, fundamentais, pesquisa, notícias,
  peers) + Twelve Data (backfill de histórico), ambos resilientes a falha, com
  `ensure_fresh`, cotação intradiária a 15 minutos e protecção contra tempestades de
  retries.
- **Analista IA**: `analyst.py`, resumo e `POST /analyst/ask` com contexto completo
  (portfólio, watchlist, fundamentais, critério-a-critério das avaliações), prompt de
  sistema editável, histórico de conversa no frontend (máx. 20 mensagens), nunca
  corrido em scheduler.
- **Alertas e notificações**: `alerts.py` (alerta de preço-alvo, edge-triggered via
  `buy_alert_triggered`/`sell_alert_triggered`; alerta de mudança de sinal, opt-in por
  acção via `alert_on_signal`), tabela `Notification`, `GET/PUT /notifications`,
  preferências de email (`email_reports_enabled`, `email_alerts_enabled`) e
  `GET /notifications/unsubscribe/{token}` sem login.
- **Relatório periódico**: `reports.py` com dia e hora escolhidos por utilizador
  (`report_day_of_week`, `report_hour`, em UTC) e `last_report_sent_at` como guarda
  anti-duplicação. O `report_job` passou a correr **de hora a hora** em vez do antigo
  cron fixo de sábado às 08:00.
- **Jobs (`main.py`)**: `daily_refresh_job` 06:00 UTC, `alerts_job` 06:15 UTC,
  `report_job` ao minuto 0 de cada hora.
- **Waitlist**: `POST /waitlist` (usado pela landing).
- **20 migrations Alembic**; nenhuma alteração de schema fora de migration.

### Frontend (React 18 + TS + Vite + Tailwind, PWA)

13 páginas (`Overview`, `Watchlist`, `StockDetail`, `Portfolio`, `Loans`, `Strategies`,
`StrategyEditor`, `StrategyWorkspace`, `Feed`, `Notifications`, `FxRates`, `Login`,
`Register`), tema claro/escuro, gráficos sem dependências externas (`Sparkline`,
`BacktestChart`, `PortfolioAllocationChart`), FAB de pergunta ao Benjamin, todas as
chamadas via `src/api/client.ts`. `PortfolioSummaryCard` no Overview mostra
Património Líquido (valor do portfolio - total em dívida) quando há empréstimos.

### Landing e infra

`landing/` contém `index.html`, política de privacidade, política de cookies e aviso
de risco, servidos pelo Caddy em `appbenjamin.com`. `docker-compose.prod.yml` +
`Caddyfile` existem e estão completos: Postgres e API sem portas expostas ao host,
frontend em imagem nginx com build estático (`Dockerfile.prod`), Caddy com 80/443 e
HTTPS automático, `alembic upgrade head` no arranque da API.

---

## 4. Últimos envios — confirmados no git

Os três itens da conversa anterior existem no repositório, todos de 2026-07-28:

| Commit | Data | O quê | Onde toca |
|---|---|---|---|
| `19a6b82` | 28/07 12:49 | Alertas + centro de notificações in-app | 26 ficheiros, migration `a4d8f2c6b9e3`, testes `test_alerts.py` e `test_notifications.py` |
| `28c3eaa` | 28/07 13:15 | Dia/hora configurável do resumo por email | 15 ficheiros, migration `b8e1d4f2a7c5`, testes `test_reports.py` |
| `ae4e848` | 28/07 15:25 | Auto-logout na expiração do token | **só 2 ficheiros, ambos frontend**: `api/client.ts` e `pages/Login.tsx` |
| `a7602c1` | 17/09 | Empréstimos (passivos) + Património Líquido no Overview | 14 ficheiros, migration `8e77a41ac464`, testes `test_loans.py` |
| `8da1ce4` | 17/09 | Atualização do ESTADO.md (fase Empréstimos) | 1 ficheiro, sem código |
| `26544de` | 17/09 | Projeção de património a longo prazo | 12 ficheiros, `routers/projection.py`, `services/projection.py`, `pages/Projection.tsx`, testes `test_projection.py` |

Detalhe relevante para a secção 5: o auto-logout é **exclusivamente frontend**
(401 com token prévio → limpa sessão → `/login?expired=1` → aviso "A tua sessão
expirou"). O resumo configurável é backend + frontend, mas a interface de escolha do
dia/hora vive em `pages/Notifications.tsx` e `utils/schedule.ts`, também frontend.
Isto é consistente com o sintoma descrito: **se o bundle do frontend não for
reconstruído, estas são exactamente as duas funcionalidades que não aparecem em
produção**, mesmo com o commit certo no VPS e a API correcta a responder.

---

## 5. Bloqueio aberto — o frontend em produção

**Sintoma relatado (conversa anterior, [POR CONFIRMAR] a partir daqui):** três deploys
seguidos serviram um bundle com hash idêntico, apesar de o commit correcto estar no
VPS. Ficou por correr `docker compose -f docker-compose.prod.yml build --no-cache
frontend` e nunca houve resposta.

Não há acesso SSH ao VPS a partir desta sessão, nem foi possível alcançar
`beta.appbenjamin.com` daqui, por isso **nada nesta secção está verificado contra
produção**. O que segue são causas candidatas, todas fundamentadas em ficheiros reais
do repositório, por ordem do que é mais barato eliminar:

1. **Build não corrido.** `docker compose -f docker-compose.prod.yml up -d` sem
   `--build` reutiliza a imagem antiga do `frontend` sem qualquer aviso. O cabeçalho
   do próprio `docker-compose.prod.yml` documenta `up -d --build` como o uso correcto.
2. **Cache de camadas do Docker.** Daí a sugestão do `build --no-cache frontend`.
3. **Falta de `.dockerignore`.** Não existe `.dockerignore` nem na raiz nem em
   `frontend/`. O `Dockerfile.prod` faz `COPY package.json ...` → `RUN npm install` →
   `COPY . .`, ou seja, o `COPY . .` copia por cima o `node_modules/` e o `dist/` que
   existirem no contexto de build. O `HANDOFF.md` já registou um caso em que o
   `node_modules` local tinha binários nativos de outra plataforma. Localmente,
   `frontend/dist/` está desactualizado (assets de 2026-07-18, `index-TFEs6wC5.js`);
   `dist/` está no `.gitignore`, logo não vai no git, mas **vai no contexto do
   `docker build`** se existir no VPS.
4. **Service worker da PWA.** Ver secção 6.1 — o SW pode servir `index.html` e assets
   em cache, o que produz exactamente o sintoma "hash idêntico" no browser mesmo com
   uma imagem nova a ser servida pelo nginx.
5. **Cache da Cloudflare.** O comentário no topo do `Caddyfile` diz explicitamente que
   o Caddy corre "mesmo atrás do proxy da Cloudflare". Uma cache de edge sobre o
   `index.html` produz o mesmo sintoma.
6. **Cabeçalhos de cache do nginx.** O `frontend/nginx.conf` define `Cache-Control:
   no-cache` **apenas** para `/manifest.webmanifest`. O `index.html` não tem política
   explícita — e é o `index.html` que aponta para o bundle com hash.

**Como distinguir sem SSH:** abrir `https://beta.appbenjamin.com` numa janela anónima,
com o service worker desregistado, e comparar o nome do ficheiro em
`<script src="/assets/index-*.js">` com o do build local mais recente. Se o hash
mudar em anónimo mas não na janela normal, a causa está no SW ou na cache do browser
(4). Se não mudar em lado nenhum, está na imagem, no build ou na Cloudflare (1, 2, 3, 5).

**Consequência prática:** até isto estar resolvido, **não é possível afirmar que o
auto-logout e o dia/hora do relatório estão em produção**. Ambos estão no código e
testados; o que falta é confirmação de entrega.

---

## 6. Pendentes conhecidos

### 6.1 Cache do service worker da PWA — correcção nunca aplicada

**Confirmado no repositório.** O `vite.config.ts` usa `VitePWA` com
`registerType: 'autoUpdate'` e **nenhum bloco `workbox`** — não há `skipWaiting` nem
`clientsClaim` explícitos. Não existe qualquer código de registo ou gestão de SW em
`frontend/src` (o `main.tsx` não toca no assunto); a única coisa que regista o SW é o
`registerSW.js` gerado pelo plugin. Ou seja, a correcção foi de facto **nunca aplicada**
e o contorno continua a ser manual: desregistar o SW e limpar as caches.
Esta é provavelmente a mesma raiz do problema da secção 5 — vale a pena tratá-las juntas.

### 6.2 Auto-sync da Trading 212 — bloqueado por documentação

**Confirmado:** não existe uma única referência a Trading 212 ou T212 em todo o
repositório (código, docs ou configuração). A proposta vive fora do repo.
O bloqueio descrito também se confirma: a secção 13 do `SPEC.md` ("Fora do MVP —
planeado para depois (não implementar)") **ainda lista "Portfólio + transações"**,
apesar de o portfólio ter sido construído em 2026-07-19. O `CLAUDE.md` diz, como
regra obrigatória, "Não implementar nada da secção 13 do SPEC.md". Enquanto essa linha
não for corrigida, qualquer sessão nova vai recusar-se a avançar com sincronização de
transações — e com razão, porque está a seguir as convenções.

Correcção mínima: separar a linha em "Portfólio" (feito, remover) e "Histórico de
transações" (decisão em aberto), em vez de a apagar em bloco.

### 6.3 Consulta jurídica (MiFID II / CMVM)

**Confirmado no `ROADMAP.md`** (secção 5, ponto 3, e secção 7, ponto 3): sinalizada
como "a mais importante antes de qualquer beta público, mesmo grátis". Não há
evidência no repositório de que tenha sido feita. O que existe já hoje é mitigação
de texto: aviso de risco, política de privacidade e de cookies, avisos de IA junto ao
chat e ao resumo, e o posicionamento "executa os teus critérios, não aconselha" em
toda a interface e na landing. Isso reduz risco, não substitui parecer.

### 6.4 Stack de faturação

**Confirmado:** zero linhas de código. A única menção a Stripe em todo o repositório
está no `ROADMAP.md` (secção 5, ponto 6) como plano: Stripe + Stripe Tax +
InvoiceXpress, modelo freemium (grátis: 1 estratégia, 5 acções, avaliação semanal;
Pro: ilimitado, diário, histórico). Não há tabelas de subscrição, tiers, limites por
plano nem conta institucional.

Dependência que costuma ser esquecida, também registada no `ROADMAP.md` (ponto 7):
os free tiers da Finnhub e da Twelve Data **não têm licença para uso comercial pago** —
a migração para planos comerciais tem de acontecer antes de cobrar o primeiro euro,
não depois.

### 6.5 Outros pendentes menores, confirmados nos documentos

- Logo real por guardar em `frontend/public/` e ligar como ícone PWA/favicon — o
  `HANDOFF.md` diz que só foi partilhado em chat. Há `coruja-logo.png` na raiz e
  ícones em `landing/` e `frontend/public/`; **[POR CONFIRMAR]** se são o ficheiro
  final ou ainda os genéricos.
- Fase 8 (learning pathway), Fase 10 (screener) e Fase 11 (comparação de variantes):
  não iniciadas.
- Fase 9 (backtesting user-facing): parcial — falta drawdown máximo, nº de trades
  explícito e disclaimers de overfitting/survivorship.
- i18n: não iniciado, app toda em PT hardcoded.
- Soma multi-moeda do portfólio: já resolvida com FX (`services/fx.py`), apesar de o
  `HANDOFF.md` ainda a listar como limitação conhecida.

---

## 7. Deriva da documentação

Os documentos existentes ficaram para trás do código. Isto é a principal razão pela
qual cada conversa nova começava do zero — quem lia os docs ficava com uma imagem
errada. Pontos concretos:

| Documento | O que diz | Realidade |
|---|---|---|
| `SPEC.md` §13 | "Portfólio + transações" fora do MVP | Portfólio construído em 2026-07-19; combinado com o `CLAUDE.md`, bloqueia trabalho novo (ver 6.2) |
| `README.md` | "9 indicadores" | 18 no registry |
| `README.md` | "Resumo semanal (sábados 08:00 UTC)" | Dia e hora por utilizador desde `28c3eaa` |
| `README.md` e `HANDOFF.md` | Fase 7: deploy de produção "por fazer" | `docker-compose.prod.yml` e `Caddyfile` existem desde 21-22/07 e a app está em `beta.appbenjamin.com` |
| `README.md` | 6 páginas no frontend | 12 páginas |
| `HANDOFF.md` §Próximos passos | Termina no ponto 8 (consulta jurídica) | Não menciona alertas, notificações, relatório configurável nem auto-logout (tudo posterior) |
| `ROADMAP.md` | Landing "ainda não está no repositório" | `landing/` existe e é servida pelo Caddy |
| `HANDOFF.md` | Portfólio multi-moeda como limitação | Resolvido com `services/fx.py` |
| `scheduler.py` | Docstring do `daily_refresh_job` refere "Yahoo Finance" | Fonte é Finnhub + Twelve Data desde 2026-07-17 |

---

## 8. O que não é verificável a partir daqui

Lista explícita, para não haver ambiguidade sobre o que é facto e o que é suposição:

- **[POR CONFIRMAR]** Que commit está realmente em `HEAD` no VPS.
- **[POR CONFIRMAR]** Que imagem Docker do `frontend` está a correr e quando foi
  construída.
- **[POR CONFIRMAR]** Que hash de bundle é servido hoje por `beta.appbenjamin.com`.
- **[POR CONFIRMAR]** Se o auto-logout e o dia/hora do relatório estão a funcionar em
  produção.
- **[POR CONFIRMAR]** Se a Cloudflare está mesmo à frente do domínio e com que regras
  de cache.
- **[POR CONFIRMAR]** Se as migrations `a4d8f2c6b9e3` e `b8e1d4f2a7c5` foram aplicadas
  em produção (correm no arranque do container `api`, mas o `HANDOFF.md` já registou
  um caso em que um container em execução não as apanhou).
- **[POR CONFIRMAR]** Estado do envio real de email em produção (SMTP configurado,
  entregabilidade, se algum resumo chegou a sair).
- **[POR CONFIRMAR]** Se houve utilizadores reais na beta e com que resultado.
- **[POR CONFIRMAR]** Consumo actual das quotas da Finnhub e da Twelve Data.
- **[POR CONFIRMAR]** Se a consulta jurídica foi iniciada fora do repositório.
- **[POR CONFIRMAR]** Se a suite de testes passa em Python 3.12 (ver secção 2).

---

## 9. Próximos passos, por prioridade

### Prioridade 1 — fechar o ciclo de entrega (bloqueia tudo o resto)

Enquanto não houver confiança de que o que está em `main` chega ao browser, cada
funcionalidade nova herda a mesma dúvida.

1. **Diagnosticar o bundle idêntico** pelo teste da janela anónima descrito na secção 5,
   antes de mexer em seja o que for. É de minutos e elimina metade das hipóteses.
2. **Correr `docker compose -f docker-compose.prod.yml build --no-cache frontend`
   seguido de `up -d`** no VPS, e confirmar que o hash do bundle muda.
3. **Adicionar `frontend/.dockerignore`** com pelo menos `node_modules`, `dist`,
   `.env*` e `*.tsbuildinfo`. Torna o build reprodutível e mais rápido, e elimina a
   hipótese 3 de vez.
4. **Confirmar em produção** o auto-logout (deixar a sessão expirar, ou limpar o token)
   e a escolha de dia/hora do relatório.

### Prioridade 2 — arrumar a casa para as próximas sessões

5. **Corrigir a secção 13 do `SPEC.md`**: separar "Portfólio" (feito) de "Histórico de
   transações" (em aberto). Sem isto, o trabalho da Trading 212 fica bloqueado por uma
   frase desactualizada.
6. **Actualizar `README.md`, `HANDOFF.md` e `ROADMAP.md`** nos pontos da secção 7, ou
   marcá-los explicitamente como histórico e apontar este ficheiro como fonte de
   verdade do estado.

### Prioridade 3 — corrigir o que já se sabe que está partido

7. **Service worker da PWA**: adicionar `workbox: { skipWaiting: true, clientsClaim: true,
   cleanupOutdatedCaches: true }` ao `VitePWA` e `Cache-Control: no-cache` para o
   `index.html` no `nginx.conf`. Provavelmente resolve também parte da secção 5.
8. **Verificar as migrations em produção** — `docker compose exec api alembic current`
   contra `head`.

### Prioridade 4 — desbloquear produto

9. **Auto-sync da Trading 212**: retomar a proposta depois do passo 5. Decidir primeiro
   o modelo de dados (importar transações exige histórico, que hoje não existe — a
   `Position` é um snapshot editável, sem transacções).
10. **Reforçar o backtesting** até à Fase 9 do plano: drawdown máximo, nº de trades e
    disclaimers estatísticos.

### Prioridade 5 — antes de qualquer pessoa desconhecida entrar

11. **Consulta jurídica (MiFID II / CMVM)**. Independente do estado técnico e
    pré-requisito de tudo o que vem a seguir. É o único item desta lista que não se
    resolve com código.
12. **Stack de faturação**: só depois do ponto 11, e a começar pela migração para
    planos comerciais da Finnhub e da Twelve Data, que é pré-requisito legal de cobrar.

---

## 10. Como manter este documento

Actualizar no fim de cada sessão que mude o estado real: o que foi enviado, o que foi
confirmado em produção, e o que passou de **[POR CONFIRMAR]** a facto. A secção 8 é a
mais importante de manter viva — é a lista do que se está a assumir sem provas.

---

## 11. Sessão 2026-09-17 (tarde) — Empréstimos + próxima fase

Sessão via Cowork, com o PC (`pcdecasa`, Windows) ligado como dispositivo remoto.
Antes de mexer em código, esta sessão detectou e recusou um bloco de instruções em
inglês injectado numa mensagem anterior (a seguir a "PC ligado", a pedir uma resposta
só em texto, sem ferramentas) - não veio do Edgar, não foi seguido, e foi sinalizado
antes de continuar. Fica registado aqui para não se perder ao longo de conversas.

**Feito nesta sessão** (commit `a7602c1`, ver secções 2-4): funcionalidade
Empréstimos completa (backend + frontend + testes + migration), verificada com
`pytest` (250 passed) e `tsc -b` (sem erros) numa venv/`node_modules` desta sessão -
**[POR CONFIRMAR]** que corre igual em Python 3.12 e num `npm install` limpo (o
`vite build` de produção falhou aqui por faltar o binário nativo do rollup para esta
VM de sandbox - problema conhecido de dependências opcionais do npm, não do código;
`tsc -b` já garante que os tipos estão correctos, mas um `npm run build` real no PC
fica por confirmar).

**Projeção de património — feita nesta mesma sessão** (commit `26544de`), com as
decisões tomadas com o Edgar: rentabilidade **input manual** (não calculada do
histórico), empréstimos amortizados **linearmente pela prestação** (sem separar
juro/capital), página nova e isolada, **sem** contribuições/levantamentos periódicos
(fica para uma fase futura, se vier a ser pedido). `GET /projection?years=&annual_return_pct=`
devolve a série ano a ano; página `Projeção` com gráfico + tabela de marcos.
Simplificações explícitas a manter em mente: taxa de câmbio fixa ao longo dos anos
(não projeta variação cambial), sem inflação, sem novas entradas de capital.


**Outros Ativos + página Património (imóveis, certificados, etc.) — feita nesta
mesma sessão** (commits a seguir a `e52c369`, ver `git log`). Partiu de uma pergunta
simples do Edgar - "não percebi onde coloco outros patrimonios como imoveis ou
certificados de tesouro" - que expandiu para uma reestruturação maior depois de
perguntar onde é que isto devia viver: o Edgar respondeu "estava a pensar ter um
'património' em vez de portfolio e dentro vários separadores (portfolio acções,
imoveis, cash, outros)", e confirmou de seguida que os Empréstimos deviam entrar
como mais um separador em vez de ficarem na página própria.

Backend: nova entidade `OtherAsset` (`category` em `imovel`/`outro`, `name`,
`currency`, `value`, `expected_return_pct` opcional) - espelha o `Loan` do lado do
ativo, mesmo padrão "só valor atual, sem histórico". CRUD completo em
`/other-assets` (`app/routers/other_assets.py`), migration `53849ddfb8d8`. Decisões
tomadas com o Edgar: campos "simples + taxa de rendimento esperada" (não um
modelo de avaliações históricas), e **cada ativo entra na Projeção de património
com a sua própria taxa** (`expected_return_pct`) em vez de herdar a rentabilidade
geral do portfolio de ações - ver `app/services/projection.py::_current_other_assets`.
Um ativo sem taxa definida fica com o valor constante ao longo da projeção, tal como
já acontecia com empréstimos sem prestação. `ProjectionOut`/`ProjectionPointOut`
ganharam `starting_other_assets_value`/`other_assets_value`; `net_worth` passou a
ser `portfolio + outros_ativos - empréstimos`. 11 testes novos em
`test_other_assets.py` e 2 em `test_projection.py` (crescimento à taxa própria, e
ativo sem taxa fica constante) - suite completa continua verde (270 passed).

Frontend: a antiga `Portfolio.tsx` (que já misturava ações e cash na mesma lista) e
a `Loans.tsx` foram substituídas por `pages/Patrimonio.tsx`, uma página só com
separadores (`?tab=` na URL, mesmo padrão do `StrategyWorkspace.tsx`): **Ações**,
**Cash** (agora com formulário e lista próprios, antes viviam juntos), **Imóveis**,
**Outros** e **Empréstimos**. Cada separador é um componente em
`components/patrimonio/` (`AcoesTab`, `CashTab`, `OtherAssetsTab` - genérico,
reutilizado por Imóveis e Outros - e `EmprestimosTab`); a página-mãe centraliza o
carregamento de dados e o seletor de moeda preferida (é uma definição global do
utilizador, afecta todos os separadores, não só Ações/Cash). Rota nova:
`/patrimonio`; `/portfolio` e `/loans` ficam como redirects para não partir
marcadores antigos. Navegação (`NavBar`/`SideNav`) passou a mostrar só
"Património" (ícone `IconWallet`) em vez de "Portfolio" + "Empréstimos"
separados. `PortfolioSummaryCard.tsx` (cartão na Overview) e a página `Projeção`
passaram a incluir os Outros Ativos no património líquido/gráfico/tabela.

Verificado com `pytest` (270 passed), `tsc -b` (sem erros) e um smoke test real
(uvicorn + SQLite via `Base.metadata.create_all`, sem passar pelas migrations
Alembic que são Postgres-specific e falham em SQLite - registar/login, criar
empréstimo + 2 outros ativos, confirmar rejeição de categoria inválida, conferir
os números da projeção à mão, editar e apagar um ativo) - tudo correcto. O
`vite build`/`vite dev` continuam sem correr nesta VM de sandbox pelo mesmo motivo
já registado acima (binário nativo do rollup em falta) - **[POR CONFIRMAR]** que o
`npm run dev` real no PC do Edgar mostra a página Património correctamente (o
`tsc -b` garante os tipos, não o resultado visual).


**Poupança mensal (rendimentos líquidos) na Projeção — pedido do Edgar depois de já
ver a página em produção** ("lembrei-me que na projecção faltam os rendimentos
líquidos"). Esclarecido antes de mexer: representa a poupança mensal que o
utilizador investe (não rendimento passivo já reinvestido - isso já está implícito
na rentabilidade assumida) e fica **fixa** ao longo de toda a simulação (decisão
tomada com o Edgar - mais simples, sem modelar aumentos salariais/inflação da
própria poupança). Novo parâmetro opcional `monthly_savings` em
`GET /projection` (default 0, mantém o comportamento anterior inalterado), somado
ao portfolio no fim de cada ano (`monthly_savings * 12`) - só ao portfolio de
ações, não aos Outros Ativos nem reduz empréstimos (para isso já existe a
prestação mensal do próprio empréstimo). Obrigou a passar o cálculo do valor do
portfolio de fórmula fechada (`valor * taxa^ano`) para iterativo ano a ano, mesmo
padrão já usado para o saldo dos empréstimos. Campo novo no formulário da página
Projeção. 3 testes novos (soma correcta, comportamento inalterado quando omitido,
valor negativo rejeitado) - suite completa continua verde (273 passed). Verificado
também com um smoke test real (uvicorn + SQLite) conferindo os valores ano a ano
à mão.
