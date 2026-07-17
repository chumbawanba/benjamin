-- ============================================================
-- SCHEMA: App Watchlist + Estratégias + Agente de Avaliação
-- ============================================================

-- ---------- 1. UTILIZADORES ----------
CREATE TABLE users (
    id              UUID PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    name            VARCHAR(255),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ---------- 2. AÇÕES (dados mestre, partilhados por todos os users) ----------
CREATE TABLE stocks (
    id              UUID PRIMARY KEY,
    ticker          VARCHAR(20) UNIQUE NOT NULL,   -- ex: AAPL, GALP.LS
    name            VARCHAR(255),
    exchange        VARCHAR(50),                    -- ex: NASDAQ, EURONEXT LISBON
    sector          VARCHAR(100),
    currency        VARCHAR(10),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ---------- 3. WATCHLIST ----------
CREATE TABLE watchlist_items (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    stock_id        UUID REFERENCES stocks(id),
    target_buy_price   DECIMAL(12,4),
    target_sell_price  DECIMAL(12,4),
    notes           TEXT,
    added_at        TIMESTAMP DEFAULT NOW(),
    display_order   INTEGER NOT NULL DEFAULT 0,     -- ordem manual definida pelo utilizador (Overview)
    UNIQUE(user_id, stock_id)
);

-- ---------- 4. ESTRATÉGIAS (templates configuráveis) ----------
CREATE TABLE strategy_templates (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,          -- ex: "Estratégia Value", "Swing Trade"
    description     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Cada item da estratégia é uma regra configurável, não código fixo
CREATE TABLE strategy_items (
    id                  UUID PRIMARY KEY,
    template_id         UUID REFERENCES strategy_templates(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,        -- ex: "RSI sobrevendido"
    category            VARCHAR(50),                  -- technical | fundamental | sentiment | news
    metric              VARCHAR(100),                 -- ex: "RSI_14", "PE_RATIO", "NEWS_SENTIMENT"
    operator            VARCHAR(20),                  -- <, >, <=, >=, ==, between
    threshold_value     DECIMAL(12,4),
    threshold_value_max DECIMAL(12,4),                -- usado quando operator = between
    weight              DECIMAL(5,2) DEFAULT 1.0,      -- importância no score final (slider 0-100)
    direction           VARCHAR(10),                  -- 'buy_signal' | 'sell_signal'
    is_active           BOOLEAN DEFAULT TRUE,
    display_order       INT
);

-- ---------- 5. DADOS DE MERCADO (cache) ----------
CREATE TABLE price_snapshots (
    id              UUID PRIMARY KEY,
    stock_id        UUID REFERENCES stocks(id),
    date            DATE NOT NULL,
    open            DECIMAL(12,4),
    high            DECIMAL(12,4),
    low             DECIMAL(12,4),
    close           DECIMAL(12,4),
    volume          BIGINT,
    UNIQUE(stock_id, date)
);

CREATE TABLE fundamentals_snapshots (
    id              UUID PRIMARY KEY,
    stock_id        UUID REFERENCES stocks(id),
    date            DATE NOT NULL,
    pe_ratio        DECIMAL(10,2),
    eps             DECIMAL(10,4),
    debt_to_equity  DECIMAL(10,2),
    dividend_yield  DECIMAL(6,4),
    market_cap      BIGINT,
    UNIQUE(stock_id, date)
);

CREATE TABLE news_items (
    id              UUID PRIMARY KEY,
    stock_id        UUID REFERENCES stocks(id),
    published_at    TIMESTAMP,
    headline        TEXT,
    source          VARCHAR(255),
    sentiment_score DECIMAL(4,3),   -- -1.0 a 1.0
    url             TEXT
);

-- ---------- 6. EXECUÇÕES DO AGENTE ----------
CREATE TABLE evaluations (
    id                  UUID PRIMARY KEY,
    user_id             UUID REFERENCES users(id),
    stock_id            UUID REFERENCES stocks(id),
    strategy_template_id UUID REFERENCES strategy_templates(id),
    run_at              TIMESTAMP DEFAULT NOW(),
    score               DECIMAL(6,2),           -- score ponderado final
    recommendation      VARCHAR(10),            -- BUY | SELL | HOLD
    summary_text        TEXT,                   -- explicação gerada (opcional, via LLM)
    price_at_evaluation DECIMAL(12,4)
);

-- Detalhe de cada critério avaliado, para auditoria/histórico
CREATE TABLE evaluation_details (
    id                  UUID PRIMARY KEY,
    evaluation_id       UUID REFERENCES evaluations(id) ON DELETE CASCADE,
    strategy_item_id    UUID REFERENCES strategy_items(id),
    observed_value      DECIMAL(12,4),
    passed              BOOLEAN,
    contribution        DECIMAL(6,2)            -- pontos que este item deu ao score
);

-- ---------- 7. PORTFÓLIO (fase futura) ----------
CREATE TABLE portfolio_positions (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    stock_id        UUID REFERENCES stocks(id),
    quantity        DECIMAL(14,4),
    avg_buy_price   DECIMAL(12,4),
    opened_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE transactions (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    stock_id        UUID REFERENCES stocks(id),
    type            VARCHAR(10),        -- BUY | SELL
    quantity        DECIMAL(14,4),
    price           DECIMAL(12,4),
    executed_at     TIMESTAMP DEFAULT NOW(),
    evaluation_id   UUID REFERENCES evaluations(id)  -- liga a transação à recomendação que a originou
);
