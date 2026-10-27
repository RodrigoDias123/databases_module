"""PG1: dados de origem (tasks_req + participant)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Pg1Base(DeclarativeBase):
    pass


class TasksReq(Pg1Base):
    """Pedidos de processamento. O Generator Service apanha os 'pendente' e fecha-os."""

    __tablename__ = "tasks_req"
    __table_args__ = (
        CheckConstraint(
            "status in ('pendente', 'em curso', 'concluído', 'erro')",
            name="tasks_req_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # data do pedido
    nome: Mapped[str] = mapped_column(String(255))
    outcome: Mapped[str | None] = mapped_column(String(255))  # resultado do processamento
    finished: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # data/hora de conclusão
    status: Mapped[str] = mapped_column(String(50), server_default="pendente")

    participants: Mapped[list[Participant]] = relationship(back_populates="task")


class Participant(Pg1Base):
    """Dados de saúde de cada pessoa."""

    __tablename__ = "participant"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nome: Mapped[str] = mapped_column(String(255))
    localidade: Mapped[str] = mapped_column(String(255))  # localidade (distrito)
    dnasc: Mapped[date] = mapped_column(Date)  # data de nascimento
    alt: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # altura (m)
    peso: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # peso (kg)
    bp_sys: Mapped[int] = mapped_column(SmallInteger)  # pressão arterial sistólica
    bp_dia: Mapped[int] = mapped_column(SmallInteger)  # pressão arterial diastólica
    hr: Mapped[int] = mapped_column(SmallInteger)  # frequência cardíaca
    # index=True: o Postgres não indexa FKs, e o Generator Service lê os participantes por task_id.
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tasks_req.id", ondelete="CASCADE"), index=True
    )

    task: Mapped[TasksReq] = relationship(back_populates="participants")
