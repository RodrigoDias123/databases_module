"""PG2: relatórios gerados (report_content + insight_report)."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Pg2Base(DeclarativeBase):
    pass


class ReportContent(Pg2Base):
    """Conteúdo do relatório (JSON)."""

    __tablename__ = "report_content"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    content: Mapped[dict] = mapped_column(JSONB)


class InsightReport(Pg2Base):
    """Um relatório por participante.

    id_ppt é o participant.id da PG1. Não pode ser FK: o Postgres não tem FKs entre bases.
    A PK inclui dt para o mesmo participante poder ter vários relatórios ao longo do tempo.
    """

    __tablename__ = "insight_report"

    id_ppt: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )  # data do relatório
    report_content_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("report_content.id", ondelete="CASCADE")
    )
