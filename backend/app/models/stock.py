import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    exchange: Mapped[str | None] = mapped_column(String(50))
    sector: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(10))
    # "stock" | "etf" - determina se refresh_fundamentals tenta obter
    # fundamentais de empresa (P/E, ROE, etc. não existem para um ETF da
    # mesma forma, ver market_data.py). Default "stock" porque é a esmagadora
    # maioria dos tickers existentes antes desta coluna existir.
    asset_type: Mapped[str] = mapped_column(String(10), nullable=False, default="stock", server_default="stock")
    # Última vez que ensure_fresh tentou o backfill de histórico (sucesso ou
    # falha) - separado da data do último PriceSnapshot de propósito: um
    # ticker que a Finnhub/Twelve Data rejeitam (ex: fora de cobertura do
    # plano gratuito, ver market_data.BACKFILL_RETRY_COOLDOWN) nunca acumula
    # snapshots, e sem isto tentava-se de novo em TODA a visita à página,
    # esgotando a quota partilhada da Twelve Data para as restantes ações.
    last_backfill_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Última vez que se tentou obter a cotação intradiária (Finnhub /quote),
    # sucesso ou falha - governa QUOTE_REFRESH_COOLDOWN em market_data.py.
    # Exposto no StockOut para o frontend mostrar "atualizado há X min" (ver
    # bug real: sem isto o preço ficava congelado no valor da 1ª consulta do
    # dia e não refletia quedas/subidas intradiárias, ex: GOOG a cair ~6%).
    last_quote_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Última vez que se tentou obter fundamentais (Finnhub /stock/metric),
    # sucesso ou falha - governa FUNDAMENTALS_RETRY_COOLDOWN em market_data.py.
    # Bug real corrigido: refresh_fundamentals só corria dentro do ramo de
    # backfill do ensure_fresh, que uma ação madura (histórico já suficiente,
    # ex: MSFT numa watchlist há semanas) nunca mais volta a percorrer - os
    # fundamentais (P/E, ROE, margens...) ficavam congelados no valor da
    # primeira vez que a ação foi adicionada, para sempre. Este campo permite
    # chamar refresh_fundamentals sempre, com proteção contra tentativas
    # repetidas quando a Finnhub rejeita o símbolo (mesmo padrão de
    # last_backfill_attempt_at/last_quote_at).
    last_fundamentals_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
